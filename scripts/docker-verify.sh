#!/usr/bin/env bash
# Verifikasi setelah deploy — pastikan semua service sehat.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

MODE="${1:-auto}"
HTTP_PORT="${HTTP_PORT:-8080}"
HRIS_HTTP_PORT="${HRIS_HTTP_PORT:-8081}"
HRIS_SITE_URL="${HRIS_SITE_URL:-}"
HRIS_DOMAIN="${HRIS_DOMAIN:-hris.besibps.com}"

if [ -f .env ]; then
  # shellcheck disable=SC1091
  set -a
  source <(grep -v '^#' .env | grep -v '^$' | sed 's/\r$//')
  set +a
  HTTP_PORT="${HTTP_PORT:-8080}"
  HRIS_HTTP_PORT="${HRIS_HTTP_PORT:-8081}"
  HRIS_SITE_URL="${HRIS_SITE_URL:-}"
  HRIS_DOMAIN="${HRIS_DOMAIN:-hris.besibps.com}"
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

fail() { echo -e "${RED}✗ $1${NC}" >&2; exit 1; }
ok()   { echo -e "${GREEN}✓ $1${NC}"; }
warn() { echo -e "${YELLOW}! $1${NC}"; }

if [ "$MODE" = "auto" ]; then
  if docker compose ps caddy --format '{{.Status}}' 2>/dev/null | grep -qi up; then
    MODE="caddy"
  elif docker compose ps nginx --format '{{.Status}}' 2>/dev/null | grep -qi up; then
    if [ "${HRIS_HTTP_PORT:-8081}" = "8080" ] || [ "${HRIS_BIND_HOST:-127.0.0.1}" = "0.0.0.0" ]; then
      MODE="dev"
    else
      MODE="mysql"
    fi
  else
    MODE="sqlite"
  fi
fi

echo "=== HRIS-Lite post-deploy verify (${MODE}) ==="
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

if [ "$MODE" = "caddy" ]; then
  CADDY_STATUS="$(docker compose ps caddy --format '{{.Status}}' 2>/dev/null || true)"
  if echo "$CADDY_STATUS" | grep -qi up; then
    ok "Container caddy: running"
  else
    fail "Container caddy tidak running. Cek: docker compose logs caddy"
  fi
  BASE_URL="${HRIS_SITE_URL:-https://${HRIS_DOMAIN}}"
elif [ "$MODE" = "mysql" ] || [ "$MODE" = "dev" ]; then
  NGINX_STATUS="$(docker compose ps nginx --format '{{.Status}}' 2>/dev/null || true)"
  if echo "$NGINX_STATUS" | grep -qi up; then
    ok "Container nginx: running"
  else
    fail "Container nginx tidak running. Cek: docker compose logs nginx"
  fi
  if [ "$MODE" = "dev" ]; then
    BASE_URL="http://127.0.0.1:${HTTP_PORT}"
  else
    BASE_URL="http://127.0.0.1:${HRIS_HTTP_PORT}"
  fi
else
  BASE_URL="http://127.0.0.1:${HTTP_PORT}"
fi

BASE_URL="${BASE_URL%/}"
HEALTH_URL="${BASE_URL}/api/v1/health/"

echo ""
echo "Health API (Docker): ${HEALTH_URL}"
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
  CURL_OPTS=(-fsS --max-time 15)
  if RESP="$(curl "${CURL_OPTS[@]}" "$HEALTH_URL" 2>/dev/null)"; then
    echo "$RESP"
    if echo "$RESP" | grep -q '"status":"ok"'; then
      ok "API health OK (via container nginx)"
      break
    fi
    fail "API merespons tapi database bermasalah. Cek: docker compose logs web"
  fi
  if [ "$i" -eq 15 ]; then
    if [ "$MODE" = "caddy" ]; then
      fail "Tidak bisa akses ${HEALTH_URL} — cek DNS, port 80/443, docker compose logs caddy"
    else
      fail "Tidak bisa akses ${HEALTH_URL} — cek: docker compose logs nginx web"
    fi
  fi
  echo "  menunggu... (${i}/15)"
  sleep 4
done

if [ "$MODE" = "mysql" ] && [ -n "${HRIS_SITE_URL:-}" ] && echo "${HRIS_SITE_URL}" | grep -qi '^https://'; then
  PUBLIC_HEALTH="${HRIS_SITE_URL%/}/api/v1/health/"
  echo ""
  echo "Health API (publik via nginx host): ${PUBLIC_HEALTH}"
  if RESP="$(curl -fsS --max-time 15 "$PUBLIC_HEALTH" 2>/dev/null)"; then
    echo "$RESP"
    ok "HTTPS publik OK (nginx host → 127.0.0.1:${HRIS_HTTP_PORT})"
  else
    warn "HTTPS publik belum bisa — jalankan: sudo ./scripts/install-nginx-host.sh && certbot (lihat docker/NGINX-HOST.md)"
  fi
  BASE_URL="${HRIS_SITE_URL}"
fi

CODE="$(curl -s -o /dev/null -w '%{http_code}' "${BASE_URL%/}/" || echo 000)"
if [ "$CODE" = "200" ] || [ "$CODE" = "302" ]; then
  ok "Halaman web merespons HTTP ${CODE}"
else
  fail "Halaman utama HTTP ${CODE}. Cek ALLOWED_HOSTS & logs web"
fi

echo ""
echo -e "${GREEN}Deploy verified.${NC}"
echo "URL: ${BASE_URL%/}/"
echo "Swagger: ${BASE_URL%/}/api/docs/"
