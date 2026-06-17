#!/bin/sh
set -e

mkdir -p /app/audit_archive /app/backups /var/log

echo "[cron] waiting for database..."
until python <<'PY'
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()
from django.db import connection

try:
    connection.ensure_connection()
except Exception:
    sys.exit(1)
sys.exit(0)
PY
do
  sleep 5
done

python manage.py migrate --noinput

CRON_FILE=/etc/cron.d/hris-lite
{
  echo "SHELL=/bin/sh"
  echo "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
  echo "0 2 * * * root cd /app && python manage.py archive_audit_logs >> /var/log/hris-cron.log 2>&1"
  echo "0 4 * * 0 root cd /app && python manage.py purge_attendance_retention --execute >> /var/log/hris-cron.log 2>&1"
  if echo "${DB_ENGINE:-}" | grep -q mysql; then
    echo "0 3 * * * root cd /app && python manage.py backup_database --output-dir /app/backups >> /var/log/hris-cron.log 2>&1"
  fi
} > "$CRON_FILE"
chmod 0644 "$CRON_FILE"

echo "[cron] scheduled jobs:"
cat "$CRON_FILE"

exec cron -f
