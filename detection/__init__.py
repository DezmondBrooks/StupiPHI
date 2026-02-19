"""PHI/PII detection (HF NER + rule-based + structured fields)."""
from detection.detector_base import Detector, Finding, EntityType, DetectorSource
from detection.structured_detector import StructuredFieldDetector

# HFDetector and RuleBasedDetector are not imported here to avoid pulling in transformers
# when only detector_base or structured_detector are needed (e.g. in tests). Use:
#   from detection.hf_detector import HFDetector
#   from detection.rule_detector import RuleBasedDetector

__all__ = [
    "Detector",
    "Finding",
    "EntityType",
    "DetectorSource",
    "StructuredFieldDetector",
]
