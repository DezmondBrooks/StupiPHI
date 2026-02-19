from __future__ import annotations

from dataclasses import replace
from typing import Optional, Tuple

from faker import Faker

from models.canonical_record import CanonicalRecord, PatientInfo
from transformation.plan import TransformationPlan, PlanAction
from transformation.pseudonymizer import stable_pseudonym


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
    Replace structured fields with synthetic values (per-call, no cross-record stability).
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


def _fake_patient_info_stable(salt: str, patient: PatientInfo) -> PatientInfo:
    """
    Replace structured fields with deterministic pseudonyms: same (salt, field, value) -> same output
    across all records (cross-record consistency). DOB is left as-is.
    """
    return PatientInfo(
        first_name=stable_pseudonym(salt, "patient.first_name", patient.first_name, "first_name"),
        last_name=stable_pseudonym(salt, "patient.last_name", patient.last_name, "last_name"),
        dob=patient.dob,
        phone=stable_pseudonym(salt, "patient.phone", patient.phone, "phone"),
        address=stable_pseudonym(salt, "patient.address", patient.address, "address"),
        email=stable_pseudonym(salt, "patient.email", patient.email, "email") if patient.email else None,
    )


def apply_plan(
    record: CanonicalRecord,
    plan: TransformationPlan,
    seed: int = 1337,
    pseudonym_salt: Optional[str] = None,
) -> Tuple[CanonicalRecord, int]:
    """
    Apply plan to free-text fields + always fake structured patient fields.

    When pseudonym_salt is set, same original value across records maps to the same pseudonym.
    When None, uses Faker with seed only (no cross-record consistency).

    Returns: (sanitized_record, redaction_count)
    """
    # Apply text redactions
    encounter_actions = [a for a in plan.actions if a.field_path == "encounter_notes"]
    new_notes = _apply_span_redactions(record.encounter_notes, encounter_actions)

    if pseudonym_salt is not None:
        new_patient = _fake_patient_info_stable(pseudonym_salt, record.patient)
    else:
        fake = Faker("en_US")
        fake.seed_instance(seed)
        new_patient = _fake_patient_info(fake, record.patient)

    sanitized = CanonicalRecord(
        record_id=record.record_id,
        patient=new_patient,
        encounter_notes=new_notes,
        metadata=record.metadata,
    )

    return sanitized, len(encounter_actions)
