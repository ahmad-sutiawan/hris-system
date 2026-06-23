#!/usr/bin/env bash
# Perbaikan login production hris.besibps.com
#   cd /var/www/hris-system && sudo bash scripts/fix-production-login.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

COMPOSE="docker compose --profile mysql"
RUN="$COMPOSE exec -T web"

echo "=============================================="
echo " HRIS — perbaikan login production"
echo "=============================================="

if [ ! -f .env ]; then
  echo "ERROR: .env tidak ada. Salin deploy/env.bps.production dulu."
  exit 1
fi

echo ""
echo "0) Pull kode terbaru..."
git fetch origin develop
git pull origin develop

if [ ! -f scripts/fix-production-login.sh ]; then
  echo "ERROR: kode belum ter-update. Commit develop terbaru belum ada di server."
  exit 1
fi

# shellcheck disable=SC1091
source <(grep -v '^#' .env | grep -v '^$' | sed 's/\r$//')

BPS_ENCRYPTION_KEY="dev-only-32-char-encryption-key!!"
WRONG_KEY="0e409590449cd788616afee8ff8db95d9320e1325b7b98ccb0d32128308b9063"

echo ""
echo "1) Cek HRIS_FIELD_ENCRYPTION_KEY..."
if [ -z "${HRIS_FIELD_ENCRYPTION_KEY:-}" ]; then
  echo "ERROR: HRIS_FIELD_ENCRYPTION_KEY kosong di .env"
  exit 1
fi

if [ "${HRIS_FIELD_ENCRYPTION_KEY}" = "$WRONG_KEY" ]; then
  echo "   Key salah (baru digenerate) — auto-fix ke key bps_hris lokal..."
  if grep -q '^HRIS_FIELD_ENCRYPTION_KEY=' .env; then
    sed -i "s|^HRIS_FIELD_ENCRYPTION_KEY=.*|HRIS_FIELD_ENCRYPTION_KEY=${BPS_ENCRYPTION_KEY}|" .env
  else
    echo "HRIS_FIELD_ENCRYPTION_KEY=${BPS_ENCRYPTION_KEY}" >> .env
  fi
  HRIS_FIELD_ENCRYPTION_KEY="$BPS_ENCRYPTION_KEY"
  echo "   Diperbarui → ${BPS_ENCRYPTION_KEY}"
else
  echo "   Key terdeteksi (${#HRIS_FIELD_ENCRYPTION_KEY} karakter)"
fi

echo ""
echo "2) Rebuild web (no cache) & restart..."
$COMPOSE build --no-cache web
$COMPOSE up -d

echo ""
echo "3) Tunggu web healthy..."
for i in $(seq 1 36); do
  if $COMPOSE ps web 2>/dev/null | grep -q healthy; then
    echo "   web healthy"
    break
  fi
  sleep 5
  if [ "$i" -eq 36 ]; then
    echo "   web belum healthy — cek: $COMPOSE logs web --tail 80"
  fi
done

echo ""
echo "4) Verifikasi env di dalam container..."
$RUN python -c "
import os
k = os.environ.get('HRIS_FIELD_ENCRYPTION_KEY','')
print('HRIS_FIELD_ENCRYPTION_KEY in container:', k[:8]+'...' if len(k)>8 else k, f'({len(k)} chars)')
"

echo ""
echo "5) Migrate + repair production..."
$RUN python manage.py migrate --noinput
$RUN python manage.py repair_production --bootstrap-admin --tenant default

echo ""
echo "6) Health check..."
SITE="${HRIS_SITE_URL:-https://hris.besibps.com}"
curl -fsS "${SITE%/}/api/v1/health/" && echo

echo ""
echo "=============================================="
echo " Selesai. Coba login:"
echo "   Admin    : admin / Admin123456!"
echo "   Karyawan : NIK + Employee ID"
echo ""
echo " Jika masih 500:"
echo "   $COMPOSE logs web --tail 80"
echo "=============================================="
