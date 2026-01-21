from __future__ import annotations

from dataclasses import dataclass
from typing import List, Protocol, Optional, Literal

EntityType = Literal[
    "NAME",
    "PHONE",
    "EMAIL",
    "ADDRESS",
    "DOB",
    "LOCATION",
    "ORG",
    "UNKNOWN",
]

DetectorSource = Literal["huggingface", "llm", "rule"]


@dataclass(frozen=True)
class Finding:
    """
    A standardized detection result.

    field_path:
      - Where the entity was found (e.g. "encounter_notes", "patient.first_name").
    start/end:
      - Character offsets for text fields (None for purely structured matches).
    entity_type:
      - Normalized category used by transformations and evaluation.
    confidence:
      - 0.0–1.0 score (best-effort across detectors).
    detector_source:
      - Which detector produced this finding.
    """
    field_path: str
    entity_type: EntityType
    confidence: float
    detector_source: DetectorSource
    start: Optional[int] = None
    end: Optional[int] = None
    text: Optional[str] = None


class Detector(Protocol):
    """
    All detectors must implement this interface.
    """

    def detect(self, record) -> List[Finding]:
        ...
