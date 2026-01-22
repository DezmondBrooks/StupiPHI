from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Literal

from detection.detector_base import Finding


ActionType = Literal["REDACT_TEXT_SPAN", "REPLACE_FIELD"]


@dataclass(frozen=True)
class PlanAction:
    action_type: ActionType
    field_path: str
    reason: str

    # For text span redaction
    start: Optional[int] = None
    end: Optional[int] = None

    # For structured field replacement
    replacement: Optional[str] = None


@dataclass(frozen=True)
class TransformationPlan:
    record_id: str
    actions: List[PlanAction]


def build_conservative_plan(record_id: str, findings: List[Finding]) -> TransformationPlan:
    """
    Conservative MVP plan:
    - For any finding in encounter_notes, redact that span.
    - Structured field changes are handled separately (always fake).
    """
    actions: List[PlanAction] = []

    for f in findings:
        if f.field_path == "encounter_notes" and f.start is not None and f.end is not None:
            actions.append(
                PlanAction(
                    action_type="REDACT_TEXT_SPAN",
                    field_path="encounter_notes",
                    start=f.start,
                    end=f.end,
                    reason=f"redact detected entity_type={f.entity_type} source={f.detector_source}",
                )
            )

    # Sort spans descending so redactions don't shift indices
    actions.sort(key=lambda a: (a.start or 0), reverse=True)

    return TransformationPlan(record_id=record_id, actions=actions)
