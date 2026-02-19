"""
Structured-field detector: emits Findings for known patient fields (DOB, address, phone, email, name).
Makes detection explicit for structured data so audit and future per-type config are consistent.
"""
from __future__ import annotations

from typing import List

from detection.detector_base import Finding
from models.canonical_record import CanonicalRecord

STRUCTURED_FIELDS: List[tuple[str, str]] = [
    ("patient.first_name", "NAME"),
    ("patient.last_name", "NAME"),
    ("patient.dob", "DOB"),
    ("patient.phone", "PHONE"),
    ("patient.address", "ADDRESS"),
    ("patient.email", "EMAIL"),
]


class StructuredFieldDetector:
    """
    Detector that reports every structured patient field as a Finding (start/end None).
    Confidence is high since these are explicit schema fields.
    """

    def __init__(self, confidence: float = 1.0) -> None:
        self.confidence = confidence

    def detect(self, record: CanonicalRecord) -> List[Finding]:
        findings: List[Finding] = []
        p = record.patient
        for field_path, entity_type in STRUCTURED_FIELDS:
            if field_path == "patient.first_name":
                value = p.first_name
            elif field_path == "patient.last_name":
                value = p.last_name
            elif field_path == "patient.dob":
                value = p.dob
            elif field_path == "patient.phone":
                value = p.phone
            elif field_path == "patient.address":
                value = p.address
            elif field_path == "patient.email":
                if p.email is None:
                    continue
                value = p.email
            else:
                continue
            if not value:
                continue
            findings.append(
                Finding(
                    field_path=field_path,
                    entity_type=entity_type,
                    confidence=self.confidence,
                    detector_source="structured",
                    start=None,
                    end=None,
                    text=None,
                )
            )
        return findings
