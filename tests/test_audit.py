"""Unit tests for audit event builder."""
from __future__ import annotations

import pytest

from detection.detector_base import Finding
from transformation.plan import TransformationPlan, PlanAction
from audit.audit_log import build_audit_event, to_dict, AuditEvent


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
