#!/usr/bin/env bash
# Pasang site nginx host untuk HRIS.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${ROOT}/ops/native/nginx-hris.besibps.com.conf"
DEST_NAME="hris.besibps.com"
AVAILABLE="/etc/nginx/sites-available/${DEST_NAME}"
ENABLED="/etc/nginx/sites-enabled/${DEST_NAME}"

if [ ! -f "$SRC" ]; then
  echo "File tidak ditemukan: $SRC" >&2
  exit 1
fi

if [ "$(id -u)" -ne 0 ]; then
  echo "Butuh root: sudo $0" >&2
  exit 1
fi

cp "$SRC" "$AVAILABLE"
ln -sf "$AVAILABLE" "$ENABLED"
nginx -t
systemctl reload nginx
echo "OK: nginx → 127.0.0.1:8001"
echo "Lanjut: certbot --nginx -d hris.besibps.com"
