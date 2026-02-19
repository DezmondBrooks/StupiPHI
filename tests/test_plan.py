"""Unit tests for transformation plan builder."""
from __future__ import annotations

import pytest

from detection.detector_base import Finding
from transformation.plan import build_conservative_plan, PlanAction, TransformationPlan


def test_build_conservative_plan_empty_findings() -> None:
    plan = build_conservative_plan(record_id="r1", findings=[])
    assert plan.record_id == "r1"
    assert plan.actions == []


def test_build_conservative_plan_encounter_notes_spans() -> None:
    findings = [
        Finding(
            field_path="encounter_notes",
            entity_type="NAME",
            confidence=0.9,
            detector_source="rule",
            start=10,
            end=18,
            text="John Doe",
        ),
        Finding(
            field_path="encounter_notes",
            entity_type="PHONE",
            confidence=0.95,
            detector_source="rule",
            start=30,
            end=42,
            text="555-123-4567",
        ),
    ]
    plan = build_conservative_plan(record_id="r1", findings=findings)
    assert plan.record_id == "r1"
    assert len(plan.actions) == 2
    for a in plan.actions:
        assert a.action_type == "REDACT_TEXT_SPAN"
        assert a.field_path == "encounter_notes"
    starts = [a.start for a in plan.actions]
    assert 10 in starts and 30 in starts
    # Spans sorted descending by start
    assert plan.actions[0].start >= plan.actions[1].start


def test_build_conservative_plan_ignores_other_fields() -> None:
    findings = [
        Finding(
            field_path="patient.first_name",
            entity_type="NAME",
            confidence=1.0,
            detector_source="rule",
            start=None,
            end=None,
        ),
    ]
    plan = build_conservative_plan(record_id="r1", findings=findings)
    assert len(plan.actions) == 0


def test_build_conservative_plan_ignores_missing_spans() -> None:
    findings = [
        Finding(
            field_path="encounter_notes",
            entity_type="NAME",
            confidence=0.9,
            detector_source="huggingface",
            start=None,
            end=None,
        ),
    ]
    plan = build_conservative_plan(record_id="r1", findings=findings)
    assert len(plan.actions) == 0
