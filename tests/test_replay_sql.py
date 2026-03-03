"""Tests for replay_case_slice SQL behavior using a fake PostgresClient."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence

import pytest

pytest.importorskip("psycopg", reason="psycopg required for replay SQL tests")

from stupiphi.connectors.postgres import PostgresClient
from stupiphi.models.canonical_record import CanonicalRecord, PatientInfo, Metadata
from stupiphi.sanitizer.pipeline import SanitizeResult, AuditEvent
from stupiphi.slice.replay_case_slice import replay_case_slice


@dataclass
class FakeAuditEvent:
    record_id: str


class FakeClient(PostgresClient):
    def __init__(self) -> None:
        # We don't use a real DSN/connection; override execute methods only.
        self.dsn = "postgresql://fake"
        self._conn = None  # type: ignore[assignment]
        self.calls: List[tuple[str, Any]] = []

    def connect(self) -> None:  # type: ignore[override]
        return

    @property  # type: ignore[override]
    def conn(self):
        raise RuntimeError("FakeClient.conn should not be used in tests")

    def execute(self, query, params=None):  # type: ignore[override]
        self.calls.append((query.strip(), params))

    def fetch_one(self, query, params=None):  # type: ignore[override]
        # Simulate empty tables so MAX(id) returns NULL/0.
        return {"max_id": 0}

    def transaction(self):  # type: ignore[override]
        class _Tx:
            def __init__(self, outer: FakeClient) -> None:
                self.outer = outer

            def __enter__(self) -> FakeClient:
                return self.outer

            def __exit__(self, exc_type, exc, tb) -> None:
                return False

        return _Tx(self)


def _make_sanitize_result(appt_id: int, notes: str) -> SanitizeResult:
    rec = CanonicalRecord(
        record_id=f"case:42:appt:{appt_id}",
        patient=PatientInfo(
            first_name="San",
            last_name="Itized",
            dob="1990-01-01",
            phone="555-000-0000",
            address="x",
            email="sanitized@example.com",
        ),
        encounter_notes=notes,
        metadata=Metadata(source="prod_db", created_at="2024-01-01T00:00:00Z"),
    )
    audit = AuditEvent(
        record_id=rec.record_id,
        detector_sources=[],
        finding_counts={},
        action_counts={},
        notes="",
    )
    return SanitizeResult(
        record=rec,
        audit_event=audit,
        verification_ok=True,
        verification_issues=[],
    )


def test_replay_case_slice_deletes_and_inserts_in_order() -> None:
    original_slice = {
        "patient_row": {
            "id": 1,
            "first_name": "Jane",
            "last_name": "Doe",
            "dob": "1990-01-01",
            "phone": "555-111-2222",
            "email": "jane@example.com",
            "address": "123 Main St",
        },
        "case_row": {"id": 42, "patient_id": 1, "status": "open", "created_at": "2024-01-01T00:00:00Z"},
        "appointments_rows": [
            {"id": 10, "case_id": 42, "therapist_id": 7, "scheduled_at": "2024-01-02T00:00:00Z", "notes": "raw A"},
            {"id": 11, "case_id": 42, "therapist_id": 8, "scheduled_at": "2024-01-03T00:00:00Z", "notes": "raw B"},
        ],
        "therapist_rows": [
            {"id": 7, "first_name": "Alex", "last_name": "Kim", "email": "alex@example.com"},
            {"id": 8, "first_name": "Sam", "last_name": "Patel", "email": "sam@example.com"},
        ],
        "payments_rows": [
            {"id": 100, "patient_id": 1, "method": "card", "last4": "4242", "created_at": "2024-01-01T00:00:00Z"},
        ],
    }

    sanitized_outputs: Sequence[SanitizeResult] = [
        _make_sanitize_result(10, "sanitized A"),
        _make_sanitize_result(11, "sanitized B"),
    ]

    client = FakeClient()
    replay_case_slice(case_id=42, dev_client=client, sanitized_outputs=sanitized_outputs, original_slice=original_slice)

    # Basic shape: deletes then inserts, and sanitized notes used for appointments.
    delete_queries = [q for q, _ in client.calls if q.upper().startswith("DELETE")]
    insert_queries = [q for q, _ in client.calls if q.upper().startswith("INSERT")]

    assert any("FROM appointments" in q for q in delete_queries)
    assert any("FROM payments" in q for q in delete_queries)
    assert any("FROM cases" in q for q in delete_queries)
    assert any("FROM therapists" in q for q in delete_queries)
    assert any("FROM patients" in q for q in delete_queries)

    # Two appointment inserts with sanitized notes.
    appt_inserts = [params for q, params in client.calls if "INSERT INTO appointments" in q]
    assert len(appt_inserts) == 2
    notes = {p[4] for p in appt_inserts}
    assert "sanitized A" in notes
    assert "sanitized B" in notes

