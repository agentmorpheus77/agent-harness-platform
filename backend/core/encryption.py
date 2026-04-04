import base64
import hashlib

from cryptography.fernet import Fernet

from backend.core.config import ENCRYPTION_KEY


def _get_fernet() -> Fernet:
    key = hashlib.sha256(ENCRYPTION_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_value(value: str) -> str:
    return _get_fernet().encrypt(value.encode()).decode()


def decrypt_value(encrypted: str) -> str:
    return _get_fernet().decrypt(encrypted.encode()).decode()
