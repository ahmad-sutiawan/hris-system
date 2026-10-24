#!/usr/bin/env bash
# Perbaikan login production hris.besibps.com (deploy native).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY="${ROOT}/.venv/bin/python"

echo "=== HRIS — perbaikan login production ==="

[ -f .env ] || { echo "ERROR: .env tidak ada"; exit 1; }

git pull origin develop

# shellcheck disable=SC1091
source <(grep -v '^#' .env | grep -v '^$' | sed 's/\r$//')

if [ -z "${HRIS_FIELD_ENCRYPTION_KEY:-}" ]; then
  echo "ERROR: HRIS_FIELD_ENCRYPTION_KEY kosong"
  exit 1
fi

if [ "${HRIS_FIELD_ENCRYPTION_KEY}" = "dev-only-32-char-encryption-key!!" ] || [ "${HRIS_FIELD_ENCRYPTION_KEY}" = "change-me-openssl-rand-hex-32" ]; then
  echo "ERROR: HRIS_FIELD_ENCRYPTION_KEY masih placeholder. Isi kunci unik di .env (openssl rand -hex 32)."
  exit 1
fi

sudo -u www-data bash -c "
  cd '$ROOT'
  .venv/bin/pip install -r requirements.txt -q
  set -a
  source <(grep -v '^#' .env | grep -v '^$' | sed 's/\r$//')
  set +a
  .venv/bin/python manage.py migrate --noinput
"

sudo systemctl restart hris-web
sleep 3
bash "$ROOT/scripts/native-verify.sh"

echo ""
echo "Buat admin jika perlu: sudo -u www-data .venv/bin/python manage.py createsuperuser"
echo "Log: journalctl -u hris-web -n 80 --no-pager"
