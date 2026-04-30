#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="/opt/lb-agent"
APP_USER="www-data"

echo "[1/6] Instalace systémových balíčků"
apt-get update
apt-get install -y \
  git \
  nginx \
  python3 \
  python3-venv \
  python3-pip \
  build-essential \
  libgl1 \
  libglib2.0-0 \
  tesseract-ocr

echo "[2/6] Vytvoření adresářů"
mkdir -p "${APP_ROOT}/app"
mkdir -p "${APP_ROOT}/shared/data/attachments"
mkdir -p "${APP_ROOT}/logs"

echo "[3/6] Nastavení práv"
chown -R "${APP_USER}:${APP_USER}" "${APP_ROOT}"

echo "[4/6] Python virtualenv"
if [[ ! -d "${APP_ROOT}/.venv" ]]; then
  python3 -m venv "${APP_ROOT}/.venv"
fi

echo "[5/6] Instalace Python závislostí"
"${APP_ROOT}/.venv/bin/pip" install --upgrade pip
if [[ -f "${APP_ROOT}/app/requirements.txt" ]]; then
  "${APP_ROOT}/.venv/bin/pip" install -r "${APP_ROOT}/app/requirements.txt"
else
  echo "Repozitář ještě není v ${APP_ROOT}/app, instalaci Python závislostí přeskočím."
fi

echo "[6/6] Připomenutí dalších kroků"
cat <<EOF

Bootstrap dokončen.

Další kroky:
1. Nahraj .env do ${APP_ROOT}/shared/.env
2. Nahraj credentials.json do ${APP_ROOT}/shared/credentials.json
3. Nastav symlinky:
   ln -sfn ${APP_ROOT}/shared/.env ${APP_ROOT}/app/.env
   ln -sfn ${APP_ROOT}/shared/data ${APP_ROOT}/app/data
   ln -sfn ${APP_ROOT}/shared/credentials.json ${APP_ROOT}/app/credentials.json
4. Zkopíruj systemd služby a nginx config z deploy/
5. Spusť:
   systemctl daemon-reload
   systemctl enable --now lb-agent-web
   systemctl enable --now lb-agent-worker

EOF
