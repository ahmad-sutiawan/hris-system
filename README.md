# HRIS-Lite

Sistem HR end-to-end untuk manufaktur multi-plant — versi simplified dengan strategi **foundation lengkap, fitur utama dulu**.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 6 + Django REST Framework |
| Web UI | HTMX + Tailwind CSS |
| Mobile API | DRF + JWT (Flutter client) |
| Database | SQLite (dev) / PostgreSQL (prod) |
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
docs/
  PRD.md         # Product requirements
  TAD.md         # Technical architecture
```

## Scope Tiers

- **Tier A (Foundation):** Full schema, RBAC, audit, API skeleton — implemented
- **Tier B (MVP features):** Employee, attendance, leave, payroll flows — in progress
- **Tier C (Scaffolded):** Hourly leave, OT before, THR, SSO — schema ready, logic later

## Documentation

See [`docs/PRD.md`](docs/PRD.md), [`docs/TAD.md`](docs/TAD.md), and [`docs/API_FLUTTER.md`](docs/API_FLUTTER.md).
