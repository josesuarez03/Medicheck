from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models

from common.security.encryption import Encryption


ENCRYPTED_VALUE_PREFIX = "enc1::"


def _field_encryption_key() -> str:
    key = getattr(settings, "FIELD_ENCRYPTION_KEY", "") or ""
    if not key:
        raise ImproperlyConfigured("FIELD_ENCRYPTION_KEY must be configured to use EncryptedTextField.")
    return key


class EncryptedTextField(models.TextField):
    """TextField encrypted at rest with Fernet."""

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value in (None, ""):
            return value
        if isinstance(value, str) and value.startswith(ENCRYPTED_VALUE_PREFIX):
            return value
        encrypted = Encryption(_field_encryption_key()).encrypt_string(str(value))
        return f"{ENCRYPTED_VALUE_PREFIX}{encrypted}"

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)

    def to_python(self, value):
        if value in (None, "") or not isinstance(value, str):
            return value
        if not value.startswith(ENCRYPTED_VALUE_PREFIX):
            return value
        encrypted_value = value[len(ENCRYPTED_VALUE_PREFIX):]
        return Encryption(_field_encryption_key()).decrypt_string(encrypted_value)
