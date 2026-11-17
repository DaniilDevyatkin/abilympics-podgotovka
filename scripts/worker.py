#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Автономный работник: пишет решения по компетенциям без участия человека.

Как устроено:
  • берёт из work/queue.json задачи со статусом todo;
  • для каждой готовит бриф (scripts/brief.py) и запускает отдельный процесс
    `hermes -z "<промпт>"` — обычный агент с инструментами, который читает
    work/INSTRUCTIONS.md и пишет solutions/_gen/<slug>__<кат>.json;
  • готовый файл проверяет по порогам (≥20 шагов, ≥18 тыс. знаков), сливает
    в solutions/<slug>.json, пересобирает страницы и ставит статус done;
  • при сбое — один повтор, потом статус failed с причиной;
  • останавливается по файлу work/STOP или когда очередь пуста.

Запуск вручную:      python3 scripts/worker.py --workers 4
Остановка:           touch work/STOP     (докатывает текущие задачи и выходит)
Смотреть прогресс:   python3 scripts/progress.py --status ; tail -f work/worker.log
"""
import argparse
import fcntl
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "work", "queue.json")
LOG = os.path.join(ROOT, "work", "worker.log")
STOP = os.path.join(ROOT, "work", "STOP")
LOCK = os.path.join(ROOT, "work", "worker.lock")
STATUS = os.path.join(ROOT, "work", "worker-status.json")
PY = "/home/fun/.venvs/pdf/lib/python3.14/site-packages"
PY14 = "/home/fun/.hermes/installs/8ebde39860bf4681/environments/43bef41d46384883bc293c9fa5e53156/venv/bin/python3.14"
HERMES = "/home/fun/.local/bin/hermes"
CAT_RU = {"shkolnik": "ШКОЛЬНИКИ", "student": "СТУДЕНТЫ", "specialist": "СПЕЦИАЛИСТЫ"}
MIN_STEPS, MIN_CHARS = 20, 18000
ITEM_TIMEOUT = 2700          # 45 минут на одну категорию


def log(msg):
    line = f"[{time.strftime('%d.%m %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_queue():
    return json.load(open(QUEUE, encoding="utf-8"))


def save_queue(q):
    with open(LOCK, "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            json.dump(q, open(QUEUE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        finally:
            fcntl.flock(lk, fcntl.LOCK_UN)


def metrics(path):
    data = json.load(open(path, encoding="utf-8"))
    steps = sum(len(a["steps"]) for t in data["tasks"] for a in t["actions"])
    chars = sum(len(s.get(k) or "")
                for t in data["tasks"] for a in t["actions"] for s in a["steps"]
                for k in ("do", "why", "check", "fail", "expert"))
    return steps, chars


def prompt_for(slug, cat, name):
    gen = f"solutions/_gen/{slug}__{cat}.json"
    return (
        f"Ты пишешь одну категорию решения для сайта «Абилимпикс Башкортостан». "
        f"Проект: {ROOT}. Прочитай work/INSTRUCTIONS.md и следуй ему буквально.\n"
        f"slug = {slug}, компетенция «{name}», категория = {cat} ({CAT_RU[cat]}).\n"
        f"Бриф с официальным конкурсным заданием: work/{slug}/brief-{cat}.txt "
        f"(если текста мало — он дополнен полным документом).\n"
        f"Эталон стиля: scripts/content_school_a.py и scripts/content_school_g.py — прочитай оба.\n"
        f"Напиши {gen} (5 полей шага: do/why/check/fail/expert, 40-55 шагов, 45-75 тыс. знаков), "
        f"создай work/{slug}/timeline-{cat}.json и выполни python3 scripts/make_timeline.py {slug} {cat}.\n"
        f"Проверь себя: python3 scripts/merge_gen.py --check — в отчёте должна быть строка "
        f"ok {slug} {cat} без пометки !!. Если помечено !! — дописывай текст, пока не пройдёт.\n"
        f"Не трогай чужие файлы и другие категории этого slug. Отвечай по-русски, коротко."
    )


def run_item(item):
    slug, cat = item["slug"], item["cat"]
    env = dict(os.environ, PYTHONPATH=PY)
    # 1) бриф
    r = subprocess.run([PY14, "scripts/brief.py", slug, cat],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        return False, f"бриф: {r.stderr.strip()[:200]}"
    # 2) агент
    t0 = time.time()
    try:
        r = subprocess.run([HERMES, "-z", prompt_for(slug, cat, item["name"]), "--yolo"],
                           cwd=ROOT, capture_output=True, text=True, timeout=ITEM_TIMEOUT)
    except subprocess.TimeoutExpired:
        return False, "таймаут агента"
    dur = int(time.time() - t0)
    # 3) проверка результата
    gen = os.path.join(ROOT, "solutions", "_gen", f"{slug}__{cat}.json")
    if not os.path.exists(gen):
        return False, f"файл не создан (агент {dur}s, код {r.returncode})"
    try:
        steps, chars = metrics(gen)
    except Exception as e:
        return False, f"битый JSON: {e}"
    if steps < MIN_STEPS or chars < MIN_CHARS:
        return False, f"мало: шагов {steps}, знаков {chars} ({dur}s)"
    return True, f"{steps} шагов, {chars} знаков, {dur}s"


def merge_one(slug, cat):
    gen = os.path.join(ROOT, "solutions", "_gen", f"{slug}__{cat}.json")
    data = json.load(open(gen, encoding="utf-8"))
    path = os.path.join(ROOT, "solutions", slug + ".json")
    with open(LOCK, "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            store = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
            store[cat] = data
            json.dump(store, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        finally:
            fcntl.flock(lk, fcntl.LOCK_UN)


def rebuild():
    env = dict(os.environ, PYTHONPATH=PY)
    subprocess.run([PY14, "scripts/build_pages.py"], cwd=ROOT, env=env,
                   capture_output=True, text=True, timeout=1800)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--max-items", type=int, default=0, help="0 = без ограничения")
    args = ap.parse_args()

    # после падения/перезапуска снимаем зависшие «writing», иначе они висят вечно
    q0 = load_queue()
    stale = [t for t in q0["tasks"] if t["status"] == "writing"]
    for t in stale:
        t["status"] = "todo"
    if stale:
        save_queue(q0)
        log(f"снято зависших задач: {len(stale)}")

    inflight = {}
    done_total = 0
    started = time.time()
    log(f"старт: {args.workers} параллельных, очередь {QUEUE}")

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        while True:
            if os.path.exists(STOP):
                log("найден work/STOP — докатываю текущие и выхожу")
                break
            for fut in list(inflight):
                if fut.done():
                    item = inflight.pop(fut)
                    ok, info = fut.result()
                    slug, cat = item["slug"], item["cat"]
                    q = load_queue()
                    for t in q["tasks"]:
                        if t["slug"] == slug and t["cat"] == cat:
                            if ok:
                                try:
                                    merge_one(slug, cat)
                                    t["status"] = "done"
                                    done_total += 1
                                    log(f"OK   {slug} {cat} — {info}")
                                except Exception as e:
                                    t["status"] = "failed"
                                    t["error"] = f"merge: {e}"
                                    log(f"ERR  {slug} {cat} — merge: {e}")
                            else:
                                if t.get("try", 0) < 2:
                                    t["try"] = t.get("try", 0) + 1
                                    t["status"] = "todo"
                                    log(f"RETRY {slug} {cat} — {info}")
                                else:
                                    t["status"] = "failed"
                                    t["error"] = info
                                    log(f"FAIL {slug} {cat} — {info}")
                    save_queue(q)
                    if ok:
                        rebuild()
            if len(inflight) < args.workers:
                q = load_queue()
                if args.max_items and done_total >= args.max_items:
                    log(f"достигнут лимит --max-items {args.max_items}")
                    break
                free = [t for t in q["tasks"] if t["status"] == "todo"]
                if not free and not inflight:
                    log("очередь пуста — работа закончена")
                    break
                for t in free[: args.workers - len(inflight)]:
                    t["status"] = "writing"
                    log(f"START {t['slug']} {t['cat']}")
                    inflight[pool.submit(run_item, t)] = t
                save_queue(q)
            json.dump({"inflight": len(inflight), "done_this_run": done_total,
                       "uptime_min": int((time.time() - started) / 60),
                       "updated": time.strftime("%Y-%m-%d %H:%M:%S")},
                      open(STATUS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            time.sleep(20)
    log(f"выход: за прогон готово {done_total} категорий")


if __name__ == "__main__":
    main()
