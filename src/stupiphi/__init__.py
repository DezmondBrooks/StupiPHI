"""
StupiPHI: open-source sanitization engine for healthcare-like data.
Single namespace for pipeline, config, verification, and audit.
"""

from stupiphi.models.canonical_record import CanonicalRecord, PatientInfo, Metadata
from stupiphi.detection.detector_base import Finding, EntityType
from stupiphi.evals.metrics import EvalResult, evaluate_sanitization
from stupiphi.audit.audit_log import (
    build_audit_event,
    AuditEvent,
    to_dict,
    to_audit_payload,
    file_audit_sink,
)
from stupiphi.verification.verify import verify_basic

try:
    # May require optional dependencies (e.g. transformers) via HF detector.
    from stupiphi.sanitizer.pipeline import (  # type: ignore[assignment]
        PipelineConfig,
        SanitizationPipeline,
        SanitizeResult,
    )
except Exception:  # pragma: no cover - allow import without optional deps
    PipelineConfig = None  # type: ignore[assignment]
    SanitizationPipeline = None  # type: ignore[assignment]
    SanitizeResult = None  # type: ignore[assignment]


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
    "to_audit_payload",
    "file_audit_sink",
    "verify_basic",
]
