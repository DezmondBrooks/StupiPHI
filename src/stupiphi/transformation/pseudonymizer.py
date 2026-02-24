"""
Deterministic pseudonymization: same (salt, field_path, original_value) yields same replacement.
Used for cross-record consistency when pseudonym_salt is set in config.
"""
from __future__ import annotations

import hashlib
from typing import Optional

from faker import Faker


def _stable_seed(salt: str, field_path: str, value: str) -> int:
    """Derive an integer seed from salt + field_path + value for deterministic Faker."""
    h = hashlib.sha256(f"{salt}:{field_path}:{value}".encode("utf-8")).hexdigest()
    return int(h[:16], 16) % (2**31 - 1)


def stable_pseudonym(
    salt: str,
    field_path: str,
    original_value: str,
    field_kind: str,
) -> str:
    """
    Return a deterministic replacement for original_value.
    Same (salt, field_path, original_value) always returns the same string.
    field_kind: "first_name" | "last_name" | "phone" | "address" | "email"
    """
    seed = _stable_seed(salt, field_path, original_value)
    fake = Faker("en_US")
    fake.seed_instance(seed)
    if field_kind == "first_name":
        return fake.first_name()
    if field_kind == "last_name":
        return fake.last_name()
    if field_kind == "phone":
        return fake.phone_number()
    if field_kind == "address":
        return fake.address().replace("\n", ", ")
    if field_kind == "email":
        return fake.email()
    # fallback: hash-based placeholder
    h = hashlib.sha256(f"{salt}:{field_path}:{original_value}:alt".encode("utf-8")).hexdigest()
    return f"x{h[:8]}"
