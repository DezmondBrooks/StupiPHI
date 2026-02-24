"""Tests for column-level database policy (apply_db_policy_to_row)."""
from __future__ import annotations

import copy

import pytest

from stupiphi.slice.apply_db_policy import apply_db_policy_to_row, REDACTED


def test_pseudonymize_stable_same_value_same_output() -> None:
    """Same table/column/value and salt -> same output."""
    policy = {"therapists": {"email": "pseudonymize"}}
    row = {"id": 1, "first_name": "A", "last_name": "B", "email": "doc@example.com"}
    salt = "test-salt"
    out1 = apply_db_policy_to_row("therapists", row, policy, salt)
    out2 = apply_db_policy_to_row("therapists", row, policy, salt)
    assert out1["email"] == out2["email"]
    assert out1["email"] != "doc@example.com"


def test_pseudonymize_different_salt_different_output() -> None:
    """Different salt -> different pseudonym."""
    policy = {"therapists": {"email": "pseudonymize"}}
    row = {"id": 1, "email": "same@example.com"}
    out1 = apply_db_policy_to_row("therapists", row, policy, "salt1")
    out2 = apply_db_policy_to_row("therapists", row, policy, "salt2")
    assert out1["email"] != out2["email"]


def test_pseudonymize_different_value_different_output() -> None:
    """Different value -> different pseudonym."""
    policy = {"therapists": {"email": "pseudonymize"}}
    salt = "s"
    out1 = apply_db_policy_to_row("therapists", {"id": 1, "email": "a@x.com"}, policy, salt)
    out2 = apply_db_policy_to_row("therapists", {"id": 1, "email": "b@x.com"}, policy, salt)
    assert out1["email"] != out2["email"]


def test_redact_replaces_with_redacted() -> None:
    """Column with redact -> value is '[REDACTED]'."""
    policy = {"payments": {"last4": "redact"}}
    row = {"id": 1, "last4": "1234", "method": "card"}
    out = apply_db_policy_to_row("payments", row, policy, None)
    assert out["last4"] == REDACTED
    assert out["method"] == "card"


def test_mask_keeps_last_four() -> None:
    """Mask: string length >= 4 -> only last 4 chars visible."""
    policy = {"payments": {"last4": "mask"}}
    row = {"id": 1, "last4": "12345678"}
    out = apply_db_policy_to_row("payments", row, policy, None)
    assert out["last4"] == "****5678"


def test_mask_short_string_redacted() -> None:
    """Mask: string length < 4 -> '[REDACTED]'."""
    policy = {"payments": {"last4": "mask"}}
    row = {"id": 1, "last4": "12"}
    out = apply_db_policy_to_row("payments", row, policy, None)
    assert out["last4"] == REDACTED


def test_preserve_unchanged() -> None:
    """Preserve leaves value unchanged."""
    policy = {"payments": {"last4": "preserve"}}
    row = {"id": 1, "last4": "9999"}
    out = apply_db_policy_to_row("payments", row, policy, None)
    assert out["last4"] == "9999"


def test_unspecified_table_preserve() -> None:
    """Table not in policy -> all columns preserved."""
    row = {"id": 1, "email": "secret@example.com"}
    out = apply_db_policy_to_row("therapists", row, None, "salt")
    assert out["email"] == "secret@example.com"


def test_unspecified_column_preserve() -> None:
    """Column not in table policy -> preserved."""
    policy = {"therapists": {"first_name": "redact"}}
    row = {"id": 1, "first_name": "Jane", "last_name": "Doe"}
    out = apply_db_policy_to_row("therapists", row, policy, None)
    assert out["first_name"] == REDACTED
    assert out["last_name"] == "Doe"


def test_no_mutation_of_input_row() -> None:
    """Input row dict is not mutated."""
    row = {"id": 1, "email": "x@y.com"}
    row_ref = row
    row_copy = copy.deepcopy(row)
    policy = {"therapists": {"email": "pseudonymize"}}
    out = apply_db_policy_to_row("therapists", row, policy, "s")
    assert row is row_ref
    assert row == row_copy
    assert row["email"] == "x@y.com"
    assert out["email"] != "x@y.com"


def test_pseudonymize_none_or_empty_redacted() -> None:
    """Pseudonymize with None or empty string -> [REDACTED]."""
    policy = {"therapists": {"email": "pseudonymize"}}
    out_none = apply_db_policy_to_row("therapists", {"id": 1, "email": None}, policy, "s")
    out_empty = apply_db_policy_to_row("therapists", {"id": 1, "email": ""}, policy, "s")
    assert out_none["email"] == REDACTED
    assert out_empty["email"] == REDACTED


def test_pseudonymize_no_salt_redacted() -> None:
    """Pseudonymize with no salt -> [REDACTED]."""
    policy = {"therapists": {"email": "pseudonymize"}}
    row = {"id": 1, "email": "a@b.com"}
    out = apply_db_policy_to_row("therapists", row, policy, None)
    assert out["email"] == REDACTED
