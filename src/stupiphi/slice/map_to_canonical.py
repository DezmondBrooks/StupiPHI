"""Map a case-centered slice into CanonicalRecord objects.

V1 assumptions:
- One patient per case (per schema).
- Free text lives in appointments.notes only.
- One CanonicalRecord per appointment.
"""
from __future__ import annotations

from typing import Any, Dict, List

from stupiphi.models.canonical_record import CanonicalRecord, PatientInfo, Metadata


SliceDict = Dict[str, Any]


def _to_iso_date(value: Any) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def case_slice_to_canonical_records(slice_dict: SliceDict) -> List[CanonicalRecord]:
    """Convert a slice dict into CanonicalRecords (one per appointment)."""
    patient_row = slice_dict["patient_row"]
    case_row = slice_dict["case_row"]
    appointments = slice_dict.get("appointments_rows", []) or []

    patient = PatientInfo(
        first_name=patient_row["first_name"],
        last_name=patient_row["last_name"],
        dob=_to_iso_date(patient_row["dob"]),
        phone=patient_row.get("phone") or "",
        address=patient_row.get("address") or "",
        email=patient_row.get("email"),
    )

    case_id = case_row["id"]
    records: List[CanonicalRecord] = []

    for appt in appointments:
        appt_id = appt["id"]
        notes = appt.get("notes") or ""
        record_id = f"case:{case_id}:appt:{appt_id}"
        metadata = Metadata(source="prod_db", created_at=CanonicalRecord.now_iso())
        records.append(
            CanonicalRecord(
                record_id=record_id,
                patient=patient,
                encounter_notes=notes,
                metadata=metadata,
            )
        )

    return records

