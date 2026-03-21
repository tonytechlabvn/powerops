"""AES-256-GCM encryption utilities for Terraform state data.

Provides encrypt/decrypt, metadata extraction, checksum, and key loading.
Encryption is optional — if no key is configured, state is stored plaintext
with a warning (dev mode).
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
import secrets

logger = logging.getLogger(__name__)


def load_encryption_key() -> bytes | None:
    """Read TERRABOT_STATE_ENCRYPTION_KEY env var and base64-decode to 32 bytes.

    Returns None if the env var is absent or empty (dev/unencrypted mode).
    Raises ValueError if the key decodes to a length other than 32 bytes.
    """
    raw = os.environ.get("TERRABOT_STATE_ENCRYPTION_KEY", "").strip()
    if not raw:
        logger.warning(
            "TERRABOT_STATE_ENCRYPTION_KEY is not set — state stored unencrypted (dev mode)."
        )
        return None

    try:
        key = base64.b64decode(raw)
    except Exception as exc:
        raise ValueError(f"Invalid base64 in TERRABOT_STATE_ENCRYPTION_KEY: {exc}") from exc

    if len(key) != 32:
        raise ValueError(
            f"TERRABOT_STATE_ENCRYPTION_KEY must decode to exactly 32 bytes, got {len(key)}."
        )

    return key


def encrypt_state(plaintext: bytes, key: bytes) -> bytes:
    """Encrypt *plaintext* with AES-256-GCM using *key*.

    Layout: 12-byte random nonce || GCM ciphertext+tag (16 bytes appended by lib).
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    nonce = secrets.token_bytes(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data=None)
    return nonce + ciphertext


def decrypt_state(ciphertext: bytes, key: bytes) -> bytes:
    """Decrypt *ciphertext* previously produced by :func:`encrypt_state`.

    Extracts the 12-byte nonce prepended by encrypt_state, then decrypts.
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if len(ciphertext) < 12:
        raise ValueError("Ciphertext too short — missing nonce.")

    nonce = ciphertext[:12]
    payload = ciphertext[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, payload, associated_data=None)


def compute_checksum(plaintext: bytes) -> str:
    """Return SHA-256 hex digest of *plaintext* bytes."""
    return hashlib.sha256(plaintext).hexdigest()


def extract_state_metadata(state_json: dict) -> dict:
    """Extract non-sensitive metadata fields from a parsed Terraform state dict.

    Returns a dict with: resource_count, outputs (names only, no values),
    lineage, serial.
    """
    try:
        resources = state_json.get("resources", [])
        resource_count = len(resources)

        # Only expose output names — not values (may contain secrets)
        raw_outputs: dict = state_json.get("outputs", {})
        safe_outputs = {
            name: {"sensitive": meta.get("sensitive", False)}
            for name, meta in raw_outputs.items()
        }

        return {
            "resource_count": resource_count,
            "outputs": safe_outputs,
            "lineage": state_json.get("lineage", ""),
            "serial": state_json.get("serial", 0),
            "terraform_version": state_json.get("terraform_version", ""),
        }
    except Exception as exc:
        logger.warning("Failed to extract state metadata: %s", exc)
        return {"resource_count": 0, "outputs": {}, "lineage": "", "serial": 0}
