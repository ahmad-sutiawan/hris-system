#!/usr/bin/env bash
# Cek prasyarat sebelum docker compose up — hentikan dini jika ada masalah.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

fail() { echo -e "${RED}✗ $1${NC}" >&2; exit 1; }
warn() { echo -e "${YELLOW}! $1${NC}"; }
ok()   { echo -e "${GREEN}✓ $1${NC}"; }

MODE="${1:-sqlite}"
HTTP_PORT="${HTTP_PORT:-8080}"

echo "=== HRIS-Lite preflight (${MODE}) ==="
echo ""

# Docker daemon
if ! command -v docker >/dev/null 2>&1; then
  fail "Docker belum terinstall. Lihat deploy/DOCKER.md bagian 'Install Docker'."
fi
if ! docker info >/dev/null 2>&1; then
  fail "Docker daemon tidak jalan. Jalankan: sudo systemctl start docker (lalu logout/login jika baru install)."
fi
ok "Docker daemon aktif"

if ! docker compose version >/dev/null 2>&1; then
  fail "Plugin 'docker compose' tidak ditemukan. Install: docker-compose-plugin"
fi
ok "docker compose tersedia"

# .env
if [ ! -f .env ]; then
  warn "File .env belum ada — akan dibuat dari .env.example"
  cp .env.example .env
fi
ok "File .env ada"

# Load .env for checks (ignore comments)
set -a
# shellcheck disable=SC1091
source <(grep -v '^#' .env | grep -v '^$' | sed 's/\r$//')
set +a

HTTP_PORT="${HTTP_PORT:-8080}"

if [ "${SECRET_KEY:-}" = "change-me-use-openssl-rand-hex-32" ] || [ -z "${SECRET_KEY:-}" ]; then
  fail "SECRET_KEY masih default. Generate: openssl rand -hex 32  lalu paste ke .env"
fi
ok "SECRET_KEY sudah diset"

if [ "${HRIS_FIELD_ENCRYPTION_KEY:-}" = "generate-a-unique-32-char-secret-key" ] || [ -z "${HRIS_FIELD_ENCRYPTION_KEY:-}" ]; then
  fail "HRIS_FIELD_ENCRYPTION_KEY masih default. Generate: openssl rand -hex 32  lalu paste ke .env"
fi
ok "HRIS_FIELD_ENCRYPTION_KEY sudah diset"

if echo "${ALLOWED_HOSTS:-}" | grep -q "your-server-ip"; then
  fail "ALLOWED_HOSTS masih 'your-server-ip'. Ganti dengan IP/domain server (contoh: 192.168.1.50,hris.company.com)"
fi
if [ -z "${ALLOWED_HOSTS:-}" ]; then
  fail "ALLOWED_HOSTS kosong. Isi IP/domain server di .env"
fi
ok "ALLOWED_HOSTS: ${ALLOWED_HOSTS}"

if [ "$MODE" = "mysql" ]; then
  if [ "${DB_ENGINE:-}" != "django.db.backends.mysql" ]; then
    fail "Mode mysql but DB_ENGINE bukan MySQL. Edit .env — lihat deploy/DOCKER.md 'Mode MySQL'"
  fi
  if [ -z "${DB_PASSWORD:-}" ] || [ "${DB_PASSWORD}" = "strong-db-password" ]; then
    fail "DB_PASSWORD masih default/kosong. Set password kuat di .env"
  fi
  if [ -z "${MYSQL_ROOT_PASSWORD:-}" ] || [ "${MYSQL_ROOT_PASSWORD}" = "strong-root-password" ]; then
    fail "MYSQL_ROOT_PASSWORD masih default/kosong. Set password kuat di .env"
  fi
  ok "Konfigurasi MySQL terdeteksi (DB_HOST=${DB_HOST:-mysql})"
else
  if [ "${DB_ENGINE:-django.db.backends.sqlite3}" != "django.db.backends.sqlite3" ]; then
    warn "DB_ENGINE bukan SQLite tapi mode sqlite — pastikan sengaja"
  fi
  ok "Mode SQLite (DB_NAME=${DB_NAME:-/app/data/db.sqlite3})"
fi

# Port check (best effort)
if command -v ss >/dev/null 2>&1; then
  if ss -tln | grep -q ":${HTTP_PORT} "; then
    warn "Port ${HTTP_PORT} sudah dipakai proses lain — ubah HTTP_PORT di .env atau stop proses tersebut"
  else
    ok "Port ${HTTP_PORT} tersedia"
  fi
elif command -v lsof >/dev/null 2>&1; then
  if lsof -i ":${HTTP_PORT}" >/dev/null 2>&1; then
    warn "Port ${HTTP_PORT} sudah dipakai — cek dengan: lsof -i :${HTTP_PORT}"
  else
    ok "Port ${HTTP_PORT} tersedia"
  fi
fi

echo ""
echo -e "${GREEN}Preflight OK — lanjut deploy.${NC}"
