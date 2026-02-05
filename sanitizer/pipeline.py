from dataclasses import dataclass
from typing import List

from models.canonical_record import CanonicalRecord
from detection.hf_detector import HFDetector
from detection.rule_detector import RuleBasedDetector
from detection.detector_base import Finding
from transformation.plan import build_conservative_plan
from transformation.apply import apply_plan


@dataclass(frozen=True)
class PipelineConfig:
    hf_min_confidence: float = 0.40
    faker_seed: int = 99


class SanitizationPipeline:
    def __init__(self, cfg: PipelineConfig) -> None:
        self.cfg = cfg
        self.hf = HFDetector(min_confidence=cfg.hf_min_confidence)
        self.rules = RuleBasedDetector()

    def detect_ensemble(self, record: CanonicalRecord) -> List[Finding]:
        return self.hf.detect(record) + self.rules.detect(record)

    def sanitize_record(self, record: CanonicalRecord) -> CanonicalRecord:
        findings = self.detect_ensemble(record)
        plan = build_conservative_plan(record_id=record.record_id, findings=findings)
        sanitized, _ = apply_plan(record, plan, seed=self.cfg.faker_seed)
        return sanitized
