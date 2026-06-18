"""
Salin data master dari database SQLite lama ke database aktif (MySQL).

Hanya menyalin referensi tenant-scoped (libur, komponen gaji, PPh21/TER/PTKP,
kode absensi, jenis lembur/cuti, shift, dll.) — bukan data transaksional
karyawan yang sudah ada di MySQL.

Relasi di-remap lewat slug tenant + kode plant/kategori, bukan ID mentah.
"""

from __future__ import annotations

import sqlite3
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.attendance.models import AttendanceCode, OvertimeType
from apps.core.models import HolidayCalendar, Plant, Tenant
from apps.leave.models import LeaveType
from apps.organization.models import LegalEntity
from apps.payroll.models import (
    Pph21TerBracket,
    Pph21TerCategory,
    Pph21TerPtkpMapping,
    SalaryComponent,
    ShiftAllowanceRate,
)
from apps.shifts.models import Shift


class Command(BaseCommand):
    help = (
        "Salin data master dari SQLite lama ke DB aktif. "
        "Hanya record yang belum ada (by natural key) yang ditambahkan."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            type=str,
            default=str(Path(settings.BASE_DIR) / "db.sqlite3"),
            help="Path ke file SQLite sumber (default: db.sqlite3 di root proyek)",
        )
        parser.add_argument(
            "--source-tenant-slug",
            type=str,
            default="default",
            help="Slug tenant di SQLite yang akan disalin",
        )
        parser.add_argument(
            "--target-tenant-slug",
            type=str,
            default="",
            help="Slug tenant di MySQL tujuan (default: sama dengan source)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Tampilkan rencana tanpa menulis ke database",
        )

    def handle(self, *args, **options):
        source_path = Path(options["source"])
        if not source_path.is_file():
            raise CommandError(f"File SQLite tidak ditemukan: {source_path}")

        source_slug = options["source_tenant_slug"]
        target_slug = options["target_tenant_slug"] or source_slug
        dry_run = options["dry_run"]

        reader = _SQLiteReader(source_path)
        try:
            source_tenant = reader.get_tenant(source_slug)
            if not source_tenant:
                raise CommandError(
                    f"Tenant slug '{source_slug}' tidak ditemukan di SQLite."
                )

            try:
                target_tenant = Tenant.objects.get(slug=target_slug)
            except Tenant.DoesNotExist as exc:
                raise CommandError(
                    f"Tenant slug '{target_slug}' tidak ditemukan di database aktif."
                ) from exc

            plant_map = _build_plant_map(reader, source_tenant["id"], target_tenant)
            stats = _SyncStats()

            sync_fn = _dry_run_sync if dry_run else _live_sync
            with transaction.atomic():
                sync_fn(reader, source_tenant, target_tenant, plant_map, stats)
                if dry_run:
                    transaction.set_rollback(True)

        finally:
            reader.close()

        mode = "DRY-RUN" if dry_run else "SELESAI"
        self.stdout.write(self.style.SUCCESS(f"\n[{mode}] Ringkasan sinkronisasi:"))
        for label, created, skipped in stats.rows:
            self.stdout.write(f"  {label}: +{created} baru, {skipped} sudah ada")
        if dry_run:
            self.stdout.write(
                self.style.WARNING("Dry-run — tidak ada perubahan yang disimpan.")
            )


class _SyncStats:
    def __init__(self):
        self.rows: list[tuple[str, int, int]] = []

    def add(self, label: str, created: int, skipped: int):
        self.rows.append((label, created, skipped))


class _SQLiteReader:
    def __init__(self, path: Path):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row

    def close(self):
        self.conn.close()

    def fetchall(self, sql: str, params=()):
        return self.conn.execute(sql, params).fetchall()

    def fetchone(self, sql: str, params=()):
        return self.conn.execute(sql, params).fetchone()

    def get_tenant(self, slug: str):
        return self.fetchone(
            "SELECT id, slug, name FROM core_tenant WHERE slug = ?",
            (slug,),
        )

    def get_plant_code(self, plant_id: int | None) -> str | None:
        if plant_id is None:
            return None
        row = self.fetchone(
            "SELECT code FROM core_plant WHERE id = ?",
            (plant_id,),
        )
        return row["code"] if row else None


def _build_plant_map(reader: _SQLiteReader, source_tenant_id: int, target_tenant: Tenant):
    """Map SQLite plant_id → MySQL Plant via kode cabang."""
    mapping: dict[int, Plant | None] = {}
    rows = reader.fetchall(
        "SELECT id, code FROM core_plant WHERE tenant_id = ?",
        (source_tenant_id,),
    )
    target_by_code = {
        p.code: p for p in Plant.objects.filter(tenant=target_tenant)
    }
    for row in rows:
        mapping[row["id"]] = target_by_code.get(row["code"])
    mapping[None] = None
    return mapping


def _dry_run_sync(reader, source_tenant, target_tenant, plant_map, stats):
    _sync_all(reader, source_tenant, target_tenant, plant_map, stats, dry_run=True)


def _live_sync(reader, source_tenant, target_tenant, plant_map, stats):
    _sync_all(reader, source_tenant, target_tenant, plant_map, stats, dry_run=False)


def _sync_all(reader, source_tenant, target_tenant, plant_map, stats, *, dry_run: bool):
    tid = source_tenant["id"]
    tenant = target_tenant

    _sync_holidays(reader, tid, tenant, plant_map, stats, dry_run=dry_run)
    _sync_salary_components(reader, tid, tenant, stats, dry_run=dry_run)
    _sync_pph21(reader, tid, tenant, stats, dry_run=dry_run)
    _sync_shift_allowance_rates(reader, tid, tenant, stats, dry_run=dry_run)
    _sync_attendance_codes(reader, tid, tenant, stats, dry_run=dry_run)
    _sync_overtime_types(reader, tid, tenant, stats, dry_run=dry_run)
    _sync_leave_types(reader, tid, tenant, stats, dry_run=dry_run)
    _sync_legal_entities(reader, tid, tenant, stats, dry_run=dry_run)
    _sync_shifts(reader, tid, tenant, stats, dry_run=dry_run)


def _sync_holidays(reader, source_tid, tenant, plant_map, stats, *, dry_run):
    created = skipped = 0
    rows = reader.fetchall(
        """
        SELECT name, holiday_date, holiday_type, plant_id, is_active
        FROM core_holidaycalendar
        WHERE tenant_id = ?
        ORDER BY holiday_date, name
        """,
        (source_tid,),
    )
    for row in rows:
        plant = plant_map.get(row["plant_id"])
        if row["plant_id"] and plant is None:
            code = reader.get_plant_code(row["plant_id"])
            raise CommandError(
                f"Plant '{code}' (id SQLite {row['plant_id']}) "
                f"belum ada di tenant '{tenant.slug}' — buat plant dulu."
            )
        exists = HolidayCalendar.objects.filter(
            tenant=tenant,
            holiday_date=row["holiday_date"],
            name=row["name"],
        ).exists()
        if exists:
            skipped += 1
            continue
        if not dry_run:
            HolidayCalendar.objects.create(
                tenant=tenant,
                name=row["name"],
                holiday_date=row["holiday_date"],
                holiday_type=row["holiday_type"],
                plant=plant,
                is_active=bool(row["is_active"]),
            )
        created += 1
    stats.add("Holiday Calendar", created, skipped)


def _sync_salary_components(reader, source_tid, tenant, stats, *, dry_run):
    created = skipped = 0
    rows = reader.fetchall(
        """
        SELECT code, name, component_type, formula_key, is_active
        FROM payroll_salarycomponent
        WHERE tenant_id = ?
        ORDER BY code
        """,
        (source_tid,),
    )
    for row in rows:
        exists = SalaryComponent.objects.filter(tenant=tenant, code=row["code"]).exists()
        if exists:
            skipped += 1
            continue
        if not dry_run:
            SalaryComponent.objects.create(
                tenant=tenant,
                code=row["code"],
                name=row["name"],
                component_type=row["component_type"],
                formula_key=row["formula_key"] or "",
                is_active=bool(row["is_active"]),
            )
        created += 1
    stats.add("Salary Component", created, skipped)


def _sync_pph21(reader, source_tid, tenant, stats, *, dry_run):
    cat_created = cat_skipped = 0
    ptkp_created = ptkp_skipped = 0
    bracket_created = bracket_skipped = 0

    cat_rows = reader.fetchall(
        """
        SELECT id, code, name, description, is_active
        FROM payroll_pph21tercategory
        WHERE tenant_id = ?
        ORDER BY code
        """,
        (source_tid,),
    )
    category_by_sqlite_id: dict[int, Pph21TerCategory] = {}

    for row in cat_rows:
        category, was_created = (
            (Pph21TerCategory.objects.get(tenant=tenant, code=row["code"]), False)
            if Pph21TerCategory.objects.filter(tenant=tenant, code=row["code"]).exists()
            else (None, True)
        )
        if was_created:
            if not dry_run:
                category = Pph21TerCategory.objects.create(
                    tenant=tenant,
                    code=row["code"],
                    name=row["name"],
                    description=row["description"] or "",
                    is_active=bool(row["is_active"]),
                )
            cat_created += 1
        else:
            cat_skipped += 1
        if category is not None:
            category_by_sqlite_id[row["id"]] = category

    ptkp_rows = reader.fetchall(
        """
        SELECT m.ptkp_code, m.category_id, c.code AS category_code
        FROM payroll_pph21terptkpmapping m
        JOIN payroll_pph21tercategory c ON c.id = m.category_id
        WHERE m.tenant_id = ?
        ORDER BY m.ptkp_code
        """,
        (source_tid,),
    )
    for row in ptkp_rows:
        if Pph21TerPtkpMapping.objects.filter(
            tenant=tenant, ptkp_code=row["ptkp_code"]
        ).exists():
            ptkp_skipped += 1
            continue
        category = category_by_sqlite_id.get(row["category_id"])
        if category is None and not dry_run:
            category = Pph21TerCategory.objects.get(
                tenant=tenant, code=row["category_code"]
            )
        if not dry_run:
            Pph21TerPtkpMapping.objects.create(
                tenant=tenant,
                category=category,
                ptkp_code=row["ptkp_code"],
            )
        ptkp_created += 1

    bracket_rows = reader.fetchall(
        """
        SELECT b.bracket_no, b.income_from, b.income_to, b.rate, b.category_id, c.code
        FROM payroll_pph21terbracket b
        JOIN payroll_pph21tercategory c ON c.id = b.category_id
        WHERE b.tenant_id = ?
        ORDER BY c.code, b.bracket_no
        """,
        (source_tid,),
    )
    for row in bracket_rows:
        category = category_by_sqlite_id.get(row["category_id"])
        if category is None and not dry_run:
            category = Pph21TerCategory.objects.get(tenant=tenant, code=row["code"])
        exists = Pph21TerBracket.objects.filter(
            tenant=tenant,
            category__code=row["code"],
            bracket_no=row["bracket_no"],
        ).exists()
        if exists:
            bracket_skipped += 1
            continue
        if not dry_run:
            Pph21TerBracket.objects.create(
                tenant=tenant,
                category=category,
                bracket_no=row["bracket_no"],
                income_from=Decimal(str(row["income_from"])),
                income_to=(
                    Decimal(str(row["income_to"]))
                    if row["income_to"] is not None
                    else None
                ),
                rate=Decimal(str(row["rate"])),
            )
        bracket_created += 1

    stats.add("PPh21 TER Category", cat_created, cat_skipped)
    stats.add("PPh21 PTKP Mapping", ptkp_created, ptkp_skipped)
    stats.add("PPh21 TER Bracket", bracket_created, bracket_skipped)


def _sync_shift_allowance_rates(reader, source_tid, tenant, stats, *, dry_run):
    created = skipped = 0
    rows = reader.fetchall(
        """
        SELECT code, name, amount, is_active
        FROM payroll_shiftallowancerate
        WHERE tenant_id = ?
        ORDER BY code
        """,
        (source_tid,),
    )
    for row in rows:
        if ShiftAllowanceRate.objects.filter(tenant=tenant, code=row["code"]).exists():
            skipped += 1
            continue
        if not dry_run:
            ShiftAllowanceRate.objects.create(
                tenant=tenant,
                code=row["code"],
                name=row["name"],
                amount=Decimal(str(row["amount"])),
                is_active=bool(row["is_active"]),
            )
        created += 1
    stats.add("Shift Allowance Rate", created, skipped)


def _sync_attendance_codes(reader, source_tid, tenant, stats, *, dry_run):
    created = skipped = 0
    rows = reader.fetchall(
        """
        SELECT code, label, payroll_impact, is_active
        FROM attendance_attendancecode
        WHERE tenant_id = ?
        ORDER BY code
        """,
        (source_tid,),
    )
    for row in rows:
        if AttendanceCode.objects.filter(tenant=tenant, code=row["code"]).exists():
            skipped += 1
            continue
        if not dry_run:
            AttendanceCode.objects.create(
                tenant=tenant,
                code=row["code"],
                label=row["label"],
                payroll_impact=row["payroll_impact"],
                is_active=bool(row["is_active"]),
            )
        created += 1
    stats.add("Attendance Code", created, skipped)


def _sync_overtime_types(reader, source_tid, tenant, stats, *, dry_run):
    created = skipped = 0
    rows = reader.fetchall(
        """
        SELECT code, name, day_category, hour_from, hour_to, multiplier, is_active
        FROM attendance_overtimetype
        WHERE tenant_id = ?
        ORDER BY code
        """,
        (source_tid,),
    )
    for row in rows:
        if OvertimeType.objects.filter(tenant=tenant, code=row["code"]).exists():
            skipped += 1
            continue
        if not dry_run:
            OvertimeType.objects.create(
                tenant=tenant,
                code=row["code"],
                name=row["name"],
                day_category=row["day_category"],
                hour_from=row["hour_from"],
                hour_to=row["hour_to"],
                multiplier=Decimal(str(row["multiplier"])),
                is_active=bool(row["is_active"]),
            )
        created += 1
    stats.add("Overtime Type", created, skipped)


def _sync_leave_types(reader, source_tid, tenant, stats, *, dry_run):
    created = skipped = 0
    rows = reader.fetchall(
        """
        SELECT code, name, is_paid, default_quota_days, requires_attachment, is_active
        FROM leave_leavetype
        WHERE tenant_id = ?
        ORDER BY code
        """,
        (source_tid,),
    )
    for row in rows:
        if LeaveType.objects.filter(tenant=tenant, code=row["code"]).exists():
            skipped += 1
            continue
        if not dry_run:
            LeaveType.objects.create(
                tenant=tenant,
                code=row["code"],
                name=row["name"],
                is_paid=bool(row["is_paid"]),
                default_quota_days=Decimal(str(row["default_quota_days"])),
                requires_attachment=bool(row["requires_attachment"]),
                is_active=bool(row["is_active"]),
            )
        created += 1
    stats.add("Leave Type", created, skipped)


def _sync_legal_entities(reader, source_tid, tenant, stats, *, dry_run):
    created = skipped = 0
    rows = reader.fetchall(
        """
        SELECT name, npwp, is_active
        FROM organization_legalentity
        WHERE tenant_id = ?
        ORDER BY name
        """,
        (source_tid,),
    )
    for row in rows:
        if LegalEntity.objects.filter(tenant=tenant, name=row["name"]).exists():
            skipped += 1
            continue
        if not dry_run:
            LegalEntity.objects.create(
                tenant=tenant,
                name=row["name"],
                npwp=row["npwp"] or "",
                is_active=bool(row["is_active"]),
            )
        created += 1
    stats.add("Legal Entity", created, skipped)


def _sync_shifts(reader, source_tid, tenant, stats, *, dry_run):
    created = skipped = 0
    rows = reader.fetchall(
        """
        SELECT code, name, label, scheduled_check_in, scheduled_check_out,
               break_minutes, grace_period_minutes, schedule_working_hours,
               cross_day, shift_allowance_code, is_active
        FROM shifts_shift
        WHERE tenant_id = ?
        ORDER BY code
        """,
        (source_tid,),
    )
    for row in rows:
        if Shift.objects.filter(tenant=tenant, code=row["code"]).exists():
            skipped += 1
            continue
        if not dry_run:
            Shift.objects.create(
                tenant=tenant,
                code=row["code"],
                name=row["name"],
                label=row["label"] or "",
                scheduled_check_in=row["scheduled_check_in"],
                scheduled_check_out=row["scheduled_check_out"],
                break_minutes=row["break_minutes"],
                grace_period_minutes=row["grace_period_minutes"],
                schedule_working_hours=Decimal(str(row["schedule_working_hours"])),
                cross_day=bool(row["cross_day"]),
                shift_allowance_code=row["shift_allowance_code"] or "",
                is_active=bool(row["is_active"]),
            )
        created += 1
    stats.add("Shift", created, skipped)
