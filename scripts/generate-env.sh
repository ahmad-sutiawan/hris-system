#!/usr/bin/env bash
# Generate .env untuk development lokal.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ -f .env ]; then
  echo "File .env sudah ada — tidak ditimpa."
  exit 0
fi

SECRET="$(openssl rand -hex 32)"
ENCRYPT="$(openssl rand -hex 32)"
LAN_IP="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
HOSTS="localhost,127.0.0.1"
[ -n "$LAN_IP" ] && HOSTS="${HOSTS},${LAN_IP}"

cat > .env <<EOF
SECRET_KEY=${SECRET}
DEBUG=True
ALLOWED_HOSTS=${HOSTS}
HRIS_SITE_URL=http://${LAN_IP:-127.0.0.1}:8000

DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3

SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8000,http://localhost:8000${LAN_IP:+,http://${LAN_IP}:8000}
CORS_ALLOWED_ORIGINS=http://127.0.0.1:8000,http://localhost:8000${LAN_IP:+,http://${LAN_IP}:8000}
CORS_ALLOW_FLUTTER_DEV=True

HRIS_FIELD_ENCRYPTION_KEY=${ENCRYPT}
HRIS_AUDIT_ARCHIVE_DIR=audit_archive
HRIS_DEFAULT_TENANT_SLUG=default
HRIS_ENABLE_ADMIN_CONSOLE=False

EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=noreply@hris.local
EOF

echo "✓ .env dibuat. Lanjut:"
echo "  python3 -m venv .venv && source .venv/bin/activate"
echo "  pip install -r requirements.txt"
echo "  python manage.py migrate && python manage.py runserver"
