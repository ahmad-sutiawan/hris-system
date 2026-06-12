from decimal import Decimal

from django.template import Context, Template
from django.test import SimpleTestCase

from apps.web.admin_crud.queryset import get_cell_value
from apps.web.formatting import format_cell_value, format_number, format_rupiah, is_money_field


class FormattingHelpersTests(SimpleTestCase):
    def test_format_rupiah_strips_trailing_zeros(self):
        self.assertEqual(format_rupiah(Decimal("5000000.00")), "Rp 5.000.000")
        self.assertEqual(format_rupiah(1500000), "Rp 1.500.000")

    def test_format_number_thousand_separator(self):
        self.assertEqual(format_number(1234567, max_decimals=0), "1.234.567")
        self.assertEqual(format_number(42, max_decimals=0), "42")

    def test_format_number_decimal_without_trailing_zeros(self):
        self.assertEqual(format_number(Decimal("12.50"), max_decimals=2), "12,5")
        self.assertEqual(format_number(Decimal("8.00"), max_decimals=2), "8")

    def test_format_number_negative(self):
        self.assertEqual(format_rupiah(Decimal("-250000.00")), "Rp -250.000")

    def test_is_money_field(self):
        self.assertTrue(is_money_field("employee.base_salary"))
        self.assertTrue(is_money_field("net_amount"))
        self.assertFalse(is_money_field("paid_working_hours"))

    def test_format_cell_value_money(self):
        self.assertEqual(
            format_cell_value(Decimal("4800000.00"), "net_amount"),
            "Rp 4.800.000",
        )

    def test_format_cell_value_hours(self):
        self.assertEqual(
            format_cell_value(Decimal("7.50"), "paid_working_hours"),
            "7,5",
        )

    def test_get_cell_value_formats_decimal(self):
        class Row:
            net_amount = Decimal("3200000.00")

        self.assertEqual(get_cell_value(Row(), "net_amount"), "Rp 3.200.000")


class FormattingTemplateFilterTests(SimpleTestCase):
    def test_rupiah_filter(self):
        rendered = Template("{% load hris_ui %}{{ value|rupiah }}").render(
            Context({"value": Decimal("5000000.00")})
        )
        self.assertEqual(rendered, "Rp 5.000.000")

    def test_num_filter(self):
        rendered = Template("{% load hris_ui %}{{ value|num:2 }}").render(
            Context({"value": Decimal("1234.50")})
        )
        self.assertEqual(rendered, "1.234,5")
