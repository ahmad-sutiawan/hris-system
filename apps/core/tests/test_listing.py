from datetime import date

from django.test import RequestFactory, TestCase

from apps.core.listing import (
    ListFilters,
    apply_date_field_range,
    apply_period_overlap,
    build_filter_query,
    paginate_queryset,
    parse_list_filters,
    queryset_to_csv,
)
from apps.employees.models import Employee


class ListingHelpersTests(TestCase):
    def test_parse_list_filters_defaults(self):
        request = RequestFactory().get("/employees/")
        filters = parse_list_filters(request)
        self.assertEqual(filters.q, "")
        self.assertEqual(filters.page, 1)

    def test_apply_date_field_range(self):
        from apps.core.models import Plant, Tenant

        tenant = Tenant.objects.create(slug="list", name="List Co")
        plant = Plant.objects.create(tenant=tenant, code="P1", name="Plant")
        Employee.objects.create(
            tenant=tenant,
            plant=plant,
            employee_id="E001",
            full_name="Alpha",
            join_date=date(2024, 1, 10),
        )
        Employee.objects.create(
            tenant=tenant,
            plant=plant,
            employee_id="E002",
            full_name="Beta",
            join_date=date(2024, 6, 10),
        )
        qs = Employee.objects.filter(tenant=tenant)
        filtered = apply_date_field_range(
            qs,
            date_from="2024-05-01",
            date_to="2024-12-31",
            field_name="join_date",
        )
        self.assertEqual(filtered.count(), 1)
        self.assertEqual(filtered.first().employee_id, "E002")

    def test_apply_period_overlap(self):
        from apps.core.models import Plant, Tenant
        from apps.payroll.models import PayrollRun

        tenant = Tenant.objects.create(slug="pay", name="Pay Co")
        plant = Plant.objects.create(tenant=tenant, code="P1", name="Plant")
        PayrollRun.objects.create(
            tenant=tenant,
            plant=plant,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
        )
        PayrollRun.objects.create(
            tenant=tenant,
            plant=plant,
            period_start=date(2024, 3, 1),
            period_end=date(2024, 3, 31),
        )
        qs = PayrollRun.objects.filter(tenant=tenant)
        filtered = apply_period_overlap(
            qs,
            date_from="2024-01-15",
            date_to="2024-02-15",
            start_field="period_start",
            end_field="period_end",
        )
        self.assertEqual(filtered.count(), 1)

    def test_paginate_queryset(self):
        from apps.core.models import Plant, Tenant

        tenant = Tenant.objects.create(slug="pg", name="Pg Co")
        plant = Plant.objects.create(tenant=tenant, code="P1", name="Plant")
        for i in range(30):
            Employee.objects.create(
                tenant=tenant,
                plant=plant,
                employee_id=f"E{i:03d}",
                full_name=f"Employee {i}",
            )
        request = RequestFactory().get("/employees/?page=2")
        filters = parse_list_filters(request, per_page=10)
        page_obj = paginate_queryset(Employee.objects.filter(tenant=tenant).order_by("employee_id"), filters)
        self.assertEqual(page_obj.number, 2)
        self.assertEqual(len(page_obj.object_list), 10)

    def test_build_filter_query_preserves_filters(self):
        request = RequestFactory().get("/attendance/?q=alpha&date_from=2024-01-01&page=2")
        query = build_filter_query(request)
        self.assertIn("q=alpha", query)
        self.assertIn("date_from=2024-01-01", query)
        self.assertNotIn("page=", query)

    def test_queryset_to_csv(self):
        content = queryset_to_csv(
            [{"name": "A"}, {"name": "B"}],
            ["Name"],
            lambda row: [row["name"]],
        )
        self.assertIn("Name", content)
        self.assertIn("A", content)
