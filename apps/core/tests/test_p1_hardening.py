"""P1 production hardening tests."""

from datetime import date
from decimal import Decimal

from urllib.parse import unquote

from django.test import TestCase, override_settings

from apps.core.media_serving import build_media_url, sign_media_path, verify_media_signature
from apps.core.models import Plant, Tenant
from apps.employees.models import Employee
from apps.payroll.services.ter import build_ter_cache, seed_ter_master
from apps.payroll.services.calculator import calc_pph21


@override_settings(HRIS_MEDIA_PROTECTED=True, HRIS_MEDIA_URL_TTL_SECONDS=3600)
class MediaProtectionTests(TestCase):
    def test_signed_url_contains_sig(self):
        url = sign_media_path("attendance/2026/06/test.jpg")
        self.assertIn("sig=", url)
        path = "attendance/2026/06/test.jpg"
        token = unquote(url.split("sig=", 1)[1])
        self.assertTrue(verify_media_signature(path, token))

    def test_build_media_url_adds_signature(self):
        url = build_media_url("employee_photos/2026/06/x.jpg")
        self.assertIn("sig=", url)


class TerCacheTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug="ter", name="TER Co")
        seed_ter_master(self.tenant)

    def test_cache_matches_lookup(self):
        from apps.payroll.services.ter import lookup_ter_rate

        cache = build_ter_cache(self.tenant)
        gross = Decimal("7000000")
        rate_db = lookup_ter_rate(tenant=self.tenant, gross=gross, ptkp_code="TK/0")
        rate_cache = cache.lookup(gross, "TK/0")
        self.assertEqual(rate_db, rate_cache)

    def test_payroll_pph21_uses_cache(self):
        plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant")
        employee = Employee.objects.create(
            tenant=self.tenant,
            plant=plant,
            employee_id="E1",
            full_name="Worker",
            tax_status="TK/0",
            join_date=date(2024, 1, 1),
            base_salary=Decimal("7000000"),
        )
        employee.tenant = self.tenant
        cache = build_ter_cache(self.tenant)
        tax = calc_pph21(Decimal("7000000"), employee, ter_cache=cache)
        self.assertGreater(tax, Decimal("0"))
