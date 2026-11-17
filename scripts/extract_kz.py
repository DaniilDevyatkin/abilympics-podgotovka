#!/usr/bin/env python3
"""Разбирает официальные конкурсные задания «Абилимпикс» на три категории.

Источник: PDF с сайта abilympics-russia.ru (по одному на компетенцию, лежат в
assets/docs/<slug>/kz.pdf). Внутри документа категории идут разделами:
  2.1.1 / 2.3.1 / 2.4.1  — «ШКОЛЬНИКИ»
  2.1.2 / 2.3.2 / 2.4.2  — «СТУДЕНТЫ»
  2.1.3 / 2.3.3 / 2.4.3  — «СПЕЦИАЛИСТЫ»

Скрипт вырезает страницы, относящиеся к каждой категории, и собирает из них
отдельный PDF: assets/docs/<slug>/kz-shkolnik.pdf, kz-student.pdf, kz-specialist.pdf.
Плюс пишет meta.json: сколько страниц, какие разделы попали, есть ли разделение.

Запуск:  python3 scripts/extract_kz.py [--only slug]
"""
import json
import os
import re
import sys

import pymupdf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "assets", "docs")

CATS = {
    "shkolnik": ("ШКОЛЬНИКИ", "ШКОЛЬНИК", "Школьники", "Школьник"),
    "student": ("СТУДЕНТЫ", "СТУДЕНТ", "Студенты", "Студент"),
    "specialist": ("СПЕЦИАЛИСТЫ", "СПЕЦИАЛИСТ", "Специалисты", "Специалист"),
}
TITLES = {
    "shkolnik": "Школьники",
    "student": "Студенты",
    "specialist": "Специалисты",
}

# Заголовки встречаются в двух видах:
#   «2.1.2. Категория участников «СТУДЕНТЫ»:»  (с нумерацией)
#   «Категория участников «ШКОЛЬНИКИ»:»        (без нумерации)
ANCHOR = re.compile(
    r"(?:2\s*\.\s*[134]\s*\.\s*[123]\s*\.?\s*)?"          # необязательный номер
    r"(?:Категория\s+участников|Категории\s+участников)"
    r"[^\n]{0,40}?[«\"]?\s*"
    r"(ШКОЛЬНИК|ШКОЛЬНИКИ|СТУДЕНТ|СТУДЕНТЫ|СПЕЦИАЛИСТ|СПЕЦИАЛИСТЫ)",
    re.I,
)
MAP = {"школьник": "shkolnik", "студент": "student", "специалист": "specialist"}

# границы разделов, на которых диапазон категории заканчивается
SECTION = re.compile(r"^\s*(2\s*\.\s*[5-9]|3\s*\.)\s", re.M)


def page_texts(doc):
    return [p.get_text("text") for p in doc]


def find_ranges(texts):
    """Возвращает {категория: [(start_page, end_page), ...]} (0-based, end исключительно)."""
    anchors = []  # (page, cat)
    for i, t in enumerate(texts):
        for m in ANCHOR.finditer(t):
            word = m.group(1).lower()
            cat = "specialist" if word.startswith("специалист") else (
                "student" if word.startswith("студент") else "shkolnik")
            anchors.append((i, cat))
    # убираем подряд идущие одинаковые
    uniq = []
    for a in anchors:
        if not uniq or uniq[-1][1] != a[1]:
            uniq.append(a)

    ranges = {k: [] for k in CATS}
    for idx, (page, cat) in enumerate(uniq):
        end = len(texts)
        if idx + 1 < len(uniq):
            end = uniq[idx + 1][0] if uniq[idx + 1][0] > page else page + 1
        else:
            # до конца документа, но не дальше следующего крупного раздела
            for j in range(page + 1, len(texts)):
                if SECTION.search(texts[j]):
                    end = j + 1
                    break
        ranges[cat].append((page, min(end + 1, len(texts))))
    return ranges


def merge(rngs):
    out = []
    for s, e in sorted(rngs):
        if out and s <= out[-1][1] + 1:
            out[-1] = (out[-1][0], max(out[-1][1], e))
        else:
            out.append((s, e))
    return out


def build_category_pdf(src, ranges, cat, slug, out_path):
    """Собирает новый PDF: титул + страницы источника по диапазонам."""
    out = pymupdf.open()
    cover = out.new_page(width=595, height=842)
    # встроенный helv не умеет кириллицу — подключаем DejaVu
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    if os.path.exists(font_path):
        cover.insert_font(fontname="deja", fontfile=font_path)
    cover.insert_textbox(
        pymupdf.Rect(48, 64, 547, 780),
        "КОНКУРСНОЕ ЗАДАНИЕ\n"
        "категория «%s»\n\n"
        "Компетенция: %s\n\n"
        "Выдержка из официального конкурсного задания, опубликованного\n"
        "на abilympics-russia.ru (раздел «Компетенции 2026»).\n"
        "Страницы источника, относящиеся к категории, приведены далее\n"
        "в исходном виде.\n\n"
        "Собрано автоматически: Региональный центр Абилимпикс\n"
        "республики Башкортостан." % (TITLES[cat], slug),
        fontsize=13,
        fontname="deja" if os.path.exists(font_path) else "helv",
        align=1,
    )
    for s, e in ranges:
        out.insert_pdf(src, from_page=s, to_page=e - 1)
    out.save(out_path, garbage=3, deflate=True)
    out.close()


def main():
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1]

    report = {}
    for slug in sorted(os.listdir(DOCS)):
        if only and slug != only:
            continue
        src_path = os.path.join(DOCS, slug, "kz.pdf")
        if not os.path.exists(src_path):
            continue
        doc = pymupdf.open(src_path)
        texts = page_texts(doc)
        ranges = {c: merge(v) for c, v in find_ranges(texts).items()}
        meta = {"pages_total": doc.page_count, "categories": {}}
        for cat, rng in ranges.items():
            pages = sum(e - s for s, e in rng)
            meta["categories"][cat] = {
                "pages": pages,
                "ranges": [[s + 1, e] for s, e in rng],
            }
            if pages:
                build_category_pdf(
                    doc, rng, cat, slug, os.path.join(DOCS, slug, f"kz-{cat}.pdf")
                )
            else:
                # FALLBACK_SKIP: категория не выделена отдельным разделом —
                # отдаём всё КЗ целиком ссылкой на kz.pdf, копию не делаем
                meta["categories"][cat]["fallback_full"] = True
        meta["split_ok"] = all(v["pages"] > 0 for v in meta["categories"].values())
        with open(os.path.join(DOCS, slug, "meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=1)
        report[slug] = meta
        doc.close()

    ok = sum(1 for m in report.values() if m["split_ok"])
    print(f"обработано: {len(report)}, разделено на три категории: {ok}")
    bad = [s for s, m in report.items() if not m["split_ok"]]
    if bad:
        print("без полного разделения (%d): %s" % (len(bad), ", ".join(bad[:15])))


if __name__ == "__main__":
    main()
