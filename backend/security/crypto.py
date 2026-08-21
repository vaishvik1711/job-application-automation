"""
Credential encryption helpers.

Job-site passwords are encrypted at rest with Fernet using
CREDENTIAL_ENCRYPTION_KEY. The key may be either a real Fernet key
(`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
or any non-empty passphrase, which is sha256-derived into a valid Fernet key.

Rules enforced elsewhere in the codebase (do not break them):
- passwords are never logged
- no API response ever includes a password or its ciphertext
"""
import base64
import hashlib
import os
from functools import lru_cache
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken


class CredentialCryptoError(RuntimeError):
    """Raised when encryption is misconfigured or decryption fails."""


@lru_cache(maxsize=1)
def _fernet_for_secret(secret: str) -> Fernet:
    try:
        # A real Fernet key is 32 url-safe base64-encoded bytes.
        return Fernet(secret.encode("ascii"))
    except Exception:
        # Treat anything else as a passphrase and derive deterministically.
        digest = hashlib.sha256(secret.encode("utf-8")).digest()
        return Fernet(base64.urlsafe_b64encode(digest))


def get_fernet() -> Optional[Fernet]:
    secret = os.getenv("CREDENTIAL_ENCRYPTION_KEY", "").strip()
    if not secret:
        return None
    return _fernet_for_secret(secret)


def encryption_configured() -> bool:
    return get_fernet() is not None


def encrypt_secret(plaintext: str) -> str:
    f = get_fernet()
    if f is None:
        raise CredentialCryptoError(
            "CREDENTIAL_ENCRYPTION_KEY is not set — refusing to store credentials unencrypted"
        )
    return f.encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_secret(ciphertext: str) -> str:
    f = get_fernet()
    if f is None:
        raise CredentialCryptoError(
            "CREDENTIAL_ENCRYPTION_KEY is not set — stored credential cannot be decrypted"
        )
    try:
        return f.decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise CredentialCryptoError(
            "Stored credential cannot be decrypted — CREDENTIAL_ENCRYPTION_KEY changed?"
        ) from exc


def mask_username(username: Optional[str]) -> Optional[str]:
    """Return a display-safe hint: 'va***@gmail.com' / 'j***e'."""
    if not username:
        return None
    if "@" in username:
        local, _, domain = username.partition("@")
        head = local[:2]
        return f"{head}{'*' * max(len(local) - len(head), 1)}@{domain}" if local else f"*@{domain}"
    if len(username) <= 1:
        return "*"
    return f"{username[0]}{'*' * (len(username) - 2)}{username[-1]}"
