from __future__ import annotations

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

class Encryption:
    def __init__(self, key=None):
        configured_key = key or getattr(settings, "FIELD_ENCRYPTION_KEY", "") or ""
        if not configured_key:
            raise ImproperlyConfigured("FIELD_ENCRYPTION_KEY must be configured.")
        if isinstance(configured_key, str):
            configured_key = configured_key.encode("utf-8")
        try:
            self.cipher = Fernet(configured_key)
        except Exception as exc:
            raise ImproperlyConfigured("FIELD_ENCRYPTION_KEY must be a valid Fernet key.") from exc
        self.key = configured_key

    def encrypt_string(self, text):
        if isinstance(text, str):
            text = text.encode("utf-8")
        encrypted_text = self.cipher.encrypt(text)
        return encrypted_text.decode("utf-8")

    def decrypt_string(self, encrypted_text):
        if isinstance(encrypted_text, str):
            encrypted_text = encrypted_text.encode("utf-8")
        decrypted = self.cipher.decrypt(encrypted_text)
        return decrypted.decode("utf-8")

    def encrypt_endpoint(self, endpoint):
        parts = endpoint.split("/")

        if len(parts) > 1 and parts[-1]:
            parts[-1] = self.encrypt_string(parts[-1])
            return "/".join(parts)
        return endpoint

    def decrypt_endpoint(self, encrypted_endpoint):
        parts = encrypted_endpoint.split("/")

        if len(parts) > 1 and parts[-1]:
            try:
                parts[-1] = self.decrypt_string(parts[-1])
                return "/".join(parts)
            except Exception:
                return encrypted_endpoint
        return encrypted_endpoint
