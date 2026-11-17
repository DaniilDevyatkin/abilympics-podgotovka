#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сборка решения «Изготовление мороженого» (студенты) из частей build/part*.json."""
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "work", "izgotovlenie-morozhennogo", "build")
OUT = os.path.join(ROOT, "solutions", "_gen", "izgotovlenie-morozhennogo__student.json")

INTRO = (
    "Студенческое задание компетенции «Изготовление мороженого» — три порции холодного десерта "
    "из натурального брусничного мороженого в вафельной корзиночке с шоколадным соусом и декором "
    "из орехов, без использования готовых смесей. На всё даётся два часа: модуль А — мороженое и "
    "подача, 60 минут, модуль Б — вафельные корзиночки, 30 минут, модуль В — соус и ореховый декор, "
    "30 минут; распределять время между модулями участник может сам, и именно это распределение "
    "решает половину результата. Требования считаются по граммам и градусам: шарик не более 60 "
    "граммов, корзиночка не более 30, общая масса порции не менее 100 граммов, гарнир 25 граммов, "
    "температура подачи не выше минус 3 °C. Региональное изменение на 30 % вносится за сутки: "
    "наполнитель для мороженого — кедровый орех. Ниже весь путь по шагам, в том порядке, в котором "
    "его выгоднее проходить в боксе, с расчётами и контрольными признаками."
)


def main():
    tasks = []
    for f in sorted(glob.glob(os.path.join(BUILD, "part*.json"))):
        tasks.append(json.load(open(f, encoding="utf-8")))
    data = {"intro": INTRO, "images": ["timeline-izgotovlenie-morozhennogo-student.svg"], "tasks": tasks}

    steps = chars = 0
    for ti, t in enumerate(tasks, 1):
        for ai, a in enumerate(t["actions"], 1):
            assert a["title"].startswith(f"Действие {ti}.{ai}."), a["title"]
            for si, s in enumerate(a["steps"], 1):
                assert s["n"] == f"{ti}.{ai}.{si}", (s["n"], f"{ti}.{ai}.{si}")
                steps += 1
                chars += sum(len(s[k]) for k in ("do", "why", "check", "fail", "expert"))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(data, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("написано:", os.path.relpath(OUT, ROOT))
    print("задач:", len(tasks), "действий:", sum(len(t["actions"]) for t in tasks),
          "шагов:", steps, "знаков:", chars, "intro:", len(INTRO))


if __name__ == "__main__":
    main()
