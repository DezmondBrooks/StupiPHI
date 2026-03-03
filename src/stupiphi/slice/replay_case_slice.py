"""Replay a sanitized case slice into the dev Postgres DB.

Behavior:
- Delete any existing rows for the original prod IDs in dev within a single transaction.
- Allocate new dev-only IDs for patients, therapists, cases, payments, appointments.
- Rewrite foreign keys in the slice to use the new IDs.
- Insert sanitized rows; therapists and payments may be transformed by database_policy.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence

from stupiphi.connectors.postgres import PostgresClient
from stupiphi.sanitizer.pipeline import SanitizeResult
from stupiphi.slice.apply_db_policy import apply_db_policy_to_row


SliceDict = Dict[str, Any]


def _extract_ids(original_slice: SliceDict) -> Dict[str, Any]:
    patient_id = original_slice["patient_row"]["id"]
    case_id = original_slice["case_row"]["id"]
    appointments = original_slice.get("appointments_rows", []) or []
    therapists = original_slice.get("therapist_rows", []) or []
    payments = original_slice.get("payments_rows", []) or []

    return {
        "patient_id": patient_id,
        "case_id": case_id,
        "appointment_ids": [a["id"] for a in appointments],
        "therapist_ids": [t["id"] for t in therapists],
        "payment_ids": [p["id"] for p in payments],
    }


def _map_sanitized_by_appointment_id(sanitized_outputs: Sequence[SanitizeResult]) -> Dict[int, SanitizeResult]:
    mapping: Dict[int, SanitizeResult] = {}
    for res in sanitized_outputs:
        rid = res.record.record_id
        # Expect format: case:{case_id}:appt:{appt_id}
        try:
            parts = str(rid).split(":")
            appt_id = int(parts[-1])
        except Exception:
            continue
        mapping[appt_id] = res
    return mapping


def _next_id_for_table(dev_client: PostgresClient, table_name: str) -> int:
    """Return the next integer ID to use for a table based on MAX(id)."""
    row = dev_client.fetch_one(f"SELECT MAX(id) AS max_id FROM {table_name}")
    max_id = 0
    if row and row.get("max_id") is not None:
        try:
            max_id = int(row["max_id"])
        except (TypeError, ValueError):
            max_id = 0
    return max_id + 1


def replay_case_slice(
    case_id: int,
    dev_client: PostgresClient,
    sanitized_outputs: Sequence[SanitizeResult],
    original_slice: SliceDict,
    database_policy: Optional[Dict[str, Dict[str, str]]] = None,
    pseudonym_salt: Optional[str] = None,
    placeholders: Optional[Dict[str, str]] = None,
) -> None:
    """Replay a sanitized case slice into dev_db.

    This function assumes:
    - sanitized_outputs correspond to appointments in original_slice
      (one SanitizeResult per appointment).
    - All sanitized records share the same patient.

    database_policy and pseudonym_salt: optional column-level policy for replay;
    if None, all columns are preserved (current behavior).
    placeholders: optional map for action "placeholder" (e.g. users.password_hash -> dev hash).
    """
    ids = _extract_ids(original_slice)
    patient_id = ids["patient_id"]
    case_row = original_slice["case_row"]
    appointments = original_slice.get("appointments_rows", []) or []
    therapists = original_slice.get("therapist_rows", []) or []
    payments = original_slice.get("payments_rows", []) or []

    sanitized_by_appt = _map_sanitized_by_appointment_id(sanitized_outputs)

    if not sanitized_outputs:
        # Nothing to replay; no appointments for this case.
        return

    # Use patient from first sanitized record for all inserts.
    sanitized_patient = sanitized_outputs[0].record.patient

    with dev_client.transaction():
        # Delete dependents first, then parents based on original prod IDs.
        if ids["appointment_ids"]:
            dev_client.execute(
                "DELETE FROM appointments WHERE id = ANY(%s)",
                (ids["appointment_ids"],),
            )

        if ids["payment_ids"]:
            dev_client.execute(
                "DELETE FROM payments WHERE id = ANY(%s)",
                (ids["payment_ids"],),
            )

        dev_client.execute("DELETE FROM cases WHERE id = %s", (ids["case_id"],))

        if ids["therapist_ids"]:
            dev_client.execute(
                "DELETE FROM therapists WHERE id = ANY(%s)",
                (ids["therapist_ids"],),
            )

        dev_client.execute("DELETE FROM patients WHERE id = %s", (patient_id,))

        # Allocate new dev-only IDs per table to avoid reusing prod IDs.
        new_patient_id = _next_id_for_table(dev_client, "patients")

        therapist_id_map: Dict[int, int] = {}
        if ids["therapist_ids"]:
            next_tid = _next_id_for_table(dev_client, "therapists")
            for old_tid in ids["therapist_ids"]:
                therapist_id_map[old_tid] = next_tid
                next_tid += 1

        new_case_id = _next_id_for_table(dev_client, "cases")

        payment_id_map: Dict[int, int] = {}
        if ids["payment_ids"]:
            next_pid = _next_id_for_table(dev_client, "payments")
            for old_pid in ids["payment_ids"]:
                payment_id_map[old_pid] = next_pid
                next_pid += 1

        appointment_id_map: Dict[int, int] = {}
        if ids["appointment_ids"]:
            next_aid = _next_id_for_table(dev_client, "appointments")
            for old_aid in ids["appointment_ids"]:
                appointment_id_map[old_aid] = next_aid
                next_aid += 1

        # Build patient row with new ID and apply database_policy before insert.
        patient_row = {
            "id": new_patient_id,
            "first_name": sanitized_patient.first_name,
            "last_name": sanitized_patient.last_name,
            "dob": sanitized_patient.dob,
            "phone": sanitized_patient.phone,
            "email": sanitized_patient.email,
            "address": sanitized_patient.address,
        }
        patient_out = apply_db_policy_to_row("patients", patient_row, database_policy, pseudonym_salt, placeholders=placeholders)
        dev_client.execute(
            """
            INSERT INTO patients (id, first_name, last_name, dob, phone, email, address)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                patient_out["id"],
                patient_out["first_name"],
                patient_out["last_name"],
                patient_out["dob"],
                patient_out["phone"],
                patient_out["email"],
                patient_out["address"],
            ),
        )

        # Insert therapists (with database_policy if configured).
        for t in therapists:
            old_tid = t["id"]
            new_tid = therapist_id_map.get(old_tid, old_tid)
            t_row = dict(t)
            t_row["id"] = new_tid
            t_sanitized = apply_db_policy_to_row("therapists", t_row, database_policy, pseudonym_salt, placeholders=placeholders)
            dev_client.execute(
                """
                INSERT INTO therapists (id, first_name, last_name, email)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    t_sanitized["id"],
                    t_sanitized["first_name"],
                    t_sanitized["last_name"],
                    t_sanitized.get("email"),
                ),
            )

        # Insert case (policy applied if defined for cases table).
        case_row_copy = dict(case_row)
        case_row_copy["id"] = new_case_id
        case_row_copy["patient_id"] = new_patient_id
        case_sanitized = apply_db_policy_to_row("cases", case_row_copy, database_policy, pseudonym_salt, placeholders=placeholders)
        dev_client.execute(
            """
            INSERT INTO cases (id, patient_id, status, created_at)
            VALUES (%s, %s, %s, %s)
            """,
            (
                case_sanitized["id"],
                case_sanitized["patient_id"],
                case_sanitized["status"],
                case_sanitized["created_at"],
            ),
        )

        # Insert payments (with database_policy if configured).
        for p in payments:
            old_pid = p["id"]
            new_pid = payment_id_map.get(old_pid, old_pid)
            p_row = dict(p)
            p_row["id"] = new_pid
            # patient_id in payments should point to the new patient ID.
            p_row["patient_id"] = new_patient_id
            p_sanitized = apply_db_policy_to_row("payments", p_row, database_policy, pseudonym_salt, placeholders=placeholders)
            dev_client.execute(
                """
                INSERT INTO payments (id, patient_id, method, last4, created_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    p_sanitized["id"],
                    p_sanitized["patient_id"],
                    p_sanitized["method"],
                    p_sanitized.get("last4"),
                    p_sanitized["created_at"],
                ),
            )

        # Insert appointments: notes from sanitized record; full row through policy.
        for appt in appointments:
            appt_id = appt["id"]
            sanitized = sanitized_by_appt.get(appt_id)
            notes = sanitized.record.encounter_notes if sanitized is not None else (appt.get("notes") or "")
            new_appt_id = appointment_id_map.get(appt_id, appt_id)
            new_case_ref = new_case_id
            new_therapist_ref = therapist_id_map.get(appt["therapist_id"], appt["therapist_id"])
            appt_row = {
                "id": new_appt_id,
                "case_id": new_case_ref,
                "therapist_id": new_therapist_ref,
                "scheduled_at": appt["scheduled_at"],
                "notes": notes,
            }
            appt_out = apply_db_policy_to_row("appointments", appt_row, database_policy, pseudonym_salt, placeholders=placeholders)
            dev_client.execute(
                """
                INSERT INTO appointments (id, case_id, therapist_id, scheduled_at, notes)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    appt_out["id"],
                    appt_out["case_id"],
                    appt_out["therapist_id"],
                    appt_out["scheduled_at"],
                    appt_out["notes"],
                ),
            )

