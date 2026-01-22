from __future__ import annotations

from dataclasses import replace
from typing import Tuple

from faker import Faker

from models.canonical_record import CanonicalRecord, PatientInfo
from transformation.plan import TransformationPlan, PlanAction


REDACTION_TOKEN = "[REDACTED]"


def _apply_span_redactions(text: str, actions: list[PlanAction]) -> str:
    """
    Apply redactions to text using (start, end) spans.
    Actions must be sorted descending by start.
    """
    out = text
    for a in actions:
        if a.action_type != "REDACT_TEXT_SPAN":
            continue
        if a.start is None or a.end is None:
            continue
        out = out[: a.start] + REDACTION_TOKEN + out[a.end :]
    return out


def _fake_patient_info(fake: Faker, patient: PatientInfo) -> PatientInfo:
    """
    Replace structured fields with synthetic values.
    DOB is left as-is in MVP (optional: perturb later).
    """
    return PatientInfo(
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        dob=patient.dob,  # optional later: shift date within range
        phone=fake.phone_number(),
        address=fake.address().replace("\n", ", "),
        email=fake.email() if patient.email else None,
    )


def apply_plan(record: CanonicalRecord, plan: TransformationPlan, seed: int = 1337) -> Tuple[CanonicalRecord, int]:
    """
    Apply plan to free-text fields + always fake structured patient fields.

    Returns: (sanitized_record, redaction_count)
    """
    fake = Faker("en_US")
    fake.seed_instance(seed)

    # Apply text redactions
    encounter_actions = [a for a in plan.actions if a.field_path == "encounter_notes"]
    new_notes = _apply_span_redactions(record.encounter_notes, encounter_actions)

    # Fake structured patient fields
    new_patient = _fake_patient_info(fake, record.patient)

    sanitized = CanonicalRecord(
        record_id=record.record_id,
        patient=new_patient,
        encounter_notes=new_notes,
        metadata=record.metadata,
    )

    return sanitized, len(encounter_actions)
