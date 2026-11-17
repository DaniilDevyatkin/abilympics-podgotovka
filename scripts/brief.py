#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Готовит «бриф» для написания решения: текст конкурсного задания по категории.

    python3 scripts/brief.py <slug>            # все категории
    python3 scripts/brief.py <slug> student    # одна

Кладёт в work/<slug>/:
    brief-<кат>.txt   — текст КЗ (обезжиренный, до ~28 тыс. знаков) + шапка с фактами
    brief-<кат>.json  — метаданные: категория, файл-источник, число страниц, есть ли текст
Печатает сводку: сколько знаков извлечено и годен ли документ (скан без текста — не годен).
"""
import functools
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "assets", "docs")
WORK = os.path.join(ROOT, "work")
CATS = {"shkolnik": "ШКОЛЬНИКИ", "student": "СТУДЕНТЫ", "specialist": "СПЕЦИАЛИСТЫ"}
LIMIT = 28000

# --- OCR для сканов без текстового слоя -------------------------------------
# tesseract распакован без root, поэтому тянем библиотеки через LD_LIBRARY_PATH.
TESS = "/home/fun/local/tesseract"
TESS_BIN = os.path.join(TESS, "usr/bin/tesseract")
TESS_LIB = os.path.join(TESS, "usr/lib/x86_64-linux-gnu")
TESSDATA = os.path.join(TESS, "usr/share/tesseract-ocr/5/tessdata")
OCR_MIN_CHARS = 40       # меньше — считаем страницу картинкой и распознаём
OCR_DPI = 300


def ocr_page(page):
    """Рендерит страницу в PNG и распознаёт её tesseract'ом (рус+англ)."""
    import subprocess
    import tempfile
    if not os.path.exists(TESS_BIN):
        return ""
    pix = page.get_pixmap(dpi=OCR_DPI)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as fh:
        png = fh.name
        pix.save(png)
    try:
        env = dict(os.environ, LD_LIBRARY_PATH=TESS_LIB,
                   TESSDATA_PREFIX=TESSDATA)
        r = subprocess.run([TESS_BIN, png, "stdout", "-l", "rus+eng", "--psm", "3"],
                           capture_output=True, text=True, timeout=180, env=env)
        return r.stdout or ""
    except Exception:
        return ""
    finally:
        try:
            os.unlink(png)
        except OSError:
            pass


def extract(path):
    return _extract_cached(os.path.abspath(path))


@functools.lru_cache(maxsize=32)
def _extract_cached(path):
    import pymupdf
    doc = pymupdf.open(path)
    pages = []
    ocr_pages = 0
    for p in doc:
        t = p.get_text("text")
        if len(t.strip()) < OCR_MIN_CHARS:
            t2 = ocr_page(p)
            if len(t2.strip()) > len(t.strip()):
                t = t2
                ocr_pages += 1
        t = t.replace("\u00ad", "")
        t = re.sub(r"[ \t]+", " ", t)
        t = re.sub(r"\n{3,}", "\n\n", t)
        pages.append(t.strip())
    if ocr_pages:
        print(f"  OCR: распознано страниц {ocr_pages} из {len(doc)}")
    return "\n\n".join(pages), len(doc)


def main():
    slug = sys.argv[1]
    only = sys.argv[2] if len(sys.argv) > 2 else None
    src_dir = os.path.join(DOCS, slug)
    if not os.path.isdir(src_dir):
        sys.exit(f"нет папки документов: {src_dir}")
    out_dir = os.path.join(WORK, slug)
    os.makedirs(out_dir, exist_ok=True)

    rows = []
    for cat in ([only] if only else ["shkolnik", "student", "specialist"]):
        src = os.path.join(src_dir, f"kz-{cat}.pdf")
        if not os.path.exists(src):
            src = os.path.join(src_dir, "kz.pdf")   # фолбэк: задание целиком
        if not os.path.exists(src):
            rows.append((cat, None, 0, 0))
            continue
        text, n = extract(src)
        if len(text) < 400:
            rows.append((cat, src, len(text), n))
            continue
        head = (
            f"КОМПЕТЕНЦИЯ: {slug}\nКАТЕГОРИЯ: {CATS[cat]}\n"
            f"ИСТОЧНИК: {os.path.relpath(src, ROOT)}\n"
            f"{'=' * 70}\n"
        )
        body = text[:LIMIT]
        if len(text) < 9000:
            full_path = os.path.join(src_dir, "kz.pdf")
            if os.path.exists(full_path) and os.path.abspath(full_path) != os.path.abspath(src):
                full_text, _ = extract(full_path)
                body += ("\n\n" + "=" * 70 +
                         "\nПОЛНЫЙ ДОКУМЕНТ (вырезка категории короткая — здесь всё задание:\n"
                         "технологические карты, критерии и баллы обычно только тут)\n" + "=" * 70 + "\n"
                         + full_text[:LIMIT])
        with open(os.path.join(out_dir, f"brief-{cat}.txt"), "w", encoding="utf-8") as f:
            f.write(head + body)
        json.dump({"slug": slug, "cat": cat, "source": os.path.relpath(src, ROOT),
                   "pages": n, "chars": len(text), "truncated": len(text) > LIMIT},
                  open(os.path.join(out_dir, f"brief-{cat}.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        rows.append((cat, src, len(text), n))

    for cat, src, chars, n in rows:
        state = "ок" if chars >= 400 else ("СКАН БЕЗ ТЕКСТА" if chars else "нет файла")
        print(f"{slug:32} {cat:11} стр {n:3} знаков {chars:6}  {state}")
    bad = [c for c, s, ch, n in rows if ch < 400]
    if bad:
        print("НЕ ГОДИТСЯ:", ", ".join(bad))


if __name__ == "__main__":
    main()
