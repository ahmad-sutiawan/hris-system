#!/usr/bin/env bash
# Jalankan di server production setelah docker compose --profile mysql up -d --build
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== HRIS production post-deploy ==="

RUN="docker compose --profile mysql exec -T web"

echo "→ migrate"
$RUN python manage.py migrate --noinput

echo "→ repair production (tenant, admin, sync login karyawan)"
$RUN python manage.py repair_production --bootstrap-admin --tenant default || true

echo "→ kompres foto profil karyawan (WebP avatar)"
$RUN python manage.py compress_employee_photos --tenant default || true

SITE_URL="${HRIS_SITE_URL:-https://hris.besibps.com}"
if [ -f .env ]; then
  # shellcheck disable=SC1091
  val="$(grep -E '^HRIS_SITE_URL=' .env | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")"
  if [ -n "$val" ]; then
    SITE_URL="$val"
  fi
fi

echo "→ health check ${SITE_URL}/api/v1/health/"
if command -v curl >/dev/null 2>&1; then
  curl -fsS "${SITE_URL%/}/api/v1/health/" && echo
fi

echo ""
echo "Selesai."
echo "  Login web admin: username akun HR/admin"
echo "  Login karyawan: NIK + Employee ID (password = Employee ID)"
echo "  Jika login 500: docker compose --profile mysql logs web --tail 80"
