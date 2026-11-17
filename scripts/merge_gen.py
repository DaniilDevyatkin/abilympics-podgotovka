#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сборка решений, написанных подагентами: solutions/_gen/<slug>__<cat>.json → solutions/<slug>.json.

    python3 scripts/merge_gen.py            # проверить и слить всё, что есть
    python3 scripts/merge_gen.py --check     # только проверить, ничего не писать

Порог: ≥20 шагов и ≥18 000 знаков в пяти полях. Файлы ниже порога остаются в _gen
и печатаются в отчёте — им нужно дописать текст, а не переписывать заново.
"""
import glob
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = os.path.join(ROOT, "solutions", "_gen")
MIN_STEPS, MIN_CHARS = 20, 18000


def metrics(cat):
    steps = sum(len(a["steps"]) for t in cat["tasks"] for a in t["actions"])
    chars = sum(len(s.get(k) or "")
                for t in cat["tasks"] for a in t["actions"] for s in a["steps"]
                for k in ("do", "why", "check", "fail", "expert"))
    return steps, chars


def schema_ok(cat):
    errs = []
    if not isinstance(cat, dict) or "tasks" not in cat:
        return ["нет ключа tasks"]
    if not cat.get("intro"):
        errs.append("нет intro")
    for ti, t in enumerate(cat["tasks"], 1):
        for key in ("title", "actions"):
            if not t.get(key):
                errs.append(f"задача {ti}: нет {key}")
        for ai, a in enumerate(t.get("actions", []), 1):
            if not a.get("title"):
                errs.append(f"задача {ti} действие {ai}: нет title")
            for st in a.get("steps", []):
                for key in ("n", "do", "why", "check", "fail"):
                    if not (st.get(key) or "").strip():
                        errs.append(f'шаг {st.get("n", "?")}: пустое поле {key}')
    return errs


def main():
    check_only = "--check" in sys.argv
    files = sorted(glob.glob(os.path.join(GEN, "*__*.json")))
    if not files:
        print("нет файлов в solutions/_gen")
        return
    good, bad = [], []
    for f in files:
        base = os.path.basename(f)[:-5]
        slug, cat = base.split("__")
        try:
            data = json.load(open(f, encoding="utf-8"))
        except Exception as e:
            bad.append((slug, cat, f"битый JSON: {e}"))
            continue
        errs = schema_ok(data)
        if errs:
            bad.append((slug, cat, "; ".join(errs[:3]) + (f" (+{len(errs)-3})" if len(errs) > 3 else "")))
            continue
        steps, chars = metrics(data)
        if steps < MIN_STEPS or chars < MIN_CHARS:
            bad.append((slug, cat, f"мало: шагов {steps}/{MIN_STEPS}, знаков {chars}/{MIN_CHARS}"))
            continue
        good.append((slug, cat, data, steps, chars))

    for slug, cat, data, steps, chars in good:
        print(f"  ok  {slug:38} {cat:11} шагов {steps:3} знаков {chars:7}")
    for slug, cat, why in bad:
        print(f"  !!  {slug:38} {cat:11} {why}")
    print(f"годных {len(good)} | проблемных {len(bad)}")
    if check_only or not good:
        return

    touched = set()
    for slug, cat, data, steps, chars in good:
        path = os.path.join(ROOT, "solutions", slug + ".json")
        store = {}
        if os.path.exists(path):
            try:
                store = json.load(open(path, encoding="utf-8"))
            except Exception:
                store = {}
        store[cat] = data
        json.dump(store, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        touched.add(slug)

    print("слито компетенций:", len(touched))
    subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "build_pages.py")], check=False)
    subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "queue.py"), "--status"], check=False)


if __name__ == "__main__":
    main()
