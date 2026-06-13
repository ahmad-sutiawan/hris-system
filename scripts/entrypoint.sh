#!/bin/sh
set -e

mkdir -p /app/data /app/media /app/audit_archive /app/backups

wait_for_db() {
  if echo "${DB_ENGINE:-}" | grep -q mysql; then
    echo "[entrypoint] waiting for MySQL..."
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
      sleep 2
    done
    echo "[entrypoint] database ready"
  fi
}

wait_for_db
python manage.py migrate --noinput
python manage.py collectstatic --noinput

if [ -n "${HRIS_BOOTSTRAP_SUPERUSER:-}" ] && [ -n "${HRIS_BOOTSTRAP_PASSWORD:-}" ]; then
  python manage.py shell -c "
from django.contrib.auth import get_user_model
import os
User = get_user_model()
username = os.environ['HRIS_BOOTSTRAP_SUPERUSER']
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, None, os.environ['HRIS_BOOTSTRAP_PASSWORD'])
    print('[entrypoint] superuser created:', username)
"
fi

exec "$@"
