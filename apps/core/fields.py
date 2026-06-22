from decimal import Decimal, InvalidOperation

from django.db import models

from apps.core.encryption import decrypt_value, encrypt_value


class EncryptedCharField(models.CharField):
    """CharField terenkripsi at-rest (Fernet)."""

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value in (None, ""):
            return value
        return encrypt_value(str(value))

    def from_db_value(self, value, expression, connection):
        if value in (None, ""):
            return value
        return decrypt_value(value)

    def to_python(self, value):
        if value in (None, ""):
            return value
        if isinstance(value, str) and value.startswith("enc:v1:"):
            return decrypt_value(value)
        return value


class EncryptedDecimalField(models.DecimalField):
    """DecimalField yang disimpan terenkripsi sebagai string di DB."""

    def get_internal_type(self):
        return "CharField"

    def get_prep_value(self, value):
        if value in (None, ""):
            return value
        return encrypt_value(str(value))

    def from_db_value(self, value, expression, connection):
        if value in (None, ""):
            return value
        plain = decrypt_value(str(value))
        try:
            return Decimal(plain)
        except (InvalidOperation, TypeError):
            return Decimal("0")

    def to_python(self, value):
        if value in (None, ""):
            return value
        if isinstance(value, Decimal):
            return value
        if isinstance(value, str) and value.startswith("enc:v1:"):
            plain = decrypt_value(value)
            try:
                return Decimal(plain) if plain else Decimal("0")
            except (InvalidOperation, TypeError):
                return Decimal("0")
        return Decimal(str(value))

    def db_type(self, connection):
        return "varchar(512)"
