#!/usr/bin/env bash
# Ждёт появления A-записи домена и выпускает на него сертификат.
# Запускается в фоне; завершается сам: 0 — сертификат выпущен и проверен,
# 1 — за отведённое время домен так и не появился.
set -uo pipefail

DOMAIN="abilympics-podgotovka.skoiptforma.ru"
IP="104.128.130.176"
ALT="104.128.130.176.sslip.io"
KEY="$HOME/.ssh/id_ed25519_vds"
LOG="$HOME/projects/abilympics-bashkortostan/work/cert-watch.log"
MAX_TRIES=40          # 40 * 3 мин ≈ 2 часа
SLEEP=180

log() { printf '%s %s\n' "$(date -u '+%H:%M:%S')" "$*" | tee -a "$LOG"; }

resolve() {
    curl -sS --max-time 15 "https://dns.google/resolve?name=${DOMAIN}&type=A" 2>/dev/null \
        | grep -o '"data":"[0-9.]*"' | head -1 | cut -d'"' -f4
}

log "старт: жду A-запись ${DOMAIN} -> ${IP}, проверка каждые ${SLEEP} с"

for i in $(seq 1 "$MAX_TRIES"); do
    got="$(resolve)"
    if [ "$got" = "$IP" ]; then
        log "попытка ${i}: A-запись появилась (${got}) — выпускаю сертификат"
        ok=0
        for attempt in 1 2 3 4 5; do
            if ssh -i "$KEY" -o BatchMode=yes -o ConnectTimeout=20 "root@${IP}" \
                "certbot --nginx -d ${DOMAIN} -d ${ALT} --expand --redirect --non-interactive --agree-tos --register-unsafely-without-email" >>"$LOG" 2>&1; then
                log "certbot: сертификат выпущен (попытка ${attempt})"
                ok=1
                break
            fi
            log "certbot: попытка ${attempt} не прошла (зона ещё расходится по NS), пауза 60 с"
            sleep 60
        done
        if [ "$ok" != "1" ]; then
            log "certbot: не удалось выпустить за 5 попыток, смотри вывод выше"
            exit 1
        fi
        sleep 3
        code="$(curl -sS --max-time 25 -o /dev/null -w '%{http_code}' "https://${DOMAIN}/" 2>/dev/null)"
        size="$(curl -sS --max-time 25 -o /dev/null -w '%{size_download}' "https://${DOMAIN}/" 2>/dev/null)"
        log "проверка снаружи: https://${DOMAIN}/ -> ${code}, ${size} байт"
        if [ "$code" = "200" ]; then
            log "готово: сайт открыт по https://${DOMAIN}/"
            exit 0
        fi
        log "сертификат выпущен, но проверка вернула ${code} — нужно смотреть nginx"
        exit 1
    fi
    if [ -n "$got" ] && [ "$got" != "$IP" ]; then
        log "ВНИМАНИЕ: A-запись ${DOMAIN} есть, но указывает на ${got}, а нужен ${IP}"
        log "сертификат не выпускаю: трафик уйдёт не на этот сервер"
        exit 2
    fi
    log "попытка ${i}/${MAX_TRIES}: A-записи пока нет (${got:-NXDOMAIN}), жду ${SLEEP} с"
    sleep "$SLEEP"
done

log "таймаут: за отведённое время домен не появился"
exit 1
