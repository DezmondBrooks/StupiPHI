from __future__ import annotations

import re
from typing import List

from detection.detector_base import Finding
from models.canonical_record import CanonicalRecord


EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

PHONE_RE = re.compile(
    r"""
    \b
    (?:\+?1[\s\-\.]?)?
    (?:\(?\d{3}\)?[\s\-\.]?)
    \d{3}[\s\-\.]?\d{4}
    (?:\s*(?:x|ext\.?|extension)\s*\d+)?
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)


class RuleBasedDetector:
    """
    Simple pattern-based detector for entities that generic NER models often miss.
    """

    def __init__(self, min_confidence: float = 0.99) -> None:
        # We treat regex matches as high-confidence in this MVP.
        self.min_confidence = min_confidence

    def detect(self, record: CanonicalRecord) -> List[Finding]:
        findings: List[Finding] = []
        text = record.encounter_notes

        for m in EMAIL_RE.finditer(text):
            findings.append(
                Finding(
                    field_path="encounter_notes",
                    entity_type="EMAIL",
                    confidence=self.min_confidence,
                    detector_source="rule",
                    start=m.start(),
                    end=m.end(),
                    text=text[m.start():m.end()],
                )
            )

        for m in PHONE_RE.finditer(text):
            findings.append(
                Finding(
                    field_path="encounter_notes",
                    entity_type="PHONE",
                    confidence=self.min_confidence,
                    detector_source="rule",
                    start=m.start(),
                    end=m.end(),
                    text=text[m.start():m.end()],
                )
            )

        # Sort descending so redaction application remains safe even if caller forgets
        findings.sort(key=lambda f: (f.start or 0), reverse=True)
        return findings
