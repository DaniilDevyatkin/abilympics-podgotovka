# -*- coding: utf-8 -*-
"""Сборка решения «Цифровая метрология» (студенты) из частей в один JSON."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from t1 import TASK1
from t2 import TASK2
from t3 import TASK3
from t4 import TASK4
from t5 import TASK5

INTRO = (
    "Конкурсное задание категории «Студенты» состоит из двух модулей общей длительностью шесть "
    "часов: четыре часа на контроль качества партии из трёх деталей и два часа на калибровку "
    "выданного средства измерений. В модуле А вы разбираете чертёж, подбираете инструмент под "
    "каждый допуск, оформляете программу измерения и проходите точку «СТОП!», после чего "
    "измеряете детали по очереди и сдаёте таблицу в Excel с именем «Модуль A_номер участника». "
    "В модуле Б вы определяете тип прибора и его метрологические характеристики, подбираете "
    "эталоны с действующими свидетельствами, калибруете по пяти точкам и оформляете протокол в "
    "PDF. Сто баллов распределены так: методика измерений — 20, измерения деталей и охрана "
    "труда — 40, протокол — 10, проведение поверки — 20, обработка результатов — 10. Больше "
    "всего теряют на двух вещах: прибор должен быть точнее трети допуска, а все записи делаются "
    "по ходу работы."
)

TASKS = [TASK1, TASK2, TASK3, TASK4, TASK5]
IMG = "timeline-tsifrovaya-metrologiya-r-student.svg"

data = {"intro": INTRO, "images": [IMG], "tasks": TASKS}

# самопроверка нумерации
prev_t = prev_a = prev_s = 0
for ti, t in enumerate(TASKS, 1):
    for ai, a in enumerate(t["actions"], 1):
        assert a["title"].startswith(f"Действие {ti}.{ai}."), a["title"]
        for si, st in enumerate(a["steps"], 1):
            assert st["n"] == f"{ti}.{ai}.{si}", (st["n"], f"{ti}.{ai}.{si}")
            for k in ("do", "why", "check", "fail", "expert"):
                assert st.get(k) and st[k].strip(), (st["n"], k)

steps = sum(len(a["steps"]) for t in TASKS for a in t["actions"])
chars = sum(len(s[k]) for t in TASKS for a in t["actions"] for s in a["steps"]
            for k in ("do", "why", "check", "fail", "expert"))

out = os.path.join(os.path.dirname(HERE), "tsifrovaya-metrologiya-r__student.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=1)

print("записано:", out)
print("задач:", len(TASKS), "действий:", sum(len(t["actions"]) for t in TASKS),
      "шагов:", steps, "знаков в пяти полях:", chars, "intro:", len(INTRO))

# длины полей по шагам — для контроля диапазонов
lim = {"do": (350, 600), "why": (250, 450), "check": (200, 350), "fail": (200, 350), "expert": (150, 300)}
bad = []
for t in TASKS:
    for a in t["actions"]:
        for s in a["steps"]:
            for k, (lo, hi) in lim.items():
                n = len(s[k])
                if not (lo <= n <= hi):
                    bad.append(f'{s["n"]} {k}={n} (нужно {lo}-{hi})')
print("выходов за диапазоны:", len(bad))
for b in bad:
    print("  ", b)
