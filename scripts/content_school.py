#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сборка решений по «Поварскому делу»: категория «Школьники» — полные тексты.

Части лежат в content_school_a..h.py, здесь только порядок задач и перенумерация.
Категории «Студенты» и «Специалисты» пока остаются прежними.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from content_school_a import TASK1          # 1.1, 1.2
from content_school_b import A13_14, A14    # 1.3, 1.4
from content_school_c import TASK2          # 2.1, 2.2
from content_school_d import A23, A24       # 2.3, 2.4
from content_school_e import A31, A32       # 3.1, 3.2
from content_school_f import A33, A34       # 3.3, 3.4
from content_school_g import A35, A36, TASK4  # 3.5, подача, задача 4
from content_school_h import A37            # композиция на тарелке

INTRO = (
    "Решение разобрано по официальному конкурсному заданию регионального чемпионата «Абилимпикс» 2026 "
    "для категории «Школьники». Задание разбито на четыре задачи, каждая — на действия, действие — на шаги. "
    "В каждом шаге сначала подробно описано, что и как делать (чем резать, под каким углом, до какого "
    "состояния), затем — почему именно так, как убедиться, что получилось, что обычно идёт не так и на что "
    "смотрит эксперт. Региональный ингредиент из «тайного ящика» объявляют за день до старта: он меняет "
    "примерно 30 % задания, поэтому в шагах он назван «региональный ингредиент» — конкретный продукт "
    "подставляйте сами."
)


def renumber(action, num):
    """Приводит нумерацию действия и его шагов к виду 3.6.1."""
    action = dict(action)
    action["title"] = re.sub(r"Действие \d+\.\d+\.", f"Действие {num}.", action["title"])
    steps = []
    for i, s in enumerate(action["steps"], 1):
        s = dict(s)
        s["n"] = f"{num}.{i}"
        steps.append(s)
    action["steps"] = steps
    return action


def main():
    root = os.path.dirname(HERE)
    path = os.path.join(root, "solutions", "povarskoe-delo.json")
    data = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}

    task1 = dict(TASK1)
    task1["actions"] = TASK1["actions"] + [A13_14, A14]

    task2 = dict(TASK2)
    task2["actions"] = TASK2["actions"] + [A23, A24]

    task3 = {
        "title": "Задача 3. Приготовить и подать картофельные зразы с соусом",
        "score": "Модуль В · 30 баллов · подача через 2 ч 30 мин",
        "goal": (
            "Нужно подать две одинаковые порции горячего блюда: картофельные зразы с начинкой из "
            "регионального ингредиента, с соусом, на подогретой тарелке диаметром 30–32 сантиметра. "
            "Температура блюда и тарелки — не ниже 45 градусов. Пюре варим из свежего картофеля, "
            "начинку обязательно пробуем, зразы формуем вручную и обжариваем до золотистой корочки."
        ),
        "img": "kz-temps.svg",
        "actions": [
            renumber(A31, "3.1"), renumber(A32, "3.2"), renumber(A33, "3.3"),
            renumber(A34, "3.4"), renumber(A35, "3.5"),
            renumber(A37, "3.6"),   # композиция на тарелке
            renumber(A36, "3.7"),   # прогрев тарелки, вынос, уборка
        ],
    }
    task3["actions"][5]["title"] = "Действие 3.6. Собрать композицию на тарелке"
    task3["actions"][6]["title"] = "Действие 3.7. Прогреть тарелки, подать и убрать бокс"

    task4 = dict(TASK4)

    data["shkolnik"] = {"intro": INTRO, "images": ["kz-timeline.svg"], "tasks": [task1, task2, task3, task4]}
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    sh = data["shkolnik"]
    chars = 0
    for t in sh["tasks"]:
        steps = sum(len(a["steps"]) for a in t["actions"])
        for a in t["actions"]:
            for s in a["steps"]:
                chars += sum(len(s.get(k) or "") for k in ("do", "why", "check", "fail", "expert"))
        print(f'{t["title"][:52]:54} действий {len(t["actions"]):2}  шагов {steps:2}')
    total = sum(len(a["steps"]) for t in sh["tasks"] for a in t["actions"])
    print(f"итого шагов: {total} | знаков: {chars} | ~слов: {chars//6}")


if __name__ == "__main__":
    main()
