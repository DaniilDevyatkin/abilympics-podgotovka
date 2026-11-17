#!/usr/bin/env python3
"""Рендер пошагового решения из структуры «задание → задачи → действия → шаги».

Формат JSON (solutions/<slug>.json):
{
  "shkolnik": {
     "intro": "необязательный абзац",
     "images": ["kz-timeline.svg", ...],
     "tasks": [
        {"title": "Задача 1. ...", "goal": "что должно получиться", "score": "Модуль А · 36 баллов",
         "img": "kz-boards.svg",
         "actions": [
            {"title": "Действие 1.1 ...",
             "steps": [
                {"n": "1.1.1", "do": "...", "why": "...", "check": "...", "fail": "...", "expert": "..."}
             ]}
         ]}
     ],
     "expert": [["Модуль А", "36", "..."], ...],
     "risks": ["...", "..."]
  }
}
"""
import html


def esc(s):
    return html.escape(s, quote=False)


def render_cat(data):
    if not data:
        return ""
    out = []
    if data.get("intro"):
        out.append(f'<p class="s-intro">{esc(data["intro"])}</p>')

    for img in data.get("images", []):
        out.append(f'<figure class="s-fig"><img src="../assets/img/{esc(img)}" alt="Схема к заданию" loading="lazy"></figure>')

    for i, task in enumerate(data.get("tasks", []), 1):
        score = f'<span class="s-score">{esc(task["score"])}</span>' if task.get("score") else ""
        out.append(f'<section class="s-task"><h3>{esc(task["title"])}{score}</h3>')
        if task.get("goal"):
            out.append(f'<p class="s-goal">{esc(task["goal"])}</p>')
        if task.get("img"):
            out.append(f'<figure class="s-fig"><img src="../assets/img/{esc(task["img"])}" alt="Схема: {esc(task["title"])}" loading="lazy"></figure>')
        for action in task.get("actions", []):
            out.append(f'<h4>{esc(action["title"])}</h4>')
            out.append('<div class="s-grid">')
            for st in action.get("steps", []):
                out.append('<div class="s-step">')
                out.append(f'<p class="s-step__n">Шаг {esc(st["n"])}</p>')
                out.append(f'<div class="s-row s-row--do"><span class="s-label">Делаем</span>'
                           f'<p class="s-val">{esc(st["do"])}</p></div>')
                rows = [("why", "Зачем", st.get("why")), ("check", "Как проверить", st.get("check")),
                        ("fail", "Типичная ошибка", st.get("fail")), ("expert", "Что видит эксперт", st.get("expert"))]
                for kind, label, val in rows:
                    if val:
                        out.append(f'<div class="s-row s-row--{kind}"><span class="s-label">{label}</span>'
                                   f'<p class="s-val">{esc(val)}</p></div>')
                if st.get("img"):
                    out.append(f'<figure class="s-fig s-fig--step"><img src="../assets/img/{esc(st["img"])}" '
                               f'alt="Схема к шагу {esc(st["n"])}" loading="lazy"></figure>')
                out.append("</div>")
            out.append("</div>")
        out.append("</section>")

    if data.get("expert"):
        out.append('<h3>Как распределяются баллы</h3><table class="s-table"><tr><th>Блок</th><th>Баллы</th><th>Что оценивают</th></tr>')
        for row in data["expert"]:
            out.append("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in row) + "</tr>")
        out.append("</table>")

    if data.get("risks"):
        out.append('<h3>Красные флаги: за это теряют всё</h3><ul class="s-risks">')
        for r in data["risks"]:
            out.append(f"<li>{esc(r)}</li>")
        out.append("</ul>")
    return "".join(out)
