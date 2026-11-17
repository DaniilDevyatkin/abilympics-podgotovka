#!/usr/bin/env python3
"""Достаёт векторный логотип «Абилимпикс» из брендбука (PDF) в SVG.

Запуск:  PYTHONPATH=<venv site-packages> python3.14 brand/extract_logo.py [--pdf path] [--fill evenodd]

Источник: страница 5 брендбука (01_logo/02), нижняя полоса — компактный локап
«знак А + АБИЛИМПИКС» на светлом фоне. Всё перекрашивается в currentColor,
поэтому один файл работает и на синем, и на белом.
"""
from __future__ import annotations

import argparse
import re
import sys

import pymupdf

PAGE_INDEX = 4
BAND = (20, 765, 265, 812)  # x0, y0, x1, y1 — полоса с компактным логотипом


def contours(drawing):
    """Разбивает items на контуры, возвращая списки тегированных сегментов."""
    out = []
    cur = []
    last = None
    for it in drawing["items"]:
        op = it[0]
        if op == "l":
            p0, p1 = it[1], it[2]
            seg = ("l", p0, p1)
            start, end = p0, p1
        elif op == "c":
            p0, p1, p2, p3 = it[1], it[2], it[3], it[4]
            seg = ("c", p0, p1, p2, p3)
            start, end = p0, p3
        elif op == "re":
            r = it[1]
            seg = ("re", r)
            start, end = r.tl, r.tl
        elif op == "qu":
            q = it[1]
            seg = ("qu", q)
            start, end = q.ul, q.ul
        else:
            continue
        if last is None or abs(start.x - last.x) > 0.05 or abs(start.y - last.y) > 0.05:
            if cur:
                out.append(cur)
            cur = []
        cur.append(seg)
        last = end
    if cur:
        out.append(cur)
    return out


def to_path(contours_, ox, oy):
    d = []
    for c in contours_:
        first = True
        for seg in c:
            kind = seg[0]
            if kind == "re":
                r = seg[1]
                d.append(f"M{r.x0-ox:.2f} {r.y0-oy:.2f}H{r.x1-ox:.2f}V{r.y1-oy:.2f}H{r.x0-ox:.2f}Z")
            elif kind == "qu":
                q = seg[1]
                d.append(f"M{q.ul.x-ox:.2f} {q.ul.y-oy:.2f}L{q.ur.x-ox:.2f} {q.ur.y-oy:.2f}"
                         f"L{q.lr.x-ox:.2f} {q.lr.y-oy:.2f}L{q.ll.x-ox:.2f} {q.ll.y-oy:.2f}Z")
            elif kind == "l":
                p0, p1 = seg[1], seg[2]
                d.append(("M" if first else "L") + f"{p0.x-ox:.2f} {p0.y-oy:.2f}")
                d.append(f"L{p1.x-ox:.2f} {p1.y-oy:.2f}")
            else:
                p0, p1, p2, p3 = seg[1], seg[2], seg[3], seg[4]
                d.append(("M" if first else "L") + f"{p0.x-ox:.2f} {p0.y-oy:.2f}")
                d.append(f"C{p1.x-ox:.2f} {p1.y-oy:.2f} {p2.x-ox:.2f} {p2.y-oy:.2f} {p3.x-ox:.2f} {p3.y-oy:.2f}")
            first = False
        d.append("Z")
    return "".join(d)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", default="/home/fun/inbox/download.pdf")
    ap.add_argument("--fill", default="nonzero", choices=["nonzero", "evenodd"])
    ap.add_argument("--out", default="/home/fun/projects/abilympics-bashkortostan/brand")
    args = ap.parse_args()

    doc = pymupdf.open(args.pdf)
    page = doc[PAGE_INDEX]
    band = pymupdf.Rect(*BAND)
    draws = [d for d in page.get_drawings()
             if d["rect"].intersects(band) and d.get("color") is None and 0.5 < d["rect"].width < 400]
    if not draws:
        print("не нашёл векторных путей в полосе", file=sys.stderr)
        return 1
    draws.sort(key=lambda d: d["rect"].x0)

    def write(subset, name):
        x0 = min(d["rect"].x0 for d in subset); y0 = min(d["rect"].y0 for d in subset)
        x1 = max(d["rect"].x1 for d in subset); y1 = max(d["rect"].y1 for d in subset)
        body = []
        for d in subset:
            d_str = to_path(contours(d), x0, y0)
            # знак «А» рисуется с вырезом (evenodd), буквы — заливкой nonzero:
            # у букв контуры пересекаются, и evenodd рвёт их на куски
            rule = "evenodd" if d is subset[0] else args.fill
            body.append(f'<path fill="currentColor" fill-rule="{rule}" d="{d_str}"/>')
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {x1-x0:.2f} {y1-y0:.2f}" '
               f'role="img" aria-label="Абилимпикс" data-source="брендбук «Абилимпикс» 2026, 01_logo/02">\n'
               + "\n".join(body) + "\n</svg>\n")
        path = f"{args.out}/{name}"
        open(path, "w", encoding="utf-8").write(svg)
        print(f"{path}: {x1-x0:.1f}x{y1-y0:.1f}, {len(svg)} байт")

    write([draws[0]], "mark.svg")
    write(draws, "lockup.svg")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
