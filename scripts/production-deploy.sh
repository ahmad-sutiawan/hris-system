#!/usr/bin/env bash
# Deploy aman ke production setelah force-push / unrelated histories.
# Jalankan di server: ./scripts/production-deploy.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

BRANCH="${DEPLOY_BRANCH:-develop}"

echo "=== HRIS production deploy (branch: $BRANCH) ==="

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Bukan git repo. Clone ulang dari GitHub ke folder ini."
  exit 1
fi

echo "→ fetch origin/$BRANCH"
git fetch origin "$BRANCH"

echo "→ reset ke origin/$BRANCH (abaikan unrelated histories)"
git reset --hard "origin/$BRANCH"

echo "→ build image (no cache)"
docker compose --profile mysql build --no-cache web worker cron

echo "→ up containers"
docker compose --profile mysql up -d

echo "→ migrate"
docker compose exec -T web python manage.py migrate --noinput

echo "→ post-deploy (sync credentials, foto, nginx reload)"
bash "$ROOT/scripts/production-post-deploy.sh"

echo ""
echo "Deploy selesai. Commit aktif:"
git log -1 --oneline
