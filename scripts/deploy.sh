#!/usr/bin/env bash
# Satu perintah deploy HRIS production — uvicorn + nginx + MySQL host.
#
#   sudo ./scripts/deploy.sh              # deploy / update
#   sudo ./scripts/deploy.sh --pull       # git pull dulu
#   sudo ./scripts/deploy.sh --fresh-db   # kosongkan DB + migrate ulang
#
# Admin: buat manual setelah deploy:
#   sudo -u www-data bash -c 'cd /var/www/hris-system && .venv/bin/python manage.py createsuperuser'
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

APP_USER="${APP_USER:-www-data}"
APP_DIR="${APP_DIR:-$ROOT}"
HRIS_PORT="${HRIS_PORT:-8001}"
DOMAIN="${HRIS_DOMAIN:-hris.besibps.com}"
BRANCH="${DEPLOY_BRANCH:-develop}"
DO_PULL=false
FRESH_DB=false

for arg in "$@"; do
  case "$arg" in
    --pull) DO_PULL=true ;;
    --fresh-db) FRESH_DB=true ;;
    -h|--help)
      sed -n '2,10p' "$0"
      exit 0
      ;;
    *) echo "Opsi tidak dikenal: $arg (gunakan --pull, --fresh-db)" >&2; exit 1 ;;
  esac
done

if [ "$(id -u)" -ne 0 ]; then
  echo "Jalankan: sudo $0 [--pull] [--fresh-db]" >&2
  exit 1
fi

ENV_FILE="$APP_DIR/.env"
ENV_EXAMPLE="$APP_DIR/ops/native/env.production.example"

echo "=============================================="
echo " HRIS deploy — $DOMAIN"
echo "=============================================="

# --- .env ---
if [ ! -f "$ENV_FILE" ]; then
  if [ -f "$ENV_EXAMPLE" ]; then
    cp "$ENV_EXAMPLE" "$ENV_FILE"
  fi
  echo ""
  echo "File .env dibuat. Edit dulu (SECRET_KEY, DB_PASSWORD), lalu jalankan lagi:"
  echo "  nano $ENV_FILE"
  exit 1
fi

# shellcheck disable=SC1091
source <(grep -v '^#' "$ENV_FILE" | grep -v '^$' | sed 's/\r$//')

if [ "${SECRET_KEY:-}" = "change-me-openssl-rand-hex-32" ] || [ -z "${SECRET_KEY:-}" ]; then
  echo "ERROR: SECRET_KEY masih default. Generate: openssl rand -hex 32" >&2
  exit 1
fi
if echo "${DB_PASSWORD:-}" | grep -qiE 'GANTI_|change-me|PASTE_'; then
  echo "ERROR: DB_PASSWORD masih placeholder di .env" >&2
  exit 1
fi
if [ -z "${HRIS_FIELD_ENCRYPTION_KEY:-}" ]; then
  echo "ERROR: HRIS_FIELD_ENCRYPTION_KEY kosong di .env" >&2
  exit 1
fi

# --- git pull ---
if [ "$DO_PULL" = true ]; then
  echo "→ git pull origin/$BRANCH"
  git fetch origin "$BRANCH"
  git reset --hard "origin/$BRANCH"
fi

# --- paket sistem ---
echo "→ paket sistem"
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
  python3 python3-venv python3-dev \
  default-libmysqlclient-dev build-essential pkg-config \
  nginx certbot python3-certbot-nginx mysql-client \
  2>/dev/null || true

# --- DB kosong (opsional) ---
if [ "$FRESH_DB" = true ]; then
  echo "→ kosongkan database ${DB_NAME:-hris_system}"
  mysql -h"${DB_HOST:-127.0.0.1}" -P"${DB_PORT:-3306}" -u"${DB_USER:-hris}" -p"${DB_PASSWORD}" -e "
    DROP DATABASE IF EXISTS \`${DB_NAME:-hris_system}\`;
    CREATE DATABASE \`${DB_NAME:-hris_system}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
  "
fi

# --- venv, migrate, static ---
echo "→ Python venv + migrate + static"
sudo -u "$APP_USER" bash -c "
  cd '$APP_DIR'
  python3 -m venv .venv 2>/dev/null || true
  .venv/bin/pip install -U pip wheel -q
  .venv/bin/pip install -r requirements.txt -q
  set -a
  source <(grep -v '^#' .env | grep -v '^$' | sed 's/\r$//')
  set +a
  .venv/bin/python manage.py migrate --noinput
  .venv/bin/python manage.py collectstatic --noinput
"

# --- systemd ---
echo "→ systemd hris-web"
cp "$APP_DIR/ops/native/hris-web.service" /etc/systemd/system/hris-web.service
systemctl daemon-reload
systemctl enable hris-web
systemctl restart hris-web

echo "→ tunggu uvicorn..."
for i in $(seq 1 24); do
  if curl -fsS "http://127.0.0.1:${HRIS_PORT}/api/v1/health/" >/dev/null 2>&1; then
    echo "   uvicorn OK"
    break
  fi
  if [ "$i" -eq 24 ]; then
    echo "ERROR: uvicorn tidak merespons — journalctl -u hris-web -n 50" >&2
    exit 1
  fi
  sleep 5
done

# --- nginx ---
echo "→ nginx"
bash "$APP_DIR/scripts/install-nginx.sh"

# --- SSL (jika belum ada) ---
if [ -d "/etc/letsencrypt/live/${DOMAIN}" ]; then
  echo "→ SSL sudah ada untuk $DOMAIN"
else
  echo "→ certbot SSL"
  CERTBOT_EMAIL="${ACME_EMAIL:-adminwebsite@besibps.com}"
  certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$CERTBOT_EMAIL" || \
    echo "⚠ certbot gagal — jalankan manual: certbot --nginx -d $DOMAIN"
fi

# --- verifikasi ---
echo ""
bash "$APP_DIR/scripts/native-verify.sh"

echo ""
echo "=============================================="
echo " Deploy selesai — $HRIS_SITE_URL"
echo ""
echo " Buat admin (sekali):"
echo "   sudo -u $APP_USER bash -c 'cd $APP_DIR && .venv/bin/python manage.py createsuperuser'"
echo ""
echo " Import data (opsional):"
echo "   bash scripts/import-bps-hris.sh /path/to/dump.sql"
echo "=============================================="
