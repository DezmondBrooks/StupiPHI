"""Unit tests for transformation apply (span redaction and apply_plan)."""
from __future__ import annotations

import pytest

from transformation.apply import (
    _apply_span_redactions,
    apply_plan,
    REDACTION_TOKEN,
)
from transformation.plan import PlanAction, TransformationPlan
from models.canonical_record import CanonicalRecord, PatientInfo, Metadata


def test_apply_span_redactions_single() -> None:
    text = "Hello John Doe world"
    actions = [
        PlanAction(
            action_type="REDACT_TEXT_SPAN",
            field_path="encounter_notes",
            reason="test",
            start=6,
            end=14,
        ),
    ]
    out = _apply_span_redactions(text, actions)
    assert out == "Hello [REDACTED] world"


def test_apply_span_redactions_descending_order() -> None:
    text = "A B C D"
    # Redact "B" (2:3) and "D" (6:7); must apply from right to left
    actions = [
        PlanAction("REDACT_TEXT_SPAN", "encounter_notes", "r", start=6, end=7),
        PlanAction("REDACT_TEXT_SPAN", "encounter_notes", "r", start=2, end=3),
    ]
    out = _apply_span_redactions(text, actions)
    assert out == "A [REDACTED] C [REDACTED]"


def test_apply_span_redactions_skips_non_span() -> None:
    text = "Hello world"
    actions = [
        PlanAction("REPLACE_FIELD", "patient.first_name", "r", start=None, end=None),
    ]
    out = _apply_span_redactions(text, actions)
    assert out == "Hello world"


def test_apply_plan_redacts_and_fakes() -> None:
    patient = PatientInfo(
        first_name="Jane",
        last_name="Doe",
        dob="1990-01-15",
        phone="555-111-2222",
        address="123 Main St",
        email="jane@example.com",
    )
    record = CanonicalRecord(
        record_id="rec1",
        patient=patient,
        encounter_notes="Contact John at 555-123-4567.",
        metadata=Metadata(source="test", created_at="2024-01-01T00:00:00Z"),
    )
    plan = TransformationPlan(
        record_id="rec1",
        actions=[
            PlanAction("REDACT_TEXT_SPAN", "encounter_notes", "r", start=8, end=12),
            PlanAction("REDACT_TEXT_SPAN", "encounter_notes", "r", start=17, end=28),
        ],
    )
    sanitized, redaction_count = apply_plan(record, plan, seed=42)
    assert redaction_count == 2
    assert "[REDACTED]" in sanitized.encounter_notes
    assert "John" not in sanitized.encounter_notes
    assert "555-123-4567" not in sanitized.encounter_notes
    assert sanitized.patient.first_name != "Jane" or sanitized.patient.last_name != "Doe"
    assert sanitized.record_id == "rec1"


def test_apply_plan_stable_pseudonym_same_value_same_output() -> None:
    """With pseudonym_salt set, same original value in two records yields the same pseudonym."""
    patient = PatientInfo(
        first_name="Alice",
        last_name="Smith",
        dob="1985-06-20",
        phone="555-000-1111",
        address="10 Same St",
        email="alice@example.com",
    )
    meta = Metadata(source="test", created_at="2024-01-01T00:00:00Z")
    plan = TransformationPlan(record_id="any", actions=[])
    salt = "test-salt-123"

    record1 = CanonicalRecord(record_id="r1", patient=patient, encounter_notes="Note 1", metadata=meta)
    record2 = CanonicalRecord(record_id="r2", patient=patient, encounter_notes="Note 2", metadata=meta)

    out1, _ = apply_plan(record1, plan, seed=99, pseudonym_salt=salt)
    out2, _ = apply_plan(record2, plan, seed=99, pseudonym_salt=salt)

    assert out1.patient.first_name == out2.patient.first_name
    assert out1.patient.last_name == out2.patient.last_name
    assert out1.patient.phone == out2.patient.phone
    assert out1.patient.address == out2.patient.address
    assert out1.patient.email == out2.patient.email
    assert out1.patient.first_name != "Alice"
    assert out1.patient.last_name != "Smith"
