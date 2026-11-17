#!/usr/bin/env python3
"""Генерирует страницы компетенций и переписывает ссылки на странице списка.

Вход:
  competencies.json              — названия и слаги (выгрузка с официального сайта)
  assets/docs/<slug>/kz-*.pdf    — задания по категориям (см. scripts/extract_kz.py)
  assets/docs/<slug>/meta.json   — какие страницы источника попали в вырезку
  solutions/<slug>.json          — пошаговые решения (если уже написаны)

Выход:
  kompetentsii/<slug>.html       — страница компетенции
  kompetentsii-2026.html         — ссылки переписаны на локальные страницы
"""
import json
import os
import re
import sys
from html import escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sol_render import render_cat

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "assets", "docs")
OUT = os.path.join(ROOT, "kompetentsii")
SOL = os.path.join(ROOT, "solutions")

CATS = [
    ("shkolnik", "Школьник", "14–16 лет, базовый уровень задания"),
    ("student", "Студент", "учащиеся колледжей и техникумов"),
    ("specialist", "Специалист", "работающие профессионалы"),
]

MARK = None


def mark_path():
    return open(os.path.join(ROOT, "brand", "mark.svg")).read()


def human(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f} МБ"
    return f"{max(1, round(n/1024))} КБ"


def build_blocks(slug, meta, sol):
    rows = []
    for key, title, hint in CATS:
        cat = meta["categories"].get(key, {})
        fname = "kz.pdf" if cat.get("fallback_full") else f"kz-{key}.pdf"
        pdf = os.path.join(DOCS, slug, fname)
        has_pdf = os.path.exists(pdf)
        size = human(os.path.getsize(pdf)) if has_pdf else ""
        if cat.get("fallback_full"):
            note = ("В официальном файле категории не разделены отдельными разделами — "
                    "приводим задание целиком; различия по категориям смотрите в таблице модулей.")
            pages_note = f"страниц: {meta['pages_total']}"
        else:
            rng = cat.get("ranges") or []
            pages_note = ", ".join(f"{a}–{b}" if b > a else str(a) for a, b in rng)
            note = ("Выдержка из официального конкурсного задания: страницы, относящиеся "
                    f"к категории «{title}» (стр. {pages_note} источника).")
        _sol = sol.get(key)
        if isinstance(_sol, dict):
            _sol = render_cat(_sol)
        sol_html = _sol or (
            '<p class="todo">Пошаговое решение для этой категории ещё пишется: нужно прочитать '
            'всё задание, регламент и критерии целиком и разложить работу на проверяемые шаги. '
            'Пока страница отдаёт официальное задание — по нему уже можно готовиться.</p>'
        )
        link = ""
        if has_pdf:
            link = (f'<a class="doc" href="../assets/docs/{slug}/{fname}" target="_blank" '
                    f'rel="noopener"><span class="doc__name">Конкурсное задание · {escape(title)}</span>'
                    f'<span class="doc__meta">PDF · {size}</span></a>')
        rows.append(f'''
    <section class="cat" id="{key}" aria-labelledby="h-{key}">
      <div class="cat__head">
        <h2 class="cat__title" id="h-{key}">{escape(title)}</h2>
        <span class="cat__hint">{escape(hint)}</span>
      </div>
      {link}
      <p class="cat__note">{escape(note)}</p>
      <details class="steps">
        <summary>Пошаговое решение</summary>
        <div class="steps__body">{sol_html}</div>
      </details>
    </section>''')
    return "\n".join(rows)


def page(slug, name, group, meta, sol, cnt):
    return f'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(name)} — Абилимпикс Башкортостан</title>
<meta name="description" content="Компетенция «{escape(name)}»: конкурсные задания «Абилимпикс» 2026 для школьника, студента и специалиста и пошаговые решения.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Jost:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../assets/base.css">
<style>
.crumbs{{display:flex;flex-wrap:wrap;align-items:center;gap:.4em;margin:0 0 clamp(16px,2vw,26px)}}
.crumbs a{{border-bottom:1px solid var(--blue)}}
.crumbs a:hover{{background:var(--blue);color:var(--white);border-bottom-color:transparent}}

.head{{padding:clamp(22px,3vw,44px) var(--gutter) clamp(16px,2vw,28px);border-bottom:2px solid var(--blue)}}
h1{{margin:0;font-size:clamp(30px,5.6vw,76px);font-weight:700;line-height:.94;letter-spacing:-.02em;text-transform:uppercase}}
.meta{{display:flex;flex-wrap:wrap;gap:8px 22px;margin:clamp(14px,1.8vw,22px) 0 0;font-size:12px;
  letter-spacing:.1em;text-transform:uppercase;font-weight:500}}
.meta a{{border-bottom:1px solid var(--blue)}}
.meta a:hover{{background:var(--blue);color:var(--white)}}

.list{{padding:clamp(10px,1.4vw,18px) var(--gutter) clamp(40px,6vw,90px)}}

.cat{{padding:clamp(22px,3vw,38px) 0;border-bottom:1px solid var(--blue)}}
.cat:last-child{{border-bottom:0}}
.cat__head{{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;margin-bottom:14px}}
.cat__title{{margin:0;font-size:clamp(22px,3vw,34px);font-weight:700;text-transform:uppercase;letter-spacing:-.01em}}
.cat__hint{{font-size:11px;font-weight:500;letter-spacing:.16em;text-transform:uppercase}}

.doc{{display:flex;justify-content:space-between;align-items:baseline;gap:16px;
  padding:12px 14px;border:2px solid var(--blue);font-weight:600;font-size:14px;
  transition:background .15s var(--ease),color .15s var(--ease)}}
.doc:hover{{background:var(--blue);color:var(--white)}}
.doc__meta{{font-size:11px;letter-spacing:.14em;text-transform:uppercase;font-weight:500}}

.cat__note{{margin:10px 0 0;font-size:12.5px;line-height:1.5;max-width:60ch}}

.steps{{margin-top:16px;border-top:2px solid var(--blue)}}
.steps summary{{cursor:pointer;padding:14px 0;font-size:13px;font-weight:600;letter-spacing:.14em;
  text-transform:uppercase;list-style:none;display:flex;align-items:center;gap:10px}}
.steps summary::-webkit-details-marker{{display:none}}
.steps summary::before{{content:"+";font-size:20px;line-height:1;font-weight:400}}
.steps[open] summary::before{{content:"–"}}
.steps summary:hover{{background:var(--blue);color:var(--white);padding-left:8px}}
.steps__body{{padding:12px 0 26px;max-width:70ch}}
.steps__body .todo{{font-size:15px;line-height:1.6;max-width:60ch}}
.take{{margin:18px 0 0;padding:12px 14px;border:2px solid var(--blue);font-size:13.5px;line-height:1.55}}
</style>
<link rel="stylesheet" href="../assets/solution.css">
</head>
<body>
<a class="skip" href="#tasks">К заданиям</a>

<header class="top">
  <a class="brand" href="../index.html" aria-label="Абилимпикс Башкортостан — на главную">
    <svg class="brand__mark" viewBox="0 0 27.27 32.78" aria-hidden="true"><path fill-rule="nonzero" d="{MARK}"/></svg>
    <span class="brand__rule" aria-hidden="true"></span>
    <span class="brand__text">
      <span class="brand__name">Абилимпикс</span>
      <span class="brand__sub region-sub">Башкортостан 2026</span>
    </span>
  </a>
  <nav class="nav" aria-label="Основная навигация">
    <a class="nav__link" href="../index.html">Главная</a>
    <a class="nav__link is-current" href="../kompetentsii-2026.html" aria-current="page">Компетенции 2026</a>
  </nav>
</header>

<main>
  <div class="head">
    <nav class="crumbs label" aria-label="Хлебные крошки">
      <a href="../index.html">Главная</a><span aria-hidden="true">/</span>
      <a href="../kompetentsii-2026.html">Компетенции 2026</a><span aria-hidden="true">/</span>
      <span>{escape(name)}</span>
    </nav>
    <h1>{escape(name)}</h1>
    <p class="meta">
      <span>Категории: школьник · студент · специалист</span>
      <a href="https://abilympics-russia.ru/competencies/Komp2026/{slug}.html" target="_blank" rel="noopener">Официальная страница компетенции</a>
    </p>
  </div>

  <div class="list" id="tasks">
    <p class="cat__note">Задания ниже — официальные файлы «Абилимпикс» (источник: abilympics-russia.ru), разложенные по категориям. Решения написаны по тексту задания, регламенту и критериям оценки; в них указано, что именно проверяет эксперт.</p>
{build_blocks(slug, meta, sol)}
  </div>
</main>

<footer class="foot">
  <span>© 2026 Региональный центр Абилимпикс республики Башкортостан</span>
  <span>Республика Башкортостан, г. Салават</span>
</footer>
</body>
</html>
'''


def main():
    global MARK
    MARK = re.search(r' d="([^"]+)"', mark_path()).group(1)
    comps = json.load(open(os.path.join(ROOT, "competencies.json")))
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(SOL, exist_ok=True)

    written = 0
    total = 0
    local = {}
    for group in comps:
        for item in group["items"]:
            slug = item["url"].rsplit("/", 1)[-1].replace(".html", "")
            meta_path = os.path.join(DOCS, slug, "meta.json")
            if not os.path.exists(meta_path):
                continue
            meta = json.load(open(meta_path))
            sol_path = os.path.join(SOL, slug + ".json")
            sol = json.load(open(sol_path)) if os.path.exists(sol_path) else {}
            cnt = sum(1 for k in ("shkolnik", "student", "specialist") if sol.get(k))
            total += cnt
            html = page(slug, item["name"], group["letter"], meta, sol, cnt)
            with open(os.path.join(OUT, slug + ".html"), "w", encoding="utf-8") as f:
                f.write(html)
            local[item["url"]] = f"kompetentsii/{slug}.html"
            written += 1
    print(f"страниц: {written} | написано решений (категорий): {total}")
    json.dump(local, open(os.path.join(ROOT, "page_map.json"), "w"), ensure_ascii=False)


if __name__ == "__main__":
    main()
