"""Unit tests for audit event builder."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from stupiphi.detection.detector_base import Finding
from stupiphi.transformation.plan import TransformationPlan, PlanAction
from stupiphi.audit.audit_log import (
    build_audit_event,
    to_dict,
    to_audit_payload,
    file_audit_sink,
    AuditEvent,
)


def test_build_audit_event() -> None:
    findings = [
        Finding("encounter_notes", "NAME", 0.9, "rule", 0, 4, "John"),
        Finding("encounter_notes", "PHONE", 0.95, "rule", 10, 22, "555-123-4567"),
    ]
    plan = TransformationPlan(
        record_id="r1",
        actions=[
            PlanAction("REDACT_TEXT_SPAN", "encounter_notes", "r", start=0, end=4),
            PlanAction("REDACT_TEXT_SPAN", "encounter_notes", "r", start=10, end=22),
        ],
    )
    event = build_audit_event("r1", findings, plan, redaction_count=2)
    assert event.record_id == "r1"
    assert "rule" in event.detector_sources
    assert event.finding_counts.get("NAME") == 1
    assert event.finding_counts.get("PHONE") == 1
    assert event.action_counts.get("REDACT_TEXT_SPAN") == 2
    assert "2" in event.notes or "redaction" in event.notes.lower()


def test_to_dict() -> None:
    event = AuditEvent(
        record_id="r1",
        detector_sources=["rule"],
        finding_counts={"NAME": 1},
        action_counts={"REDACT_TEXT_SPAN": 1},
        notes="Applied 1 redactions.",
    )
    d = to_dict(event)
    assert d["record_id"] == "r1"
    assert d["detector_sources"] == ["rule"]
    assert d["finding_counts"] == {"NAME": 1}


def test_to_audit_payload_includes_verification_and_modifications() -> None:
    event = AuditEvent(
        record_id="r1",
        detector_sources=["rule"],
        finding_counts={"NAME": 1},
        action_counts={"REDACT_TEXT_SPAN": 1},
        notes="Applied 1 redactions.",
    )
    modifications = [
        {"field_path": "encounter_notes", "action_type": "REDACT_TEXT_SPAN", "entity_type": "NAME"},
    ]
    payload = to_audit_payload(
        audit_event=event,
        verification_ok=False,
        verification_issues=["encounter_notes still contains an email-like pattern"],
        modifications=modifications,
    )
    assert payload["record_id"] == "r1"
    assert payload["verification_ok"] is False
    assert payload["verification_issues"] == ["encounter_notes still contains an email-like pattern"]
    assert payload["modifications"] == modifications
    assert "detector_sources" in payload
    assert "finding_counts" in payload


def test_file_audit_sink_appends_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    sink = file_audit_sink(str(path))
    sink({"record_id": "r1", "verification_ok": True, "modifications": []})
    sink({"record_id": "r2", "verification_ok": False, "modifications": [{"field_path": "x", "action_type": "REDACT_TEXT_SPAN", "entity_type": "EMAIL"}]})
    lines = path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0])["record_id"] == "r1"
    assert json.loads(lines[1])["record_id"] == "r2"
    assert json.loads(lines[1])["modifications"][0]["entity_type"] == "EMAIL"
