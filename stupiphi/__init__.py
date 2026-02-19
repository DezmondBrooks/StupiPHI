"""
StupiPHI: open-source sanitization engine for healthcare-like data.
Single namespace for pipeline, config, verification, and audit.
"""
from sanitizer.pipeline import (
    PipelineConfig,
    SanitizationPipeline,
    SanitizeResult,
)
from models.canonical_record import CanonicalRecord, PatientInfo, Metadata
from detection.detector_base import Finding, EntityType
from evals.metrics import EvalResult, evaluate_sanitization
from audit.audit_log import build_audit_event, AuditEvent, to_dict
from verification.verify import verify_basic

__all__ = [
    "PipelineConfig",
    "SanitizationPipeline",
    "SanitizeResult",
    "CanonicalRecord",
    "PatientInfo",
    "Metadata",
    "Finding",
    "EntityType",
    "EvalResult",
    "evaluate_sanitization",
    "build_audit_event",
    "AuditEvent",
    "to_dict",
    "verify_basic",
]
