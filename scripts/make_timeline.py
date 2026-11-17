#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Универсальная схема «план конкурса» для любой компетенции.

    python3 scripts/make_timeline.py <slug>

Читает work/<slug>/timeline.json:
{
  "title": "ПЛАН КОНКУРСА · 3 Ч 00 МИН",
  "rows": [{"t": "0:00–0:40", "what": "Модуль А: разметка деталей", "note": "доска 2"},
           {"t": "2:55–3:00", "what": "СДАЧА РАБОТЫ", "note": "окно ±5 минут", "accent": true}],
  "footer": "Опоздание к сдаче — работа не оценивается."
}
Пишет assets/img/timeline-<slug>.svg в той же графике, что и кулинарный таймлайн.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "img")
BLUE, GREEN, INK, GREY, PAPER = "#0540F2", "#007000", "#0B1A26", "#5b6472", "#FFFFFF"
W = 680


def t(x, y, s, size=16, fill=INK, weight=400, anchor="start", ls=0):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" '
            f'text-anchor="{anchor}" letter-spacing="{ls}">{s}</text>')


def main(slug, cat=None):
    name = f"timeline-{cat}.json" if cat else "timeline.json"
    out_name = f"timeline-{slug}-{cat}.svg" if cat else f"timeline-{slug}.svg"
    spec = json.load(open(os.path.join(ROOT, "work", slug, name), encoding="utf-8"))
    rows = spec["rows"]
    h = 118 + len(rows) * 44
    body = [t(40, 46, spec.get("title", "ПЛАН КОНКУРСА"), 20, BLUE, 700, ls=1)]
    x_time, x_line, x_text = 136, 158, 180
    body.append(f'<line x1="{x_line}" y1="74" x2="{x_line}" y2="{74 + (len(rows) - 1) * 44}" '
                f'stroke="{BLUE}" stroke-width="2"/>')
    for i, r in enumerate(rows):
        y = 82 + i * 44
        accent = bool(r.get("accent"))
        body.append(t(x_time, y, r["t"], 16, GREEN if accent else GREY, 700, "end"))
        body.append(f'<circle cx="{x_line}" cy="{y - 5}" r="{6 if accent else 4}" '
                    f'fill="{GREEN if accent else BLUE}"/>')
        body.append(t(x_text, y, r["what"], 16, GREEN if accent else INK, 700 if accent else 400))
        if r.get("note"):
            body.append(t(x_text, y + 20, r["note"], 14, GREEN if accent else GREY))
    if spec.get("footer"):
        body.append(t(40, h - 22, spec["footer"], 14, GREY))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" '
           f'font-family="Jost, Arial, sans-serif"><rect width="100%" height="100%" fill="{PAPER}"/>'
           + "".join(body) + "</svg>")
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, out_name)
    open(path, "w", encoding="utf-8").write(svg)
    print("написано:", os.path.relpath(path, ROOT), f"({len(rows)} строк)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("укажите slug [категория]")
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
