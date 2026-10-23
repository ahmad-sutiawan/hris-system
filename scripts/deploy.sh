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

fail() { echo "ERROR: $*" >&2; exit 1; }

sql_escape() { printf '%s' "$1" | sed "s/'/''/g"; }

fresh_database() {
  local db="${DB_NAME:-hris_system}"
  local user="${DB_USER:-hris}"
  local pass_escaped
  pass_escaped="$(sql_escape "${DB_PASSWORD}")"

  local sql="
DROP DATABASE IF EXISTS \`${db}\`;
CREATE DATABASE \`${db}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${user}'@'localhost' IDENTIFIED BY '${pass_escaped}';
ALTER USER '${user}'@'localhost' IDENTIFIED BY '${pass_escaped}';
GRANT ALL PRIVILEGES ON \`${db}\`.* TO '${user}'@'localhost';
FLUSH PRIVILEGES;
"

  if mysql -h"${DB_HOST:-127.0.0.1}" -P"${DB_PORT:-3306}" -u"$user" -p"${DB_PASSWORD}" -e "SELECT 1" &>/dev/null; then
    echo "   akses MySQL sebagai $user OK"
    mysql -h"${DB_HOST:-127.0.0.1}" -P"${DB_PORT:-3306}" -u"$user" -p"${DB_PASSWORD}" -e "$sql"
  elif [ -n "${MYSQL_ROOT_PASSWORD:-}" ]; then
    echo "   akses MySQL sebagai root (password dari .env)"
    mysql -h"${DB_HOST:-127.0.0.1}" -P"${DB_PORT:-3306}" -uroot -p"${MYSQL_ROOT_PASSWORD}" -e "$sql"
  elif sudo mysql -e "SELECT 1" &>/dev/null; then
    echo "   akses MySQL via sudo mysql (root socket Ubuntu)"
    sudo mysql -e "$sql"
  else
    fail "Tidak bisa akses MySQL. Buat user manual atau set MYSQL_ROOT_PASSWORD di .env"
  fi
}

setup_python() {
  echo "→ Python venv + migrate + static"
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3-venv python3-dev \
    default-libmysqlclient-dev build-essential pkg-config

  mkdir -p "$APP_DIR/media" "$APP_DIR/audit_archive" "$APP_DIR/backups"
  rm -rf "$APP_DIR/.venv"
  python3 -m venv "$APP_DIR/.venv"
  chown -R "$APP_USER:$APP_USER" "$APP_DIR/.venv" "$APP_DIR/media" "$APP_DIR/audit_archive" "$APP_DIR/backups"

  sudo -u "$APP_USER" bash -c "
    set -euo pipefail
    cd '$APP_DIR'
    .venv/bin/pip install -U pip wheel
    .venv/bin/pip install -r requirements.txt
    set -a
    source <(grep -v '^#' .env | grep -v '^$' | sed 's/\r$//')
    set +a
    .venv/bin/python manage.py migrate --noinput
    .venv/bin/python manage.py collectstatic --noinput
  "
}

echo "=============================================="
echo " HRIS deploy — $DOMAIN"
echo "=============================================="

if [ ! -f "$ENV_FILE" ]; then
  [ -f "$ENV_EXAMPLE" ] && cp "$ENV_EXAMPLE" "$ENV_FILE"
  echo ""
  echo "File .env dibuat. Edit SECRET_KEY + DB_PASSWORD, lalu jalankan lagi:"
  echo "  nano $ENV_FILE"
  exit 1
fi

# shellcheck disable=SC1091
source <(grep -v '^#' "$ENV_FILE" | grep -v '^$' | sed 's/\r$//')

[ "${SECRET_KEY:-}" = "change-me-openssl-rand-hex-32" ] || [ -z "${SECRET_KEY:-}" ] && \
  fail "SECRET_KEY masih default — openssl rand -hex 32"
echo "${DB_PASSWORD:-}" | grep -qiE 'GANTI_|change-me|PASTE_' && \
  fail "DB_PASSWORD masih placeholder di .env"
[ -z "${HRIS_FIELD_ENCRYPTION_KEY:-}" ] && fail "HRIS_FIELD_ENCRYPTION_KEY kosong"
[ "${DB_USER:-}" = "root" ] && \
  fail "DB_USER jangan 'root' di Ubuntu — pakai DB_USER=hris (script buat user otomatis saat --fresh-db)"

if [ "$DO_PULL" = true ]; then
  echo "→ git pull origin/$BRANCH"
  git fetch origin "$BRANCH"
  git reset --hard "origin/$BRANCH"
fi

echo "→ paket sistem"
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
  python3 python3-venv python3-dev \
  default-libmysqlclient-dev build-essential pkg-config \
  nginx certbot python3-certbot-nginx mysql-client \
  2>/dev/null || true

if [ "$FRESH_DB" = true ]; then
  echo "→ kosongkan database ${DB_NAME:-hris_system}"
  fresh_database
fi

setup_python

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
  [ "$i" -eq 24 ] && fail "uvicorn tidak merespons — journalctl -u hris-web -n 50"
  sleep 5
done

echo "→ nginx"
bash "$APP_DIR/scripts/install-nginx.sh"

if [ -d "/etc/letsencrypt/live/${DOMAIN}" ]; then
  echo "→ SSL sudah ada"
else
  echo "→ certbot SSL"
  certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos \
    -m "${ACME_EMAIL:-adminwebsite@besibps.com}" || \
    echo "⚠ certbot gagal — jalankan: certbot --nginx -d $DOMAIN"
fi

echo ""
bash "$APP_DIR/scripts/native-verify.sh"

echo ""
echo "=============================================="
echo " Deploy selesai — ${HRIS_SITE_URL:-https://$DOMAIN}"
echo ""
echo " Buat admin:"
echo "   sudo -u $APP_USER bash -c 'cd $APP_DIR && .venv/bin/python manage.py createsuperuser'"
echo "=============================================="
