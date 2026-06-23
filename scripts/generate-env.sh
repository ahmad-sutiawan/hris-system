#!/usr/bin/env bash
# Generate .env aman untuk deploy Docker (SQLite default).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ -f .env ]; then
  echo "File .env sudah ada — tidak ditimpa."
  echo "Hapus manual jika ingin generate ulang: rm .env && $0"
  exit 0
fi

if ! command -v openssl >/dev/null 2>&1; then
  echo "openssl tidak ditemukan. Install: sudo apt install openssl"
  exit 1
fi

SECRET="$(openssl rand -hex 32)"
ENCRYPT="$(openssl rand -hex 32)"

# Deteksi IP LAN untuk ALLOWED_HOSTS
LAN_IP="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
HOSTS="localhost,127.0.0.1"
if [ -n "$LAN_IP" ]; then
  HOSTS="${HOSTS},${LAN_IP}"
fi

cat > .env <<EOF
# Generated $(date -Iseconds) — edit ALLOWED_HOSTS/HRIS_SITE_URL jika perlu

SECRET_KEY=${SECRET}
DEBUG=False
ALLOWED_HOSTS=${HOSTS}
HRIS_SITE_URL=http://${LAN_IP:-127.0.0.1}:8080
HTTP_PORT=8080
HRIS_BIND_HOST=0.0.0.0
HRIS_HTTP_PORT=8080

DB_ENGINE=django.db.backends.sqlite3
DB_NAME=/app/data/db.sqlite3

SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8080,http://localhost:8080${LAN_IP:+,http://${LAN_IP}:8080}
CORS_ALLOWED_ORIGINS=http://127.0.0.1:8080,http://localhost:8080${LAN_IP:+,http://${LAN_IP}:8080}

HRIS_FIELD_ENCRYPTION_KEY=${ENCRYPT}
HRIS_AUDIT_ARCHIVE_DIR=/app/audit_archive
HRIS_DEFAULT_TENANT_SLUG=default

EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=noreply@hris.local
EOF

echo "✓ .env dibuat dengan SECRET_KEY & HRIS_FIELD_ENCRYPTION_KEY random."
echo "  ALLOWED_HOSTS=${HOSTS}"
echo "  HRIS_SITE_URL=http://${LAN_IP:-127.0.0.1}:8080"
echo ""
echo "Review .env lalu jalankan: ./scripts/docker-up.sh sqlite"
