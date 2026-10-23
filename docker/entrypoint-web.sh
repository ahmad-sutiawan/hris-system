#!/bin/sh
set -eu
cd /app

python - <<'PY'
import os
import time

import pymysql

host = os.environ.get("DB_HOST", "mysql")
user = os.environ["DB_USER"]
password = os.environ["DB_PASSWORD"]
database = os.environ["DB_NAME"]
port = int(os.environ.get("DB_PORT") or 3306)

for attempt in range(60):
    try:
        conn = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port,
        )
        conn.close()
        break
    except Exception as exc:
        print(f"waiting for mysql ({attempt + 1}/60): {exc}", flush=True)
        time.sleep(2)
else:
    raise SystemExit("mysql not ready")
PY

python manage.py migrate --noinput
python manage.py collectstatic --noinput

python manage.py shell <<'PY'
import os

from django.contrib.auth import get_user_model

from apps.core.models import Tenant

User = get_user_model()
username = os.environ.get("HRIS_SUPERUSER", "admin")
if User.objects.filter(username=username).exists():
    print(f"superuser {username} already exists")
else:
    slug = os.environ.get("HRIS_DEFAULT_TENANT_SLUG", "default")
    tenant, _created = Tenant.objects.get_or_create(
        slug=slug,
        defaults={"name": slug.upper()},
    )
    user = User.objects.create_superuser(
        username=username,
        email=os.environ.get("HRIS_ADMIN_EMAIL", "admin@hris.local"),
        password=os.environ["HRIS_ADMIN_PASSWORD"],
    )
    user.role = User.Role.ADMIN
    user.tenant = tenant
    user.save()
    print(f"created superuser {username}")
PY

exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
