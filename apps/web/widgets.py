from django import forms


class HRISDateInput(forms.DateInput):
    """HTML5 date picker — always ISO YYYY-MM-DD for reliable parsing."""

    input_type = "date"

    def __init__(self, attrs=None, format=None):
        attrs = {**(attrs or {})}
        attrs.setdefault("class", "hris-input hris-date-input")
        attrs.setdefault("lang", "en-CA")
        super().__init__(attrs=attrs, format="%Y-%m-%d")


def apply_date_fields(form, *field_names):
    for name in field_names:
        if name not in form.fields:
            continue
        field = form.fields[name]
        field.input_formats = ["%Y-%m-%d"]
        field.widget = HRISDateInput()
