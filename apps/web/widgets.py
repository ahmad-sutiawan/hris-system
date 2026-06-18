from django import forms


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
