#!/usr/bin/env bash
# Import dump SQL ke MySQL host (production native).
#   bash scripts/import-bps-hris.sh /path/to/bps_hris_export.sql
set -euo pipefail

SQL_FILE="${1:-}"
if [ -z "$SQL_FILE" ] || [ ! -f "$SQL_FILE" ]; then
  echo "Usage: $0 /path/to/export.sql"
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
[ -f .env ] || { echo ".env tidak ada"; exit 1; }

# shellcheck disable=SC1091
source <(grep -v '^#' .env | grep -v '^$' | sed 's/\r$//')

DB="${DB_NAME:-hris_system}"
HOST="${DB_HOST:-127.0.0.1}"
PORT="${DB_PORT:-3306}"
USER="${DB_USER:-hris}"
PASS="${DB_PASSWORD:?DB_PASSWORD tidak ada di .env}"

echo "Import $SQL_FILE → $DB @ $HOST ..."
mysql -h"$HOST" -P"$PORT" -u"$USER" -p"$PASS" "$DB" < "$SQL_FILE"

echo "Import selesai. Restart: sudo systemctl restart hris-web"
echo "Admin: .venv/bin/python manage.py createsuperuser"
