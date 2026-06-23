# Deploy HRIS tanpa Docker (VPS + nginx host)

Sama seperti `1.bgmtracking.com`: nginx di port 80/443, Django di socket/port lokal.

## Arsitektur

```
https://hris.besibps.com  →  nginx host  →  127.0.0.1:8001  →  uvicorn (systemd hris-web)
https://1.bgmtracking.com →  nginx host  →  gunicorn.sock   →  (tidak terganggu)
MySQL host 127.0.0.1:3306 → database `hris_system`
```

## 1. Matikan Docker HRIS

```bash
cd /var/www/hris-system
docker compose --profile mysql down
# Jangan docker compose down -v kecuali sengaja hapus volume
```

## 2. MySQL di host

```bash
sudo mysql -e "
CREATE DATABASE IF NOT EXISTS hris_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'hris'@'localhost' IDENTIFIED BY 'PASSWORD_KUAT';
GRANT ALL PRIVILEGES ON hris_system.* TO 'hris'@'localhost';
FLUSH PRIVILEGES;
"
```

## 3. `.env`

```bash
cp ops/native/env.production.example .env
nano .env
```

Wajib: `SECRET_KEY`, `HRIS_FIELD_ENCRYPTION_KEY`, `DB_PASSWORD`, `DB_HOST=127.0.0.1`.

## 4. Deploy

```bash
git pull
chmod +x scripts/native-deploy.sh
sudo ./scripts/native-deploy.sh
```

## 5. SSL (jika belum)

```bash
sudo certbot --nginx -d hris.besibps.com
curl -fsS https://hris.besibps.com/api/v1/health/
```

## 6. Bootstrap

```bash
sudo -u www-data bash -c 'cd /var/www/hris-system && .venv/bin/python manage.py repair_production --bootstrap-admin --tenant default'
```

## Operasi

```bash
sudo systemctl status hris-web
sudo systemctl restart hris-web
sudo journalctl -u hris-web -f
cd /var/www/hris-system && git pull
sudo -u www-data .venv/bin/pip install -r requirements.txt
sudo -u www-data .venv/bin/python manage.py migrate
sudo -u www-data .venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart hris-web
```

## Import data production

Restore dump MySQL ke `hris_system` (bukan SQLite lokal), pastikan `HRIS_FIELD_ENCRYPTION_KEY` sama dengan saat data dienkripsi.
