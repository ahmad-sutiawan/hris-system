from django.test import TestCase

from apps.core.models import Plant, Tenant
from apps.organization.models import Department
from apps.organization.services.codes import department_code_from_name


class DepartmentCodeTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug="codes", name="Codes Co")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant 1")

    def test_generates_code_from_name(self):
        code = department_code_from_name(
            "Human Resources",
            tenant_id=self.tenant.pk,
            plant_id=self.plant.pk,
        )
        self.assertEqual(code, "HUMAN_RESOURCES")

    def test_avoids_duplicate_codes(self):
        Department.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            code="PRODUKSI",
            name="Produksi",
        )
        code = department_code_from_name(
            "Produksi",
            tenant_id=self.tenant.pk,
            plant_id=self.plant.pk,
        )
        self.assertEqual(code, "PRODUKSI_2")
