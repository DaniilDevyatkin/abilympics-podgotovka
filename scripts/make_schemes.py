#!/usr/bin/env python3
"""Схемы-иллюстрации к решениям (SVG, без внешних библиотек).

Правила читаемости:
  • холст 680 px — на странице схема выводится шириной ~840 px, поэтому
    шрифт 16 в SVG читается как ~19 px;
  • заголовок 20, основной текст 16, подписи 14;
  • никаких <br/> внутри <text>: каждая строка — отдельный <text>;
  • воздух: 22 px между строками, 40+ между блоками.
"""
import os

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "img")
BLUE, GREEN, RED, INK, GREY, PAPER = "#0540F2", "#007000", "#E83845", "#0B1A26", "#5b6472", "#FFFFFF"
W = 680


def head(h):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" '
            f'font-family="Jost, Arial, sans-serif"><rect width="100%" height="100%" fill="{PAPER}"/>')


def t(x, y, s, size=16, fill=INK, weight=400, anchor="start", ls=0):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" '
            f'text-anchor="{anchor}" letter-spacing="{ls}">{s}</text>')


def save(name, body, h):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        f.write(head(h) + "".join(body) + "</svg>")
    print("assets/img/" + name)


# 1. Таймлайн -----------------------------------------------------------------
def timeline():
    rows = [
        ("−0:15", "Приёмка сырья, спецодежда, инвентарь", "вне конкурсного времени"),
        ("0:00–0:20", "Картофель на плиту, нарезка хлеба, начинка", ""),
        ("0:20–1:00", "Сборка бенто-торта, холодильник 20 минут", ""),
        ("1:00–1:40", "Пюре, начинка, формовка, обжарка, соус", ""),
        ("1:40–1:50", "Декор торта, охлаждение тарелок", ""),
        ("1:55–2:05", "ПОДАЧА МОДУЛЯ Б", "окно ±5 минут · закуска 1–14 °C"),
        ("2:00–2:20", "Доводка зраз, соус, прогрев тарелок", ""),
        ("2:25–2:35", "ПОДАЧА МОДУЛЯ В", "окно ±5 минут · горячее 45 °C и выше"),
    ]
    h = 120 + len(rows) * 44
    body = [t(40, 46, "ПЛАН КОНКУРСА · 2 Ч 30 МИН", 20, BLUE, 700, ls=1)]
    x_time, x_line, x_text = 136, 158, 180
    body.append(f'<line x1="{x_line}" y1="74" x2="{x_line}" y2="{74 + (len(rows)-1)*44}" stroke="{BLUE}" stroke-width="2"/>')
    for i, (tm, what, note) in enumerate(rows):
        y = 82 + i * 44
        serve = what.startswith("ПОДАЧА")
        body.append(t(x_time, y, tm, 16, GREEN if serve else GREY, 700, "end"))
        body.append(f'<circle cx="{x_line}" cy="{y-5}" r="{6 if serve else 4}" fill="{GREEN if serve else BLUE}"/>')
        body.append(t(x_text, y, what, 16, GREEN if serve else INK, 700 if serve else 400))
        if note:
            body.append(t(x_text, y + 20, note, 14, GREEN if serve else GREY))
    body.append(t(40, h - 22, "Опоздание к сервисному окну — блюдо не оценивают.", 14, GREY))
    save("kz-timeline.svg", body, h)


# 2. Маркировка досок ----------------------------------------------------------
def boards():
    items = [("красная", "сырое мясо", "#c1121f"), ("синяя", "рыба, морепродукты", BLUE),
             ("жёлтая", "сырая птица", "#e8b800"), ("зелёная", "овощи, фрукты", GREEN),
             ("белая", "гастрономия, хлеб", "#ffffff"), ("коричневая", "готовая продукция", "#7a5230")]
    h = 300
    body = [t(40, 46, "МАРКИРОВКА ДОСОК", 20, BLUE, 700, ls=1)]
    for i, (name, what, color) in enumerate(items):
        col, row = i % 3, i // 3
        x, y = 40 + col * 210, 76 + row * 108
        stroke = f'stroke="{BLUE}" stroke-width="2"' if color == "#ffffff" else ""
        body.append(f'<rect x="{x}" y="{y}" width="180" height="52" fill="{color}" {stroke}/>')
        body.append(t(x, y + 78, name, 16, INK, 700))
        body.append(t(x, y + 98, what, 14, GREY))
    save("kz-boards.svg", body, h)


# 3. Слои бенто-торта ---------------------------------------------------------
def bento():
    h = 330
    body = [t(40, 46, "СБОРКА БЕНТО-ТОРТА", 20, BLUE, 700, ls=1)]
    x, top, cw, ch = 60, 96, 230, 34
    layers = [("хлеб", "#e9e4d8"), ("начинка", "#cfe6d5"), ("хлеб", "#e9e4d8"),
              ("начинка", "#cfe6d5"), ("хлеб", "#e9e4d8")]
    for i, (name, color) in enumerate(layers):
        y = top + i * ch
        body.append(f'<rect x="{x}" y="{y}" width="{cw}" height="{ch-4}" fill="{color}" stroke="{BLUE}" stroke-width="1.2"/>')
        body.append(t(x + 12, y + 23, name, 15, INK, 500))
    body.append(f'<line x1="{x-18}" y1="{top}" x2="{x-18}" y2="{top + len(layers)*ch}" stroke="{BLUE}" stroke-width="2"/>')
    body.append(t(40, top + len(layers)*ch + 26, "5 слоёв · высота изделия 4–5 см", 14, GREY))
    for i, line in enumerate(["Кольцо снимаем", "после 20 минут", "в холодильнике"]):
        body.append(t(340, 116 + i * 22, line, 16, INK, 600))
    body.append(t(340, 206, "На подаче 1–14 °C", 16, GREEN, 700))
    for i, line in enumerate(["Слои прижимаем ладонью:", "воздуха и начинки по краям", "быть не должно"]):
        body.append(t(340, 240 + i * 20, line, 14, GREY))
    body.append(t(40, h - 24, "Пять слоёв: хлеб → начинка → хлеб → начинка → хлеб.", 14, GREY))
    save("kz-bento.svg", body, h)


# 4. Формовка зраз ------------------------------------------------------------
def zrazy():
    h = 270
    body = [t(40, 46, "ФОРМОВКА ЗРАЗ · 4 ШАГА", 20, BLUE, 700, ls=1)]
    labels = ["лепёшка 60–70 г", "начинка 25–30 г", "защип по краю", "овальная форма"]
    for i, label in enumerate(labels):
        cx, cy = 105 + i * 158, 150
        body.append(f'<ellipse cx="{cx}" cy="{cy}" rx="58" ry="30" fill="#f0ead9" stroke="{BLUE}" stroke-width="2"/>')
        if i == 1:
            body.append(f'<ellipse cx="{cx}" cy="{cy}" rx="24" ry="12" fill="#cfe6d5" stroke="{GREEN}" stroke-width="1.5"/>')
        if i == 2:
            body.append(f'<path d="M{cx-58} {cy} Q{cx} {cy+26} {cx+58} {cy}" fill="none" stroke="{GREEN}" stroke-width="3" stroke-dasharray="7 6"/>')
        if i == 3:
            body.append(f'<ellipse cx="{cx}" cy="{cy}" rx="46" ry="32" fill="none" stroke="{GREEN}" stroke-width="3"/>')
        body.append(t(cx, 208, f"{i+1}. {label}", 14, INK, 500, "middle"))
        if i < 3:
            body.append(f'<path d="M{cx+66} {cy} h20" stroke="{BLUE}" stroke-width="2"/>')
            body.append(f'<path d="M{cx+86} {cy-5} l8 5 l-8 5 z" fill="{BLUE}"/>')
    body.append(t(40, h - 22, "Пюре тёплое. Начинка без свободной жидкости — иначе зраза лопнет на обжарке.", 14, GREY))
    save("kz-zrazy.svg", body, h)


# 5. Схема тарелки ------------------------------------------------------------
def plate():
    h = 320
    body = [t(40, 46, "ПОДАЧА · ТАРЕЛКА 30–32 СМ", 20, BLUE, 700, ls=1)]
    cx, cy, r = 186, 196, 100
    body.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{PAPER}" stroke="{BLUE}" stroke-width="3"/>')
    body.append(f'<circle cx="{cx}" cy="{cy}" r="{r-26}" fill="none" stroke="{BLUE}" stroke-width="1.2" stroke-dasharray="6 6"/>')
    body.append(t(cx, cy + 5, "рабочее поле", 14, GREY, 400, "middle"))
    body.append(f'<line x1="{cx}" y1="{cy-r}" x2="{cx}" y2="{cy-r-26}" stroke="{BLUE}" stroke-width="1.5"/>')
    body.append(t(cx, cy - r - 32, "30–32 см", 14, INK, 600, "middle"))
    body.append(t(330, 100, "Правила подачи", 17, BLUE, 700))
    for i, s in enumerate(["две одинаковые порции", "декор тарелки запрещён",
                           "без шпажек и аксессуаров", "край протёрт насухо",
                           "холодное: тарелка 1–14 °C", "горячее: 45 °C и выше"]):
        body.append(t(330, 132 + i * 28, "— " + s, 15, INK))
    save("kz-plate.svg", body, h)


# 6. Температурная шкала ------------------------------------------------------
def temps():
    h = 240
    body = [t(40, 46, "ТЕМПЕРАТУРА ПОДАЧИ", 20, BLUE, 700, ls=1)]
    x0, x1, y = 60, 620, 130
    body.append(f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="{BLUE}" stroke-width="2"/>')
    cold = (14 / 100) * (x1 - x0)
    body.append(f'<rect x="{x0}" y="{y-18}" width="{cold:.0f}" height="18" fill="{GREEN}"/>')
    hot_x = x0 + 0.45 * (x1 - x0)
    body.append(f'<rect x="{hot_x:.0f}" y="{y-18}" width="{(x1-hot_x):.0f}" height="18" fill="{BLUE}"/>')
    for v in (0, 14, 45, 75, 100):
        x = x0 + (v / 100) * (x1 - x0)
        body.append(f'<line x1="{x:.0f}" y1="{y-24}" x2="{x:.0f}" y2="{y+8}" stroke="{BLUE}" stroke-width="1.5"/>')
        body.append(t(x, y + 30, f"{v} °C", 14, INK, 400, "middle"))
    body.append(t(40, y + 78, "Холодные блюда и десерты: 1–14 °C", 16, GREEN, 600))
    body.append(t(40, y + 106, "Горячие блюда: 45 °C и выше", 16, BLUE, 600))
    body.append(t(40, h - 26, "Птица внутри — 72–75 °C. Тарелку эксперт измеряет пирометром.", 14, GREY))
    save("kz-temps.svg", body, h)


# 7. Толщина нарезки ----------------------------------------------------------
def thickness():
    h = 300
    body = [t(40, 46, "ТОЛЩИНА НАРЕЗКИ", 20, BLUE, 700, ls=1)]
    groups = [
        ("Хлеб для бенто-торта", "5–7 мм", 9, "#e9e4d8", BLUE, "ровные ломти — ровная высота"),
        ("Картофель дофинуа", "2–3 мм", 14, "#f2e7c9", GREEN, "разная толщина — сырые слои"),
        ("Рыба и индейка", "кусок 120–150 г", 2, "#f6d7cf", BLUE, "толщина 2–3 см — равномерно"),
    ]
    for i, (title, size, n, fill, stroke, note) in enumerate(groups):
        y = 84 + i * 72
        body.append(f'<rect x="40" y="{y}" width="150" height="48" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
        for k in range(1, n):
            xx = 40 + k * (150 / n)
            body.append(f'<line x1="{xx:.0f}" y1="{y}" x2="{xx:.0f}" y2="{y+48}" stroke="{stroke}" stroke-width="1.2"/>')
        body.append(t(212, y + 22, title, 16, INK, 600))
        body.append(t(212, y + 44, size, 15, stroke, 700))
        body.append(t(430, y + 30, note, 14, GREY))
    save("kz-thickness.svg", body, h)


if __name__ == "__main__":
    timeline(); boards(); bento(); zrazy(); plate(); temps(); thickness()
