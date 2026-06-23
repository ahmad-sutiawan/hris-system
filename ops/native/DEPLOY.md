# Deploy HRIS di VPS

## Satu perintah

```bash
cd /var/www/hris-system
git pull
cp ops/native/env.production.example .env   # pertama kali saja
nano .env                                   # SECRET_KEY, DB_PASSWORD
chmod +x scripts/*.sh
sudo ./scripts/deploy.sh --fresh-db
```

`--fresh-db` = kosongkan database `hris_system` lalu migrate ulang (DB bersih).

Update rutin (tanpa hapus data):

```bash
sudo ./scripts/deploy.sh --pull
```

## Admin

Tidak ada bootstrap otomatis. Setelah deploy:

```bash
sudo -u www-data bash -c 'cd /var/www/hris-system && .venv/bin/python manage.py createsuperuser'
```

## Import data karyawan (opsional)

```bash
bash scripts/import-bps-hris.sh /path/to/dump.sql
```

## Troubleshooting

```bash
journalctl -u hris-web -n 80 --no-pager
curl -fsS http://127.0.0.1:8001/api/v1/health/
```
