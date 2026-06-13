# HRIS-Lite

Sistem HR end-to-end untuk manufaktur multi-plant — versi simplified dengan strategi **foundation lengkap, fitur utama dulu**.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 6 + Django REST Framework |
| Web UI | HTMX + Tailwind CSS |
| Mobile API | DRF + JWT (Flutter client) |
| Database | SQLite (dev) / MySQL 8 (prod) |
| API Docs | drf-spectacular (OpenAPI/Swagger) |

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Login web: `admin` / `Admin123456!`

Demo users:

| User | Password | Role |
|---|---|---|
| admin | Admin123456! | Admin |
| budi | Employee123! | Employee (clock in/out, cuti) |
| manager | Manager123! | Manager (approve cuti) |

## URLs

| URL | Description |
|---|---|
| `/` | Dashboard (HTMX web) |
| `/admin/` | Django admin |
| `/api/v1/` | REST API (Flutter/mobile) |
| `/api/v1/auth/token/` | JWT obtain pair |
| `/api/docs/` | Swagger UI |
| `mobile/` | Flutter employee app (see [`mobile/README.md`](mobile/README.md)) |

## Project Structure

```
apps/
  core/          # Tenant, Plant, User, Audit, FeatureFlag
  organization/  # LegalEntity, Department, JobPosition
  employees/     # Employee master data
  shifts/        # Shift & assignment
  attendance/    # Attendance + DailyTimesheet (24 kolom)
  leave/         # Leave types, balance, requests
  payroll/       # Payroll run & payslip
  web/           # HTMX server-rendered views
mobile/        # Flutter employee app
```

## Scope Tiers

- **Tier A (Foundation):** Full schema, RBAC, audit, API skeleton — implemented
- **Tier B (MVP features):** Employee, attendance, leave, payroll flows — in progress
- **Tier C (Scaffolded):** Hourly leave, OT before, THR, SSO — schema ready, logic later

## Production (Docker)

```bash
cp .env.example .env
nano .env    # SECRET_KEY, ALLOWED_HOSTS, DB_* (lihat .env.example)
chmod +x scripts/*.sh
./scripts/docker-up.sh mysql     # production MySQL
# ./scripts/docker-up.sh sqlite  # uji coba
docker compose exec web python manage.py seed_demo
docker compose exec web python manage.py encrypt_employee_data
```

| Script | Fungsi |
|---|---|
| `scripts/docker-up.sh sqlite` | Deploy SQLite (default) |
| `scripts/docker-up.sh mysql` | Deploy MySQL + cron backup |
| `scripts/docker-preflight.sh` | Cek `.env` sebelum deploy |
| `scripts/docker-verify.sh` | Cek health setelah deploy |

| Service | Port | Keterangan |
|---|---|---|
| nginx | 8080 (default) | Reverse proxy + media |
| web | internal | Gunicorn + WhiteNoise |
| mysql | internal | Profile `--profile mysql` |
| cron | internal | Arsip audit + backup (MySQL) |

**Health check:** `GET /api/v1/health/`

**Cron manual:**
```bash
python manage.py archive_audit_logs
python manage.py backup_database
```

Dokumentasi PRD/TAD/API Flutter disimpan lokal di folder `docs/` (tidak di repository).
