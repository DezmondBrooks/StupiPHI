from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from stupiphi.models.canonical_record import CanonicalRecord
from stupiphi.detection.hf_detector import HFDetector
from stupiphi.detection.rule_detector import RuleBasedDetector
from stupiphi.detection.structured_detector import StructuredFieldDetector
from stupiphi.detection.detector_base import Finding
from stupiphi.transformation.plan import build_conservative_plan
from stupiphi.transformation.apply import apply_plan
from stupiphi.audit.audit_log import build_audit_event, AuditEvent
from stupiphi.verification.verify import verify_basic


VALID_DB_POLICY_ACTIONS = frozenset({"preserve", "redact", "pseudonymize", "mask"})


@dataclass(frozen=True)
class PipelineConfig:
    hf_min_confidence: float = 0.40
    faker_seed: int = 99
    enable_hf: bool = True
    enable_rule: bool = True
    enable_structured: bool = True  # Structured-field detector (patient.*)
    pseudonym_salt: str | None = None  # When set, same value -> same pseudonym across records
    # Column-level sanitization during replay: { table_name: { column_name: action } }.
    # None = preserve everything (current behavior). Actions: preserve, redact, pseudonymize, mask.
    database_policy: Optional[Dict[str, Dict[str, str]]] = None


@dataclass(frozen=True)
class SanitizeResult:
    """Result of sanitizing a single record: sanitized record, audit event, and verification outcome."""

    record: CanonicalRecord
    audit_event: AuditEvent
    verification_ok: bool
    verification_issues: List[str]


class SanitizationPipeline:
    def __init__(self, cfg: PipelineConfig) -> None:
        self.cfg = cfg
        self.hf = HFDetector(min_confidence=cfg.hf_min_confidence) if cfg.enable_hf else None
        self.rules = RuleBasedDetector() if cfg.enable_rule else None
        self.structured = StructuredFieldDetector() if cfg.enable_structured else None

    @classmethod
    def from_yaml(cls, path: str) -> "SanitizationPipeline":
        """Build a pipeline from a YAML config file. See stupiphi/config/example.yaml for schema."""
        from stupiphi.config.load import load_config
        return cls(load_config(path))

    def detect_ensemble(self, record: CanonicalRecord) -> List[Finding]:
        findings: List[Finding] = []
        if self.hf is not None:
            findings.extend(self.hf.detect(record))
        if self.rules is not None:
            findings.extend(self.rules.detect(record))
        if self.structured is not None:
            findings.extend(self.structured.detect(record))
        return findings

    def sanitize_record(self, record: CanonicalRecord) -> SanitizeResult:
        findings = self.detect_ensemble(record)
        plan = build_conservative_plan(record_id=record.record_id, findings=findings)
        sanitized, redaction_count = apply_plan(
            record, plan, seed=self.cfg.faker_seed, pseudonym_salt=self.cfg.pseudonym_salt
        )
        audit_event = build_audit_event(
            record_id=record.record_id,
            findings=findings,
            plan=plan,
            redaction_count=redaction_count,
        )
        verification_ok, verification_issues = verify_basic(sanitized)
        return SanitizeResult(
            record=sanitized,
            audit_event=audit_event,
            verification_ok=verification_ok,
            verification_issues=verification_issues,
        )
