"""AudioVault cryptography: scrypt password KDF, AES-256-GCM, SHA-256.

Designed for a local university steganography demonstration.
"""
from __future__ import annotations

import hashlib
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

SALT_SIZE = 16
NONCE_SIZE = 12
GCM_TAG_SIZE = 16
ENCRYPTION_OVERHEAD = SALT_SIZE + NONCE_SIZE + GCM_TAG_SIZE


def sha256_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _key(password: str, salt: bytes) -> bytes:
    if not password:
        raise ValueError("Enter a non-empty encryption password.")
    return Scrypt(salt=salt, length=32, n=2**14, r=8, p=1).derive(
        password.encode("utf-8")
    )


def encrypt_data(plaintext: bytes, password: str) -> bytes:
    salt = os.urandom(SALT_SIZE)
    nonce = os.urandom(NONCE_SIZE)
    ciphertext_and_tag = AESGCM(_key(password, salt)).encrypt(
        nonce, plaintext, None
    )
    return salt + nonce + ciphertext_and_tag


def decrypt_data(encrypted: bytes, password: str) -> bytes:
    if len(encrypted) < ENCRYPTION_OVERHEAD:
        raise ValueError("The encrypted content is incomplete or damaged.")
    salt = encrypted[:SALT_SIZE]
    nonce = encrypted[SALT_SIZE:SALT_SIZE + NONCE_SIZE]
    ciphertext_and_tag = encrypted[SALT_SIZE + NONCE_SIZE:]
    try:
        return AESGCM(_key(password, salt)).decrypt(
            nonce, ciphertext_and_tag, None
        )
    except InvalidTag as exc:
        raise ValueError("Incorrect password or the hidden data has been changed.") from exc
