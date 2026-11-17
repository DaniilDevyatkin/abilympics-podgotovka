#!/usr/bin/env python3
"""Статический сервер для сайта «Абилимпикс Башкортостан».

Зачем свой, а не `python3 -m http.server`:
  * многопоточный — 915 PDF по 5-7 МБ не блокируют друг друга;
  * поддерживает Range — иначе встроенный просмотрщик PDF в браузере
    не листает документ и не умеет докачивать;
  * сжимает gzip'ом HTML/CSS/JS/SVG/JSON — 308 страниц по ~450 КБ
    уходят втрое меньше, а канал до VDS узкий;
  * отдаёт 304 по If-Modified-Since и кэш-заголовки для статики.

Запуск: python3 scripts/serve.py [--bind 127.0.0.1] [--port 8099] [--root DIR]
"""

import argparse
import gzip
import os
import posixpath
import sys
import threading
from email.utils import formatdate, parsedate_to_datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

COMPRESSIBLE = {
    "text/html", "text/css", "text/plain", "application/javascript",
    "application/json", "image/svg+xml", "application/xml",
}
MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
    ".txt": "text/plain; charset=utf-8",
    ".md": "text/plain; charset=utf-8",
}
CHUNK = 256 * 1024


class Handler(BaseHTTPRequestHandler):
    server_version = "AbilympicsStatic/1.0"
    protocol_version = "HTTP/1.1"
    root = PROJECT_ROOT
    min_gzip = 1024

    # ---------- служебное ----------

    def log_message(self, fmt, *args):
        sys.stdout.write("%s %s\n" % (self.address_string(), fmt % args))
        sys.stdout.flush()

    def resolve(self):
        """Путь из URL -> абсолютный путь на диске или None, если выход за root."""
        raw = unquote(urlsplit(self.path).path)
        if "\x00" in raw:
            return None
        parts = [p for p in posixpath.normpath(raw).split("/") if p not in ("", ".", "..")]
        full = os.path.join(self.root, *parts)
        if not os.path.abspath(full).startswith(os.path.abspath(self.root) + os.sep) and \
                os.path.abspath(full) != os.path.abspath(self.root):
            return None
        return full

    # ---------- GET / HEAD ----------

    def do_HEAD(self):
        self.serve(send_body=False)

    def do_GET(self):
        self.serve(send_body=True)

    def serve(self, send_body=True):
        # /index.html и /foo/index.html — служебные имена файлов, в адресной
        # строке они не нужны: отдаём постоянный редирект на каталог.
        raw_path = urlsplit(self.path).path
        if raw_path.endswith("/index.html"):
            candidate = self.resolve()
            if candidate and os.path.isfile(candidate):
                target = raw_path[: -len("index.html")] or "/"
                query = urlsplit(self.path).query
                if query:
                    target += "?" + query
                self.send_response(HTTPStatus.MOVED_PERMANENTLY)
                self.send_header("Location", target)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return

        full = self.resolve()
        if full is None:
            self.send_error(HTTPStatus.FORBIDDEN, "Invalid path")
            return
        if os.path.isdir(full):
            index = os.path.join(full, "index.html")
            if not os.path.isfile(index):
                self.send_error(HTTPStatus.NOT_FOUND, "No index.html in directory")
                return
            full = index
        if not os.path.isfile(full):
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return

        try:
            st = os.stat(full)
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return

        etag = '"%x-%x"' % (int(st.st_mtime), st.st_size)
        last_mod = formatdate(st.st_mtime, usegmt=True)

        # Условные запросы: браузер не перекачивает то, что уже есть.
        inm = self.headers.get("If-None-Match")
        if inm and inm.strip() == etag:
            self.send_response(HTTPStatus.NOT_MODIFIED)
            self.send_header("ETag", etag)
            self.end_headers()
            return
        ims = self.headers.get("If-Modified-Since")
        if ims and not inm:
            try:
                if int(st.st_mtime) <= parsedate_to_datetime(ims).timestamp():
                    self.send_response(HTTPStatus.NOT_MODIFIED)
                    self.send_header("ETag", etag)
                    self.end_headers()
                    return
            except (TypeError, ValueError):
                pass

        ext = os.path.splitext(full)[1].lower()
        ctype = MIME.get(ext, "application/octet-stream")

        start, end = 0, st.st_size - 1
        rng = self.headers.get("Range")
        partial = False
        if rng and rng.startswith("bytes=") and st.st_size:
            spec = rng[6:].split(",")[0].strip()
            try:
                a, _, b = spec.partition("-")
                if a:
                    start = int(a)
                    end = int(b) if b else st.st_size - 1
                else:
                    # bytes=-N — последние N байт
                    start = max(0, st.st_size - int(b))
                if start > end or start >= st.st_size:
                    raise ValueError
                end = min(end, st.st_size - 1)
                partial = True
            except (ValueError, IndexError):
                self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                self.send_header("Content-Range", "bytes */%d" % st.st_size)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return

        length = end - start + 1
        use_gzip = (
            send_body
            and not partial
            and ctype.split(";")[0] in COMPRESSIBLE
            and length >= self.min_gzip
            and length <= 8 * 1024 * 1024
            and "gzip" in (self.headers.get("Accept-Encoding") or "")
        )

        self.send_response(HTTPStatus.PARTIAL_CONTENT if partial else HTTPStatus.OK)
        self.send_header("Content-Type", ctype)
        self.send_header("Last-Modified", last_mod)
        self.send_header("ETag", etag)
        # HTML перепроверяется при каждом заходе (304 по ETag почти бесплатен),
        # иначе правки не доезжают до посетителя до истечения max-age.
        # Картинки, шрифты и PDF кэшируются надолго.
        if ctype.startswith("text/html"):
            self.send_header("Cache-Control", "no-cache, must-revalidate")
        elif ctype.startswith(("image/", "font/", "application/pdf")):
            self.send_header("Cache-Control", "public, max-age=86400")
        else:
            self.send_header("Cache-Control", "public, max-age=3600")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("X-Content-Type-Options", "nosniff")
        if partial:
            self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, st.st_size))
        if not send_body:
            self.send_header("Content-Length", str(length))
            self.end_headers()
            return

        if use_gzip:
            # Сжимаем в память: длина тела должна быть известна, иначе при
            # HTTP/1.1 клиент ждёт закрытия соединения и запрос висит.
            try:
                with open(full, "rb") as f:
                    f.seek(start)
                    body = gzip.compress(f.read(length), compresslevel=6, mtime=0)
            except OSError:
                self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "Read error")
                return
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Vary", "Accept-Encoding")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass
            return

        self.send_header("Content-Length", str(length))
        self.end_headers()
        try:
            with open(full, "rb") as f:
                f.seek(start)
                left = length
                while left > 0:
                    buf = f.read(min(CHUNK, left))
                    if not buf:
                        break
                    self.wfile.write(buf)
                    left -= len(buf)
        except (BrokenPipeError, ConnectionResetError):
            pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bind", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8099)
    ap.add_argument("--root", default=PROJECT_ROOT)
    args = ap.parse_args()

    Handler.root = os.path.abspath(args.root)
    ThreadingHTTPServer.daemon_threads = True
    ThreadingHTTPServer.request_queue_size = 64
    srv = ThreadingHTTPServer((args.bind, args.port), Handler)
    sys.stdout.write("Abilympics static: http://%s:%d/ -> %s\n"
                     % (args.bind, args.port, Handler.root))
    sys.stdout.flush()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
