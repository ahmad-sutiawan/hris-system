#!/usr/bin/env bash
# Verifikasi setelah deploy — pastikan semua service sehat.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

HTTP_PORT="${HTTP_PORT:-8080}"
if [ -f .env ]; then
  # shellcheck disable=SC1091
  source <(grep -E '^HTTP_PORT=' .env | sed 's/\r$//') || true
  HTTP_PORT="${HTTP_PORT:-8080}"
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

fail() { echo -e "${RED}✗ $1${NC}" >&2; exit 1; }
ok()   { echo -e "${GREEN}✓ $1${NC}"; }

echo "=== HRIS-Lite post-deploy verify ==="
echo ""

docker compose ps || fail "docker compose ps gagal"

WEB_STATUS="$(docker compose ps web --format '{{.Status}}' 2>/dev/null || true)"
if echo "$WEB_STATUS" | grep -qi healthy; then
  ok "Container web: healthy"
elif echo "$WEB_STATUS" | grep -qi up; then
  ok "Container web: running (healthcheck mungkin masih pending)"
else
  fail "Container web tidak running. Cek: docker compose logs web"
fi

NGINX_STATUS="$(docker compose ps nginx --format '{{.Status}}' 2>/dev/null || true)"
if echo "$NGINX_STATUS" | grep -qi up; then
  ok "Container nginx: running"
else
  fail "Container nginx tidak running. Cek: docker compose logs nginx"
fi

echo ""
echo "Health API..."
for i in 1 2 3 4 5 6 7 8 9 10; do
  if RESP="$(curl -fsS "http://127.0.0.1:${HTTP_PORT}/api/v1/health/" 2>/dev/null)"; then
    echo "$RESP"
    if echo "$RESP" | grep -q '"status":"ok"'; then
      ok "API health OK"
      break
    fi
    fail "API merespons tapi database bermasalah. Cek: docker compose logs web"
  fi
  if [ "$i" -eq 10 ]; then
    fail "Tidak bisa akses http://127.0.0.1:${HTTP_PORT}/api/v1/health/ — cek firewall & docker compose logs"
  fi
  echo "  menunggu... (${i}/10)"
  sleep 3
done

CODE="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${HTTP_PORT}/" || echo 000)"
if [ "$CODE" = "200" ] || [ "$CODE" = "302" ]; then
  ok "Halaman web merespons HTTP ${CODE}"
else
  fail "Halaman utama HTTP ${CODE}. Cek ALLOWED_HOSTS & logs web"
fi

echo ""
echo -e "${GREEN}Deploy verified.${NC}"
echo "URL: http://127.0.0.1:${HTTP_PORT}/"
echo "Swagger: http://127.0.0.1:${HTTP_PORT}/api/docs/"
