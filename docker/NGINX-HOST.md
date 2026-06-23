# HRIS di belakang nginx host

Gunakan jika port 80/443 sudah dipakai nginx lain di VPS yang sama.

## Arsitektur

```
Internet :443 → nginx host (hris.besibps.com)
                    ↓
              127.0.0.1:8081 → container nginx → web:8000
```

## `.env`

```env
HRIS_BIND_HOST=127.0.0.1
HRIS_HTTP_PORT=8081
HRIS_SITE_URL=https://hris.besibps.com
SECURE_SSL_REDIRECT=False
```

## Deploy

```bash
docker compose --profile mysql up -d --build
curl -fsS http://127.0.0.1:8081/api/v1/health/
./scripts/install-nginx-host.sh
sudo certbot --nginx -d hris.besibps.com
```
