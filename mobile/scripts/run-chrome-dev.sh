#!/usr/bin/env bash
# Jalankan mobile Flutter di Chrome untuk uji ke server publik.
# Chrome dev server (localhost:port acak) butuh CORS dari server — pastikan production
# sudah deploy nginx.conf terbaru, atau pakai flag di bawah untuk dev lokal saja.
set -euo pipefail
cd "$(dirname "$0")/.."

exec flutter run -d chrome \
  --web-browser-flag="--disable-web-security" \
  --web-browser-flag="--user-data-dir=${TMPDIR:-/tmp}/flutter_hris_chrome_dev"
