#!/bin/sh
set -e

echo "[cron] waiting for database..."
until python manage.py migrate --noinput; do
  sleep 5
done

# Arsip audit log — tiap hari jam 02:00
echo "0 2 * * * cd /app && python manage.py archive_audit_logs >> /var/log/cron.log 2>&1" > /etc/crontabs/root

# Backup MySQL — tiap hari jam 03:00
echo "0 3 * * * cd /app && python manage.py backup_database --output-dir /app/backups >> /var/log/cron.log 2>&1" >> /etc/crontabs/root

crond -f -l 2
