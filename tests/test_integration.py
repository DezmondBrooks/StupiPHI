"""Integration tests: pipeline on labeled records, FN rate and residual metrics."""
from __future__ import annotations

import pytest

pytest.importorskip("transformers", reason="transformers optional for integration tests")

from evals.labeled_dataset import generate_labeled_records
from evals.metrics import evaluate_sanitization
from sanitizer.pipeline import SanitizationPipeline, PipelineConfig


def test_pipeline_eval_easy_fn_rate_below_threshold() -> None:
    """Run pipeline on a small labeled set; expect FN rate below a loose threshold."""
    cfg = PipelineConfig(hf_min_confidence=0.40, faker_seed=99)
    pipeline = SanitizationPipeline(cfg)
    labeled = generate_labeled_records(count=20, seed=456, difficulty="easy")
    sanitized = [pipeline.sanitize_record(lr.record).record for lr in labeled]
    result = evaluate_sanitization(labeled, sanitized)
    # Allow some FNs due to detector variance; assert not catastrophic
    assert result.false_negative_rate < 0.50, "FN rate should be below 50% on easy set"
    assert result.total_labels > 0


def test_pipeline_eval_audit_and_verification_present() -> None:
    """Sanitize one record and assert audit event and verification are in result."""
    cfg = PipelineConfig(hf_min_confidence=0.40, faker_seed=99)
    pipeline = SanitizationPipeline(cfg)
    labeled = generate_labeled_records(count=1, seed=789, difficulty="easy")
    result = pipeline.sanitize_record(labeled[0].record)
    assert result.audit_event.record_id == labeled[0].record.record_id
    assert hasattr(result, "verification_ok")
    assert isinstance(result.verification_issues, list)


def test_residual_metrics_computed() -> None:
    """Eval result includes residual email/phone counts."""
    cfg = PipelineConfig(hf_min_confidence=0.40, faker_seed=99)
    pipeline = SanitizationPipeline(cfg)
    labeled = generate_labeled_records(count=5, seed=111, difficulty="easy")
    sanitized = [pipeline.sanitize_record(lr.record).record for lr in labeled]
    result = evaluate_sanitization(labeled, sanitized)
    assert hasattr(result, "residual_email_count")
    assert hasattr(result, "residual_phone_count")
    assert isinstance(result.residual_email_count, int)
    assert isinstance(result.residual_phone_count, int)
