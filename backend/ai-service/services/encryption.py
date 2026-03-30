from cryptography.fernet import Fernet

from config.config import Config


class Encryption:
    def __init__(self, key=None):
        configured_key = key or Config.MONGO_ENCRYPTION_KEY
        if isinstance(configured_key, str):
            configured_key = configured_key.encode("utf-8")
        self.cipher = Fernet(configured_key)

    def encrypt_string(self, text):
        if isinstance(text, str):
            text = text.encode("utf-8")
        return self.cipher.encrypt(text).decode("utf-8")

    def decrypt_string(self, encrypted_text):
        if isinstance(encrypted_text, str):
            encrypted_text = encrypted_text.encode("utf-8")
        return self.cipher.decrypt(encrypted_text).decode("utf-8")
