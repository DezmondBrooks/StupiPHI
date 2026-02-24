"""Extract a minimal case-centered slice from the prod Postgres DB.

This module only knows about the toy schema defined in docker/init/001_schema.sql:
- patients
- therapists
- cases
- payments
- appointments
"""
from __future__ import annotations

from typing import Any, Dict, List

from stupiphi.connectors.postgres import PostgresClient


SliceDict = Dict[str, Any]


def extract_case_slice(case_id: int, prod_client: PostgresClient) -> SliceDict:
    """Extract a case-centered slice from prod_db.

    Returns a dict with:
      - patient_row
      - case_row
      - appointments_rows
      - therapist_rows
      - payments_rows
    """
    case_row = prod_client.fetch_one("SELECT * FROM cases WHERE id = %s", (case_id,))
    if case_row is None:
        raise ValueError(f"case_id {case_id} not found")

    patient_id = case_row["patient_id"]
    patient_row = prod_client.fetch_one("SELECT * FROM patients WHERE id = %s", (patient_id,))
    if patient_row is None:
        raise RuntimeError(f"Patient {patient_id} referenced by case {case_id} not found")

    appointments_rows: List[Dict[str, Any]] = prod_client.fetch_all(
        "SELECT * FROM appointments WHERE case_id = %s ORDER BY id", (case_id,)
    )

    therapist_rows: List[Dict[str, Any]] = []
    therapist_ids = sorted({row["therapist_id"] for row in appointments_rows}) if appointments_rows else []
    if therapist_ids:
        therapist_rows = prod_client.fetch_all(
            "SELECT * FROM therapists WHERE id = ANY(%s)",
            (therapist_ids,),
        )

    payments_rows: List[Dict[str, Any]] = prod_client.fetch_all(
        "SELECT * FROM payments WHERE patient_id = %s ORDER BY id", (patient_id,)
    )

    return {
        "patient_row": patient_row,
        "case_row": case_row,
        "appointments_rows": appointments_rows,
        "therapist_rows": therapist_rows,
        "payments_rows": payments_rows,
    }

