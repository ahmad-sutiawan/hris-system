#!/usr/bin/env bash
# Perbaikan login production hris.besibps.com — jalankan di server sebagai root.
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
  echo "ERROR: .env tidak ada. Salin deploy/env.production.example dulu."
  exit 1
fi

# shellcheck disable=SC1091
source <(grep -v '^#' .env | grep -v '^$' | sed 's/\r$//')

echo ""
echo "1) Cek HRIS_FIELD_ENCRYPTION_KEY..."
if [ -z "${HRIS_FIELD_ENCRYPTION_KEY:-}" ]; then
  echo "ERROR: HRIS_FIELD_ENCRYPTION_KEY kosong di .env"
  exit 1
fi
echo "   Key terdeteksi (${#HRIS_FIELD_ENCRYPTION_KEY} karakter)"

if [ "${HRIS_FIELD_ENCRYPTION_KEY:-}" = "0e409590449cd788616afee8ff8db95d9320e1325b7b98ccb0d32128308b9063" ]; then
  echo ""
  echo "   PERINGATAN: Key ini baru digenerate — tidak cocok dengan data bps_hris lokal."
  echo "   Jika sudah import dump bps_hris, ganti di .env menjadi:"
  echo "   HRIS_FIELD_ENCRYPTION_KEY=dev-only-32-char-encryption-key!!"
  echo ""
fi

echo ""
echo "2) Rebuild & restart container..."
$COMPOSE up -d --build

echo ""
echo "3) Tunggu web healthy..."
for i in $(seq 1 30); do
  if $COMPOSE ps web 2>/dev/null | grep -q healthy; then
    echo "   web healthy"
    break
  fi
  sleep 5
  if [ "$i" -eq 30 ]; then
    echo "   web belum healthy — lanjut repair (cek log jika gagal)"
  fi
done

echo ""
echo "4) Migrate + repair production..."
$RUN python manage.py migrate --noinput
$RUN python manage.py repair_production --bootstrap-admin --tenant default

echo ""
echo "5) Health check..."
SITE="${HRIS_SITE_URL:-https://hris.besibps.com}"
curl -fsS "${SITE%/}/api/v1/health/" && echo

echo ""
echo "=============================================="
echo " Selesai. Coba login:"
echo "   Admin : admin / Admin123456!  (ganti setelah berhasil)"
echo "   Karyawan: NIK + Employee ID"
echo ""
echo " Jika masih 500:"
echo "   $COMPOSE logs web --tail 80"
echo "=============================================="
