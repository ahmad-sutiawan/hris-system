#!/usr/bin/env bash
# Verifikasi deploy native — health API lokal & publik.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

HRIS_PORT="${HRIS_PORT:-8001}"
SITE_URL="${HRIS_SITE_URL:-https://hris.besibps.com}"

if [ -f .env ]; then
  # shellcheck disable=SC1091
  set -a
  source <(grep -v '^#' .env | grep -v '^$' | sed 's/\r$//')
  set +a
  SITE_URL="${HRIS_SITE_URL:-$SITE_URL}"
fi

LOCAL="http://127.0.0.1:${HRIS_PORT}/api/v1/health/"
PUBLIC="${SITE_URL%/}/api/v1/health/"

echo "=== HRIS native verify ==="
echo "Local:  $LOCAL"
curl -fsS "$LOCAL" && echo && echo "✓ local OK" || { echo "✗ local gagal — systemctl status hris-web"; exit 1; }

if echo "$SITE_URL" | grep -qi '^https://'; then
  echo "Public: $PUBLIC"
  if curl -fsS "$PUBLIC"; then
    echo && echo "✓ HTTPS OK"
  else
    echo "⚠ HTTPS belum OK — cek nginx + certbot"
  fi
fi
