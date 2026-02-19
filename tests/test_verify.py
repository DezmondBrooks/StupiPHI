"""Unit tests for verification (residual pattern checks)."""
from __future__ import annotations

import pytest

from models.canonical_record import CanonicalRecord, PatientInfo, Metadata
from verification.verify import verify_basic


def _record(notes: str) -> CanonicalRecord:
    return CanonicalRecord(
        record_id="r1",
        patient=PatientInfo(
            first_name="A",
            last_name="B",
            dob="1990-01-01",
            phone="555-000-0000",
            address="x",
            email=None,
        ),
        encounter_notes=notes,
        metadata=Metadata(source="test", created_at="2024-01-01T00:00:00Z"),
    )


def test_verify_basic_clean() -> None:
    ok, issues = verify_basic(_record("No PHI here."))
    assert ok is True
    assert issues == []


def test_verify_basic_email_fail() -> None:
    ok, issues = verify_basic(_record("Email: foo@example.com in notes."))
    assert ok is False
    assert any("email" in i.lower() for i in issues)


def test_verify_basic_phone_fail() -> None:
    ok, issues = verify_basic(_record("Call (555) 123-4567 for info."))
    assert ok is False
    assert any("phone" in i.lower() for i in issues)


def test_verify_basic_both_fail() -> None:
    ok, issues = verify_basic(_record("Contact bob@test.com or 555-999-8888."))
    assert ok is False
    assert len(issues) >= 2
