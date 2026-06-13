#!/usr/bin/env bash
# Deploy HRIS-Lite — satu perintah, dengan preflight & verifikasi.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

MODE="${1:-sqlite}"

if [ "$MODE" != "sqlite" ] && [ "$MODE" != "mysql" ]; then
  echo "Usage: $0 [sqlite|mysql]"
  echo ""
  echo "  sqlite  — uji coba / staging (default, tanpa MySQL)"
  echo "  mysql   — production (MySQL 8 + cron backup)"
  exit 1
fi

if [ ! -f .env ]; then
  echo "Membuat .env..."
  bash scripts/generate-env.sh
fi

bash scripts/docker-preflight.sh "$MODE"

echo ""
echo "=== Building & starting containers ==="
if [ "$MODE" = "mysql" ]; then
  docker compose --profile mysql up -d --build
  bash scripts/wait-mysql.sh
else
  docker compose up -d --build
fi

bash scripts/docker-verify.sh

echo ""
echo "=== Langkah berikutnya (opsional) ==="
echo "  Seed demo:  docker compose exec web python manage.py seed_demo"
echo "  Log live:   docker compose logs -f web nginx"
echo "  Stop:       docker compose down"
echo ""
echo "Login demo (setelah seed): admin / Admin123456!"
