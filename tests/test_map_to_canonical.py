"""Tests for mapping case slices to CanonicalRecord."""
from __future__ import annotations

from stupiphi.models.canonical_record import CanonicalRecord, PatientInfo, Metadata
from stupiphi.slice.map_to_canonical import case_slice_to_canonical_records


def test_case_slice_to_canonical_records_basic_mapping() -> None:
    patient_row = {
        "id": 1,
        "first_name": "Jane",
        "last_name": "Doe",
        "dob": "1990-01-01",
        "phone": "555-111-2222",
        "email": "jane@example.com",
        "address": "123 Main St",
    }
    case_row = {"id": 42, "patient_id": 1, "status": "open", "created_at": "2024-01-01T00:00:00Z"}
    appointments_rows = [
        {"id": 10, "case_id": 42, "therapist_id": 7, "scheduled_at": "2024-01-02T00:00:00Z", "notes": "Note A"},
        {"id": 11, "case_id": 42, "therapist_id": 8, "scheduled_at": "2024-01-03T00:00:00Z", "notes": "Note B"},
    ]

    slice_dict = {
        "patient_row": patient_row,
        "case_row": case_row,
        "appointments_rows": appointments_rows,
        "therapist_rows": [],
        "payments_rows": [],
    }

    records = case_slice_to_canonical_records(slice_dict)
    assert len(records) == 2

    r0, r1 = records
    assert isinstance(r0, CanonicalRecord)
    assert r0.patient == r1.patient
    assert r0.patient.first_name == "Jane"
    assert r0.patient.last_name == "Doe"
    assert r0.patient.dob == "1990-01-01"
    assert r0.patient.phone == "555-111-2222"
    assert r0.patient.address == "123 Main St"
    assert r0.patient.email == "jane@example.com"

    assert r0.encounter_notes == "Note A"
    assert r1.encounter_notes == "Note B"

    assert r0.metadata.source == "prod_db"
    assert r0.metadata.schema_version == "1.0"

    assert r0.record_id == "case:42:appt:10"
    assert r1.record_id == "case:42:appt:11"

