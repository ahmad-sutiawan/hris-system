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

Karyawan: **username** = NIK atau Employee ID, **password** = Employee ID.

Contoh (setelah `seed_demo` atau `sync_employee_credentials`):

| Karyawan | Employee ID | NIK | Login mobile (NIK + Employee ID) |
|---|---|---|---|
| Budi | `PLT01-2026-001` | `3201010101900001` | NIK `3201010101900001` / ID `PLT01-2026-001` |
| Aan Ansori | `1704` | `3604231902010003` | NIK `3604231902010003` / ID `1704` |

Admin/HR: username `admin` / password `Admin123456!` (bukan NIK/Employee ID).

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

## Production (VPS)

```bash
cp ops/native/env.production.example .env
nano .env
chmod +x scripts/*.sh
sudo ./scripts/deploy.sh --fresh-db
```

Satu script: venv, migrate, systemd, nginx, SSL, health check.  
DB kosong (`--fresh-db`); admin via `createsuperuser` manual.

Panduan: [`ops/native/DEPLOY.md`](ops/native/DEPLOY.md)

| Script | Fungsi |
|---|---|
| **`scripts/deploy.sh`** | **Deploy lengkap** (`--pull`, `--fresh-db`) |
| `scripts/import-bps-hris.sh` | Import dump MySQL |
| `scripts/fix-production-login.sh` | Perbaiki key enkripsi / restart |

**Health check:** `GET /api/v1/health/`

**Cron manual:**
```bash
python manage.py archive_audit_logs
python manage.py backup_database
```

Dokumentasi PRD/TAD/API Flutter disimpan lokal di folder `docs/` (tidak di repository).
