#!/bin/sh
set -eu
cd /app

python - <<'PY'
import os
import time

import redis

url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
for attempt in range(60):
    try:
        client = redis.Redis.from_url(url)
        client.ping()
        break
    except Exception as exc:
        print(f"waiting for redis ({attempt + 1}/60): {exc}", flush=True)
        time.sleep(2)
else:
    raise SystemExit("redis not ready")
PY

exec python manage.py rqworker default punch
