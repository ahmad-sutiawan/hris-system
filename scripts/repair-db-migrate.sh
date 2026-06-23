#!/usr/bin/env bash
# Perbaiki migrate gagal (Table already exists) — jalankan di server production.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

COMPOSE="docker compose --profile mysql"
ACTION="${1:-status}"

if [ -f .env ]; then
  # shellcheck disable=SC1091
  set -a
  source <(grep -v '^#' .env | grep -v '^$' | sed 's/\r$//')
  set +a
fi

run_django() {
  $COMPOSE run --rm --no-deps --entrypoint python web manage.py "$@"
}

mysql_root() {
  $COMPOSE exec -T mysql mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" "$@"
}

case "$ACTION" in
  status)
    echo "=== Tabel di hris_system ==="
    mysql_root -e "USE ${DB_NAME:-hris_system}; SHOW TABLES;"
    echo ""
    echo "=== django_migrations (20 terakhir) ==="
    mysql_root -e "USE ${DB_NAME:-hris_system}; SELECT app, name FROM django_migrations ORDER BY id DESC LIMIT 20;"
    echo ""
    echo "=== Employee count ==="
    mysql_root -e "USE ${DB_NAME:-hris_system}; SELECT COUNT(*) AS employees FROM employees_employee;" 2>/dev/null \
      || echo "(tabel employees_employee belum ada)"
    ;;
  migrate)
    echo "→ migrate --fake-initial (bypass entrypoint)"
    run_django migrate --fake-initial --noinput
    echo "→ restart web"
    $COMPOSE up -d --force-recreate web nginx
    ;;
  reset-db)
    echo "PERINGATAN: menghapus semua data di database ${DB_NAME:-hris_system}."
    echo "Backup dulu jika perlu: docker compose exec web python manage.py backup_database"
    read -r -p "Ketik YES untuk lanjut: " confirm
    if [ "$confirm" != "YES" ]; then
      echo "Dibatalkan."
      exit 1
    fi
    $COMPOSE stop web worker cron nginx
    mysql_root -e "
      DROP DATABASE IF EXISTS \`${DB_NAME:-hris_system}\`;
      CREATE DATABASE \`${DB_NAME:-hris_system}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
      GRANT ALL PRIVILEGES ON \`${DB_NAME:-hris_system}\`.* TO '${DB_USER:-hris}'@'%';
      FLUSH PRIVILEGES;
    "
    echo "→ start web dulu (migrate hanya di sini)"
    $COMPOSE up -d --build --force-recreate web
    echo "→ tunggu web healthy..."
    for i in $(seq 1 30); do
      if $COMPOSE ps web --format '{{.Status}}' 2>/dev/null | grep -qi healthy; then
        echo "web healthy"
        break
      fi
      if [ "$i" -eq 30 ]; then
        echo "web belum healthy — cek: $COMPOSE logs web --tail 80" >&2
        exit 1
      fi
      sleep 5
    done
    $COMPOSE up -d worker cron nginx
    echo "→ tunggu web healthy, lalu:"
    echo "   curl -fsS http://127.0.0.1:\${HRIS_HTTP_PORT:-8081}/api/v1/health/"
    echo "   docker compose exec web python manage.py repair_production --bootstrap-admin"
    ;;
  *)
    echo "Usage: $0 [status|migrate|reset-db]"
    exit 1
    ;;
esac
