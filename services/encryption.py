"""Data encryption using RSA-OAEP."""

import json
import base64
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

from config import PUBLIC_KEY

CHUNK_SIZE = 190


def encrypt_data(data: dict) -> str:
    """Encrypt data using RSA-OAEP.

    Args:
        data: Dictionary to encrypt

    Returns:
        JSON string of base64-encoded encrypted chunks
    """
    raw = json.dumps(data).encode()
    key = serialization.load_pem_public_key(
        PUBLIC_KEY.encode(),
        backend=default_backend()
    )

    chunks = []
    for i in range(0, len(raw), CHUNK_SIZE):
        chunk = raw[i:i + CHUNK_SIZE]
        encrypted = key.encrypt(
            chunk,
            padding.OAEP(
                mgf=padding.MGF1(SHA256()),
                algorithm=SHA256(),
                label=None
            )
        )
        chunks.append(base64.b64encode(encrypted).decode())

    return json.dumps(chunks)
