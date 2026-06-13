#!/usr/bin/env bash
# Tunggu MySQL healthy; jika gagal tampilkan log & saran perbaikan.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

fail_mysql() {
  echo -e "${RED}✗ MySQL gagal start${NC}" >&2
  echo ""
  docker compose --profile mysql logs mysql --tail=100 2>&1 || true
  echo ""
  echo -e "${YELLOW}Perbaikan umum:${NC}"
  echo "  1. Di .env: DB_USER=hris  (JANGAN root)"
  echo "  2. MYSQL_ROOT_PASSWORD harus terisi (openssl rand -hex 32)"
  echo "  3. Password dengan @/#/ spasi — pakai tanda kutip: DB_PASSWORD=\"pass@123\""
  echo "  4. Reset volume MySQL (hapus data DB):"
  echo "       docker compose --profile mysql down -v"
  echo "       ./scripts/docker-up.sh mysql"
  exit 1
}

echo "Menunggu MySQL siap (max ~2 menit)..."
for _ in $(seq 1 60); do
  state="$(docker compose --profile mysql ps mysql --format '{{.State}}' 2>/dev/null || true)"
  health="$(docker compose --profile mysql ps mysql --format '{{.Health}}' 2>/dev/null || true)"

  if [ "$health" = "healthy" ]; then
    echo "✓ MySQL healthy"
    exit 0
  fi

  if echo "$state" | grep -qiE 'exited|dead'; then
    fail_mysql
  fi

  sleep 2
done

fail_mysql
