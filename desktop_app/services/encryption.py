import os
from cryptography.fernet import Fernet
from config import SECRET_KEY_PATH

def _load_or_create_key():
    if not os.path.exists(SECRET_KEY_PATH):
        key = Fernet.generate_key()
        with open(SECRET_KEY_PATH, "wb") as f:
            f.write(key)
    with open(SECRET_KEY_PATH, "rb") as f:
        return f.read()

_fernet = Fernet(_load_or_create_key())

def encrypt_text(plain_text: str) -> str:
    if not plain_text:
        return ""
    return _fernet.encrypt(plain_text.encode()).decode()

def decrypt_text(cipher_text: str) -> str:
    if not cipher_text:
        return ""
    try:
        return _fernet.decrypt(cipher_text.encode()).decode()
    except Exception:
        return ""
