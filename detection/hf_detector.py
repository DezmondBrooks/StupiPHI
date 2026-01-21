from __future__ import annotations

from typing import List

from detection.detector_base import Detector, Finding, EntityType
from models.hf_runner import HFTokenClassifier
from models.canonical_record import CanonicalRecord


def _map_hf_label_to_entity_type(label: str) -> EntityType:
    """
    Map generic NER labels to our domain entity types.

    dslim/bert-base-NER outputs entity groups like:
      - PER, ORG, LOC, MISC
    """
    l = label.upper().strip()

    if l in {"PER", "PERSON"}:
        return "NAME"
    if l in {"ORG", "ORGANIZATION"}:
        return "ORG"
    if l in {"LOC", "LOCATION"}:
        return "LOCATION"

    return "UNKNOWN"


class HFDetector:
    """
    Hugging Face-based detector for free text fields.

    For now, we only run on encounter_notes.
    Later we can add:
      - other free-text fields
      - structured-field matching (e.g. email regex) as a separate detector
    """

    def __init__(
        self,
        model_name: str = "dslim/bert-base-NER",
        min_confidence: float = 0.50,
        device: int = -1,
    ) -> None:
        self.min_confidence = min_confidence
        self.classifier = HFTokenClassifier(model_name=model_name, device=device)

    def detect(self, record: CanonicalRecord) -> List[Finding]:
        text = record.encounter_notes
        entities = self.classifier.predict(text)

        findings: List[Finding] = []
        for ent in entities:
            if ent.score < self.min_confidence:
                continue

            findings.append(
                Finding(
                    field_path="encounter_notes",
                    entity_type=_map_hf_label_to_entity_type(ent.label),
                    confidence=ent.score,
                    detector_source="huggingface",
                    start=ent.start,
                    end=ent.end,
                    text=ent.text,
                )
            )

        return findings
