#!/usr/bin/env bash
# Perbaikan login production hris.besibps.com (deploy native).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY="${ROOT}/.venv/bin/python"
CANONICAL_KEY="0e409590449cd788616afee8ff8db95d9320e1325b7b98ccb0d32128308b9063"

echo "=== HRIS — perbaikan login production ==="

[ -f .env ] || { echo "ERROR: .env tidak ada"; exit 1; }

git pull origin develop

# shellcheck disable=SC1091
source <(grep -v '^#' .env | grep -v '^$' | sed 's/\r$//')

if [ -z "${HRIS_FIELD_ENCRYPTION_KEY:-}" ]; then
  echo "ERROR: HRIS_FIELD_ENCRYPTION_KEY kosong"
  exit 1
fi

if [ "${HRIS_FIELD_ENCRYPTION_KEY}" = "dev-only-32-char-encryption-key!!" ]; then
  sed -i "s|^HRIS_FIELD_ENCRYPTION_KEY=.*|HRIS_FIELD_ENCRYPTION_KEY=${CANONICAL_KEY}|" .env
  echo "HRIS_FIELD_ENCRYPTION_KEY diperbarui ke key production."
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
