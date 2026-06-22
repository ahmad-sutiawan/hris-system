#!/usr/bin/env bash
# Jalankan di server production (148.230.98.125) setelah git pull / docker build.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== HRIS production post-deploy ==="

if docker compose ps web >/dev/null 2>&1; then
  RUN="docker compose exec -T web"
elif command -v python3 >/dev/null 2>&1 && [ -f manage.py ]; then
  RUN="python3 manage.py"
else
  echo "Jalankan dari folder proyek HRIS dengan Docker atau manage.py."
  exit 1
fi

echo "→ migrate"
$RUN python manage.py migrate --noinput

echo "→ sync kredensial login karyawan (NIK + Employee ID)"
$RUN python manage.py sync_employee_credentials --tenant default

echo "→ uji login JWT contoh (opsional, abaikan jika gagal)"
if command -v curl >/dev/null 2>&1; then
  curl -s -X POST "http://127.0.0.1:8080/api/v1/auth/token/" \
    -H "Content-Type: application/json" \
    -d '{"username":"525","password":"525"}' || true
  echo
  echo "→ uji CORS Flutter web (localhost emulator)"
  curl -s -i -X OPTIONS "http://127.0.0.1:8080/api/v1/health/" \
    -H "Origin: http://localhost:49609" \
    -H "Access-Control-Request-Method: GET" | head -12 || true
  echo
fi

if docker compose ps nginx >/dev/null 2>&1; then
  echo "→ reload nginx (CORS /api/)"
  docker compose exec -T nginx nginx -s reload 2>/dev/null || docker compose restart nginx
fi

echo ""
echo "Selesai. Login mobile: NIK + Employee ID (password = Employee ID)."
