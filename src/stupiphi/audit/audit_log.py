from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from typing import Any, Callable, Dict, List

from stupiphi.detection.detector_base import Finding
from stupiphi.transformation.plan import TransformationPlan


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


def to_audit_payload(
    audit_event: AuditEvent,
    verification_ok: bool,
    verification_issues: List[str],
    modifications: List[Dict[str, str]],
) -> Dict[str, Any]:
    """Build the full audit payload for the user's sink (no PHI).

    Includes what was modified (modifications) and what may have made it through
    (verification_ok, verification_issues) so it is easily identifiable.
    """
    payload: Dict[str, Any] = dict(asdict(audit_event))
    payload["verification_ok"] = verification_ok
    payload["verification_issues"] = list(verification_issues)
    payload["modifications"] = list(modifications)
    return payload


def file_audit_sink(path: str) -> Callable[[Dict[str, Any]], None]:
    """Return a callable that appends one JSON line per payload to the file at path.

    For user-controlled storage: the tool never writes audit itself; the user
    passes this sink (or their own) when they want file-based audit logging.
    """
    def sink(payload: Dict[str, Any]) -> None:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return sink
