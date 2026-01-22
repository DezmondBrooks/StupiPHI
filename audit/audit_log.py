from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List

from detection.detector_base import Finding
from transformation.plan import TransformationPlan


@dataclass(frozen=True)
class AuditEvent:
    record_id: str
    detector_sources: List[str]
    finding_counts: Dict[str, int]
    action_counts: Dict[str, int]
    notes: str


def build_audit_event(
    record_id: str,
    findings: List[Finding],
    plan: TransformationPlan,
    redaction_count: int,
) -> AuditEvent:
    sources = sorted({f.detector_source for f in findings})

    finding_counts: Dict[str, int] = {}
    for f in findings:
        finding_counts[f.entity_type] = finding_counts.get(f.entity_type, 0) + 1

    action_counts: Dict[str, int] = {}
    for a in plan.actions:
        action_counts[a.action_type] = action_counts.get(a.action_type, 0) + 1

    # IMPORTANT: audit should not include raw PHI strings
    return AuditEvent(
        record_id=record_id,
        detector_sources=sources,
        finding_counts=finding_counts,
        action_counts=action_counts,
        notes=f"Applied {redaction_count} free-text redactions; structured fields replaced with synthetic values.",
    )


def to_dict(event: AuditEvent) -> Dict[str, Any]:
    return asdict(event)
