"""Minimal example: build a pipeline, sanitize one record, and print summary."""
from __future__ import annotations

from stupiphi import SanitizationPipeline, PipelineConfig, verify_basic
from stupiphi.models.canonical_record import CanonicalRecord, PatientInfo, Metadata


def main() -> None:
    # Configure the pipeline (defaults are usually fine).
    cfg = PipelineConfig(hf_min_confidence=0.40, faker_seed=99)
    pipeline = SanitizationPipeline(cfg)

    # Build a tiny synthetic record.
    record = CanonicalRecord(
        record_id="demo:1",
        patient=PatientInfo(
            first_name="Jane",
            last_name="Doe",
            dob="1990-01-01",
            phone="555-123-4567",
            address="123 Main St",
            email="jane@example.com",
        ),
        encounter_notes="Follow-up with Jane Doe at 123 Main St. Call 555-123-4567.",
        metadata=Metadata(source="demo", created_at="2024-01-01T00:00:00Z"),
    )

    # Run sanitization.
    result = pipeline.sanitize_record(record)

    # Basic verification (email/phone patterns in free text).
    v_ok, v_issues = verify_basic(result.record)

    print("=== Sanitized record ===")
    print(result.record)
    print("\n=== Verification ===")
    print("verification_ok:", result.verification_ok, "basic_ok:", v_ok)
    print("verification_issues:", result.verification_issues or v_issues)
    print("\n=== Audit summary ===")
    print("record_id:", result.audit_event.record_id)
    print("finding_counts:", result.audit_event.finding_counts)
    print("action_counts:", result.audit_event.action_counts)


if __name__ == "__main__":
    main()
