"""
Symmetric encryption for secrets stored at rest.

The current Fernet key encrypts new values. During key rotation the previous
key is retained temporarily and is accepted for decryption only, allowing the
database to be re-encrypted safely without making a crash between filesystem
and database updates fatal.
"""

from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from src.core.config import settings
from src.core.fernet_key import previous_fernet_key


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    try:
        return Fernet(settings.SECRET_KEY.encode())
    except (ValueError, TypeError) as exc:
        raise RuntimeError("Configured SECRET_KEY is not a valid Fernet key.") from exc


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as current_exc:
        previous = previous_fernet_key()
        if previous:
            try:
                return Fernet(previous.encode()).decrypt(ciphertext.encode()).decode()
            except InvalidToken:
                pass
        raise RuntimeError(
            "Could not decrypt stored secret: the current and previous Fernet keys "
            "could not decrypt the value."
        ) from current_exc
