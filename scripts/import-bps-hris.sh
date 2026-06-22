#!/usr/bin/env bash
# Import dump bps_hris ke MySQL Docker production.
# Jalankan di server setelah file SQL di-upload, contoh: /var/www/bps_hris_export.sql
#
#   bash scripts/import-bps-hris.sh /var/www/bps_hris_export.sql
set -euo pipefail

SQL_FILE="${1:-}"
if [ -z "$SQL_FILE" ] || [ ! -f "$SQL_FILE" ]; then
  echo "Usage: $0 /path/to/bps_hris_export.sql"
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# shellcheck disable=SC1091
source <(grep -v '^#' .env | grep -v '^$' | sed 's/\r$//')

DB="${DB_NAME:-hris_system}"
ROOT_PW="${MYSQL_ROOT_PASSWORD:?MYSQL_ROOT_PASSWORD tidak ada di .env}"

echo "Import $SQL_FILE → MySQL database $DB ..."
docker compose --profile mysql exec -T mysql \
  mysql -uroot -p"$ROOT_PW" "$DB" < "$SQL_FILE"

echo "Import selesai. Jalankan:"
echo "  bash scripts/fix-production-login.sh"
