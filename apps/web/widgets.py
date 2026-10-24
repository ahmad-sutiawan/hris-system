from django import forms
from django.utils.html import format_html, format_html_join


class HRISDateInput(forms.DateInput):
    """HTML5 date picker — always ISO YYYY-MM-DD for reliable parsing."""

    input_type = "date"

    def __init__(self, attrs=None, format=None):
        attrs = {**(attrs or {})}
        attrs.setdefault("class", "hris-input hris-date-input")
        attrs.setdefault("lang", "en-CA")
        super().__init__(attrs=attrs, format="%Y-%m-%d")


class HRISTimeInput(forms.TimeInput):
    """HTML5 time picker — always HH:MM (24h) for reliable browser parsing."""

    input_type = "time"

    def __init__(self, attrs=None, format=None):
        attrs = {**(attrs or {})}
        attrs.setdefault("class", "hris-input")
        attrs.setdefault("step", "60")
        super().__init__(attrs=attrs, format="%H:%M")


class ApprovalToWidget(forms.Select):
    """Searchable employee picker. The native select still submits the approver id."""

    def render(self, name, value, attrs=None, renderer=None):
        value = "" if value in (None, "") else str(value)
        widget_id = self.build_attrs(self.attrs, attrs).get("id") or f"id_{name}"
        select_attrs = {
            **(attrs or {}),
            "id": f"{widget_id}-value",
            "class": "hris-approval-picker__native",
            "tabindex": "-1",
            "aria-hidden": "true",
        }
        selected_label = "Pilih karyawan"
        rows = []
        for opt_value, opt_label in self.choices:
            opt_value = "" if opt_value in (None, "") else str(opt_value)
            label = str(opt_label)
            if not opt_value:
                continue
            if opt_value == value:
                selected_label = label
            rows.append((opt_value, label.casefold(), label))
        options = format_html_join(
            "",
            '<li role="option" data-value="{}" data-search="{}">{}</li>',
            rows,
        )
        native = super().render(name, value, select_attrs, renderer)
        return format_html(
            '<div class="hris-approval-picker" data-approval-picker>'
            '<button type="button" class="hris-input hris-approval-picker__trigger" id="{}" aria-haspopup="listbox" aria-expanded="false">{}</button>'
            '<div class="hris-approval-picker__panel" hidden>'
            '<input type="search" class="hris-input" placeholder="Cari nama atau Employee ID" aria-label="Cari karyawan">'
            '<ul class="hris-approval-picker__list" role="listbox">{}</ul>'
            '<p class="hris-approval-picker__empty" hidden>Tidak ada karyawan yang cocok.</p>'
            '</div>{}</div>',
            widget_id,
            selected_label,
            options,
            native,
        )


def apply_time_fields(form, *field_names):
    for name in field_names:
        if name not in form.fields:
            continue
        field = form.fields[name]
        field.input_formats = ["%H:%M", "%H:%M:%S"]
        field.widget = HRISTimeInput()


def apply_date_fields(form, *field_names):
    for name in field_names:
        if name not in form.fields:
            continue
        field = form.fields[name]
        field.input_formats = ["%Y-%m-%d"]
        field.widget = HRISDateInput()
