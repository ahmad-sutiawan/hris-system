#!/usr/bin/env bash
# Satu perintah deploy HRIS-Lite via Docker (Ubuntu 24 / lokal)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example — edit SECRET_KEY & ALLOWED_HOSTS before production."
fi

MODE="${1:-sqlite}"

case "$MODE" in
  sqlite)
    docker compose up -d --build
    ;;
  mysql)
    docker compose --profile mysql up -d --build
    ;;
  *)
    echo "Usage: $0 [sqlite|mysql]"
    exit 1
    ;;
esac

echo ""
echo "Waiting for health check..."
sleep 5
curl -fsS "http://127.0.0.1:${HTTP_PORT:-8080}/api/v1/health/" | head -c 200 || true
echo ""
echo ""
echo "HRIS-Lite running at http://127.0.0.1:${HTTP_PORT:-8080}"
echo "Seed demo: docker compose exec web python manage.py seed_demo"
echo "Logs:      docker compose logs -f web"
