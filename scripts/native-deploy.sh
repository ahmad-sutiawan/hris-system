#!/usr/bin/env bash
# Deploy HRIS tanpa Docker — uvicorn + nginx host + MySQL host.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

APP_USER="${APP_USER:-www-data}"
APP_DIR="${APP_DIR:-/var/www/hris-system}"
HRIS_PORT="${HRIS_PORT:-8001}"

echo "=== HRIS native deploy ==="
echo "App dir: $APP_DIR"

if [ "$(id -u)" -ne 0 ]; then
  echo "Jalankan dengan sudo untuk systemd + nginx." >&2
  exit 1
fi

if [ ! -f "$APP_DIR/.env" ]; then
  cp "$APP_DIR/ops/native/env.production.example" "$APP_DIR/.env"
  echo "Buat $APP_DIR/.env — edit SECRET_KEY, DB_PASSWORD, lalu jalankan lagi."
  exit 1
fi

echo "→ apt packages (jika belum)"
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
  python3 python3-venv python3-dev \
  default-libmysqlclient-dev build-essential pkg-config \
  nginx certbot python3-certbot-nginx \
  || true

echo "→ venv + pip"
sudo -u "$APP_USER" bash -c "
  cd '$APP_DIR'
  python3 -m venv .venv
  .venv/bin/pip install -U pip wheel
  .venv/bin/pip install -r requirements.txt
"

echo "→ migrate + static"
sudo -u "$APP_USER" bash -c "
  set -a
  source <(grep -v '^#' '$APP_DIR/.env' | grep -v '^$' | sed 's/\r$//')
  set +a
  cd '$APP_DIR'
  .venv/bin/python manage.py migrate --noinput
  .venv/bin/python manage.py collectstatic --noinput
"

echo "→ systemd hris-web"
cp "$APP_DIR/ops/native/hris-web.service" /etc/systemd/system/hris-web.service
systemctl daemon-reload
systemctl enable hris-web
systemctl restart hris-web

echo "→ nginx site"
cp "$APP_DIR/ops/native/nginx-hris.besibps.com.conf" /etc/nginx/sites-available/hris.besibps.com
ln -sf /etc/nginx/sites-available/hris.besibps.com /etc/nginx/sites-enabled/hris.besibps.com
nginx -t
systemctl reload nginx

echo ""
echo "Selesai. Cek:"
echo "  systemctl status hris-web"
echo "  curl -fsS http://127.0.0.1:${HRIS_PORT}/api/v1/health/"
echo "  certbot --nginx -d hris.besibps.com   # jika SSL belum ada"
echo "  sudo -u $APP_USER bash -c 'cd $APP_DIR && .venv/bin/python manage.py repair_production --bootstrap-admin'"
