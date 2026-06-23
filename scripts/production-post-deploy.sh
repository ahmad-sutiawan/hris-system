#!/usr/bin/env bash
# Post-deploy ringan (tanpa bootstrap admin).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
APP_USER="${APP_USER:-www-data}"

[ -x "${ROOT}/.venv/bin/python" ] || { echo "Jalankan: sudo ./scripts/deploy.sh" >&2; exit 1; }

sudo -u "$APP_USER" bash -c "
  cd '$ROOT'
  set -a
  source <(grep -v '^#' .env | grep -v '^$' | sed 's/\r$//')
  set +a
  .venv/bin/python manage.py migrate --noinput
"

systemctl restart hris-web 2>/dev/null || sudo systemctl restart hris-web
bash "$ROOT/scripts/native-verify.sh"
