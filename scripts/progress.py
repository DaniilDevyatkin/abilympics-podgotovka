#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Очередь написания решений: work/queue.json.

    python3 scripts/progress.py --build      # пересобрать очередь по 308 компетенциям
    python3 scripts/progress.py --status     # сводка: сколько сделано / в работе / осталось
    python3 scripts/progress.py --next 9     # выдать следующие 9 задач (slug, кат) для написания

Статусы: todo → writing (пока пишут подагенты) → done (в solutions/<slug>.json есть
категория, проходящая порог: ≥20 шагов и ≥18 000 знаков).
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "work", "queue.json")
CATS = ["shkolnik", "student", "specialist"]
MIN_STEPS, MIN_CHARS = 20, 18000


def slug_of(url):
    return re.sub(r"\.html$", "", url.rstrip("/").split("/")[-1])


def metrics(cat):
    steps = sum(len(a["steps"]) for t in cat["tasks"] for a in t["actions"])
    chars = sum(len(s.get(k) or "")
                for t in cat["tasks"] for a in t["actions"] for s in a["steps"]
                for k in ("do", "why", "check", "fail", "expert"))
    return steps, chars


def build():
    comp = json.load(open(os.path.join(ROOT, "competencies.json"), encoding="utf-8"))
    items = [(slug_of(i["url"]), i["name"]) for g in comp for i in g["items"]]
    tasks = []
    for slug, name in items:
        docdir = os.path.join(ROOT, "assets", "docs", slug)
        for cat in CATS:
            tasks.append({"slug": slug, "name": name, "cat": cat,
                          "has_pdf": os.path.exists(os.path.join(docdir, "kz.pdf")),
                          "status": "todo"})
    json.dump({"tasks": tasks}, open(QUEUE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("в очереди:", len(tasks))
    refresh()


def refresh():
    """Помечает done те задачи, где решение уже проходит порог."""
    q = json.load(open(QUEUE, encoding="utf-8"))
    cache = {}
    for t in q["tasks"]:
        path = os.path.join(ROOT, "solutions", t["slug"] + ".json")
        if not os.path.exists(path):
            continue
        if path not in cache:
            try:
                cache[path] = json.load(open(path, encoding="utf-8"))
            except Exception:
                cache[path] = None
        data = cache[path]
        if not data or t["cat"] not in data:
            continue
        try:
            steps, chars = metrics(data[t["cat"]])
        except Exception:
            continue
        if steps >= MIN_STEPS and chars >= MIN_CHARS:
            t["status"] = "done"
            t["steps"], t["chars"] = steps, chars
    json.dump(q, open(QUEUE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return q


def status():
    q = refresh()
    st = {}
    for t in q["tasks"]:
        st[t["status"]] = st.get(t["status"], 0) + 1
    total = len(q["tasks"])
    print(f"всего {total} | " + " | ".join(f"{k}: {v}" for k, v in sorted(st.items())))
    done = st.get("done", 0)
    print(f"готово {done} ({done * 100 // total}%)")
    byslug = {}
    for t in q["tasks"]:
        byslug.setdefault(t["slug"], []).append(t["status"])
    full = sum(1 for v in byslug.values() if all(x == "done" for x in v))
    print(f"компетенций полностью готовы: {full} из {len(byslug)}")


def next_batch(n):
    q = refresh()
    out = [t for t in q["tasks"] if t["status"] == "todo"][:n]
    for t in out:
        t["status"] = "writing"
    json.dump(q, open(QUEUE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for t in out:
        print(f'{t["slug"]}\t{t["cat"]}\t{t["name"]}')


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "--status"
    if arg == "--build":
        build()
    elif arg == "--next":
        next_batch(int(sys.argv[2]) if len(sys.argv) > 2 else 9)
    else:
        status()
