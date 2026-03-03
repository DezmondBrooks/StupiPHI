"""Unit tests for case transfer job: dry-run, fail-on-verification, report-out, audit_sink."""
from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("psycopg", reason="psycopg required to import case_transfer")

from stupiphi.audit.audit_log import AuditEvent, file_audit_sink
from stupiphi.jobs.case_transfer import (
    VerificationFailedError,
    run_case_transfer,
    TransferReport,
)
from stupiphi.models.canonical_record import CanonicalRecord, PatientInfo, Metadata
from stupiphi.sanitizer.pipeline import SanitizeResult


class FakeClient:
    def close(self) -> None:
        pass


def _minimal_slice():
    return {
        "patient_row": {
            "first_name": "A",
            "last_name": "B",
            "dob": "1990-01-01",
            "phone": "",
            "address": "",
            "email": None,
        },
        "case_row": {"id": 1},
        "appointments_rows": [{"id": 10, "notes": "Generic note"}],
    }


def _one_record():
    return CanonicalRecord(
        record_id="case:1:appt:10",
        patient=PatientInfo(
            first_name="A",
            last_name="B",
            dob="1990-01-01",
            phone="",
            address="",
            email=None,
        ),
        encounter_notes="Generic note",
        metadata=Metadata(source="prod_db", created_at="2024-01-01T00:00:00Z"),
    )


def _sanitize_result(verification_ok: bool, verification_issues: list[str] | None = None):
    rec = _one_record()
    audit = AuditEvent(
        record_id=rec.record_id,
        detector_sources=[],
        finding_counts={},
        action_counts={},
        notes="Applied 0 redactions.",
    )
    return SanitizeResult(
        record=rec,
        audit_event=audit,
        verification_ok=verification_ok,
        verification_issues=verification_issues or [],
    )


@patch("stupiphi.jobs.case_transfer.replay_case_slice")
@patch("stupiphi.jobs.case_transfer.case_slice_to_canonical_records")
@patch("stupiphi.jobs.case_transfer.extract_case_slice")
@patch("stupiphi.jobs.case_transfer.get_dev_client")
@patch("stupiphi.jobs.case_transfer.get_prod_client")
def test_dry_run_does_not_call_replay(
    mock_prod: MagicMock,
    mock_dev: MagicMock,
    mock_extract: MagicMock,
    mock_map: MagicMock,
    mock_replay: MagicMock,
) -> None:
    mock_prod.return_value = FakeClient()
    mock_dev.return_value = FakeClient()
    mock_extract.return_value = _minimal_slice()
    mock_map.return_value = [_one_record()]
    with patch("stupiphi.jobs.case_transfer.SanitizationPipeline") as MockPipeline, patch.dict(
        "os.environ", {"STUPIPHI_ALLOW_PROD_TO_DEV": "true"}
    ):
        MockPipeline.return_value.sanitize_record.return_value = _sanitize_result(True)

        run_case_transfer(case_id=1, dry_run=True)

    mock_replay.assert_not_called()


@patch("stupiphi.jobs.case_transfer.replay_case_slice")
@patch("stupiphi.jobs.case_transfer.case_slice_to_canonical_records")
@patch("stupiphi.jobs.case_transfer.extract_case_slice")
@patch("stupiphi.jobs.case_transfer.get_dev_client")
@patch("stupiphi.jobs.case_transfer.get_prod_client")
def test_fail_on_verification_prevents_replay(
    mock_prod: MagicMock,
    mock_dev: MagicMock,
    mock_extract: MagicMock,
    mock_map: MagicMock,
    mock_replay: MagicMock,
) -> None:
    mock_prod.return_value = FakeClient()
    mock_dev.return_value = FakeClient()
    mock_extract.return_value = _minimal_slice()
    mock_map.return_value = [_one_record()]
    with patch("stupiphi.jobs.case_transfer.SanitizationPipeline") as MockPipeline, patch.dict(
        "os.environ", {"STUPIPHI_ALLOW_PROD_TO_DEV": "true"}
    ):
        MockPipeline.return_value.sanitize_record.return_value = _sanitize_result(
            False, ["encounter_notes still contains an email-like pattern"]
        )

        with pytest.raises(VerificationFailedError) as exc_info:
            run_case_transfer(case_id=1, fail_on_verification=True)

        assert "1 record" in str(exc_info.value)
    mock_replay.assert_not_called()


ALLOWED_REPORT_KEYS = {
    "case_id",
    "rows_extracted",
    "rows_inserted",
    "verification_failures",
    "audit_events",
    "replay_skipped",
    "replay_skip_reason",
    "started_at",
    "finished_at",
    "config_path",
    "db_verification_ok",
    "db_findings_count",
    "db_findings_by_table",
    "db_findings_by_column",
}


@patch("stupiphi.jobs.case_transfer.replay_case_slice")
@patch("stupiphi.jobs.case_transfer.case_slice_to_canonical_records")
@patch("stupiphi.jobs.case_transfer.extract_case_slice")
@patch("stupiphi.jobs.case_transfer.get_dev_client")
@patch("stupiphi.jobs.case_transfer.get_prod_client")
def test_report_out_writes_valid_json_no_sensitive_fields(
    mock_prod: MagicMock,
    mock_dev: MagicMock,
    mock_extract: MagicMock,
    mock_map: MagicMock,
    mock_replay: MagicMock,
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "report.json"
    mock_prod.return_value = FakeClient()
    mock_dev.return_value = FakeClient()
    mock_extract.return_value = _minimal_slice()
    mock_map.return_value = [_one_record()]
    with patch("stupiphi.jobs.case_transfer.SanitizationPipeline") as MockPipeline, patch.dict(
        "os.environ", {"STUPIPHI_ALLOW_PROD_TO_DEV": "true"}
    ):
        MockPipeline.return_value.sanitize_record.return_value = _sanitize_result(True)

        run_case_transfer(case_id=1, dry_run=True, report_out=str(report_path))

    data = json.loads(report_path.read_text(encoding="utf-8"))
    assert set(data.keys()) <= ALLOWED_REPORT_KEYS
    assert data["case_id"] == 1
    assert "rows_extracted" in data
    assert "rows_inserted" in data
    assert data["replay_skipped"] is True
    assert data["replay_skip_reason"] == "dry_run"


# Forbidden substrings that could indicate PHI in audit JSONL (conservative)
FORBIDDEN_AUDIT_SUBSTRINGS = [
    "Patient ",
    "@",  # email-like
]
PHONE_PATTERN = re.compile(r"\d{3}[-.\s]?\d{3}[-.\s]?\d{4}")


@patch("stupiphi.jobs.case_transfer.replay_case_slice")
@patch("stupiphi.jobs.case_transfer.case_slice_to_canonical_records")
@patch("stupiphi.jobs.case_transfer.extract_case_slice")
@patch("stupiphi.jobs.case_transfer.get_dev_client")
@patch("stupiphi.jobs.case_transfer.get_prod_client")
def test_audit_sink_writes_jsonl_no_phi(
    mock_prod: MagicMock,
    mock_dev: MagicMock,
    mock_extract: MagicMock,
    mock_map: MagicMock,
    mock_replay: MagicMock,
    tmp_path: Path,
) -> None:
    audit_path = tmp_path / "audit.jsonl"
    mock_prod.return_value = FakeClient()
    mock_dev.return_value = FakeClient()
    mock_extract.return_value = _minimal_slice()
    mock_map.return_value = [_one_record()]
    with patch("stupiphi.jobs.case_transfer.SanitizationPipeline") as MockPipeline, patch.dict(
        "os.environ", {"STUPIPHI_ALLOW_PROD_TO_DEV": "true"}
    ):
        result = _sanitize_result(True)

        def _sanitize_side_effect(rec, audit_sink=None):
            if audit_sink is not None:
                payload = {
                    "record_id": result.record.record_id,
                    "detector_sources": [],
                    "finding_counts": {},
                    "action_counts": {},
                    "notes": "Applied 0 redactions.",
                    "verification_ok": result.verification_ok,
                    "verification_issues": list(result.verification_issues),
                    "modifications": [],
                }
                audit_sink(payload)
            return result

        MockPipeline.return_value.sanitize_record.side_effect = _sanitize_side_effect

        run_case_transfer(case_id=1, dry_run=True, audit_sink=file_audit_sink(str(audit_path)))

    lines = audit_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) >= 1
    for line in lines:
        if not line.strip():
            continue
        obj = json.loads(line)
        text = json.dumps(obj)
        for forbidden in FORBIDDEN_AUDIT_SUBSTRINGS:
            assert forbidden not in text, f"Audit line should not contain {forbidden!r}"
        assert not PHONE_PATTERN.search(text), "Audit line should not contain phone-like pattern"
        assert "record_id" in obj
        assert "verification_ok" in obj
        assert "verification_issues" in obj
        assert "modifications" in obj


def test_transfer_report_to_dict_serializable() -> None:
    report = TransferReport(
        case_id=1,
        rows_extracted={"patients": 1, "cases": 1},
        rows_inserted={"patients": 1, "cases": 1},
        verification_failures=0,
        audit_events=1,
        replay_skipped=False,
        replay_skip_reason=None,
        started_at="2024-01-01T00:00:00Z",
        finished_at="2024-01-01T00:01:00Z",
        config_path=None,
    )
    d = report.to_dict()
    assert d["case_id"] == 1
    out = json.dumps(d)
    assert "2024-01-01T00:00:00Z" in out
