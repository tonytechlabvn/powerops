"""Encryption/decryption helpers for sensitive variable set values.

Mirrors the state-encryption pattern: AES-256-GCM when key is configured,
base64-tagged plaintext in dev mode. All stored values are prefixed with a
tag ("enc:" or "plain:") to distinguish the storage format.
"""
from __future__ import annotations

import base64
import logging
import os

logger = logging.getLogger(__name__)


def encrypt_value(value: str) -> str:
    """Encrypt *value*; returns tagged ciphertext string safe for DB storage."""
    key_b64 = os.environ.get("TERRABOT_STATE_ENCRYPTION_KEY", "").strip()
    if not key_b64:
        logger.debug("No encryption key set — storing sensitive variable as base64 plaintext.")
        return "plain:" + base64.b64encode(value.encode()).decode()
    try:
        import secrets
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        key = base64.b64decode(key_b64)
        nonce = secrets.token_bytes(12)
        ct = AESGCM(key).encrypt(nonce, value.encode(), None)
        return "enc:" + base64.b64encode(nonce + ct).decode()
    except Exception as exc:
        logger.warning("AES encryption failed, falling back to plaintext: %s", exc)
        return "plain:" + base64.b64encode(value.encode()).decode()


def decrypt_value(stored: str) -> str:
    """Decrypt a stored variable value produced by encrypt_value()."""
    if stored.startswith("plain:"):
        return base64.b64decode(stored[6:]).decode()
    if stored.startswith("enc:"):
        key_b64 = os.environ.get("TERRABOT_STATE_ENCRYPTION_KEY", "").strip()
        if not key_b64:
            raise ValueError("Encryption key not configured; cannot decrypt variable value.")
        raw = base64.b64decode(stored[4:])
        key = base64.b64decode(key_b64)
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        nonce, ct = raw[:12], raw[12:]
        return AESGCM(key).decrypt(nonce, ct, None).decode()
    # Legacy: untagged plain value stored before tagging was introduced
    return stored


def varset_to_dict(row, include_values: bool = False) -> dict:
    """Serialize a VariableSet ORM row to a plain dict."""
    return {
        "id": row.id,
        "name": row.name,
        "description": row.description,
        "org_id": row.org_id,
        "is_global": row.is_global,
        "created_at": row.created_at.isoformat() if row.created_at else "",
        "updated_at": row.updated_at.isoformat() if row.updated_at else "",
        "variable_count": len(row.variables) if row.variables else 0,
        "workspace_count": len(row.assignments) if row.assignments else 0,
        "variables": [var_to_dict(v, include_values) for v in (row.variables or [])],
    }


def var_to_dict(row, include_value: bool = False) -> dict:
    """Serialize a VariableSetVariable ORM row, masking sensitive values by default."""
    if include_value and row.value:
        try:
            value = decrypt_value(row.value) if row.is_sensitive else row.value
        except Exception:
            value = "***decryption-error***"
    elif not row.is_sensitive:
        value = row.value or ""
    else:
        value = ""
    return {
        "id": row.id,
        "variable_set_id": row.variable_set_id,
        "key": row.key,
        "value": value,
        "is_sensitive": row.is_sensitive,
        "is_hcl": row.is_hcl,
        "category": row.category,
        "description": row.description,
    }
