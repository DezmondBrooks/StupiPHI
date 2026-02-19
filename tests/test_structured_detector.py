"""Unit tests for structured-field detector."""
from __future__ import annotations

from models.canonical_record import CanonicalRecord, PatientInfo, Metadata
from detection.structured_detector import StructuredFieldDetector


def _record(
    first_name: str = "Jane",
    last_name: str = "Doe",
    dob: str = "1990-01-15",
    phone: str = "555-123-4567",
    address: str = "123 Main St",
    email: str | None = "jane@example.com",
) -> CanonicalRecord:
    return CanonicalRecord(
        record_id="r1",
        patient=PatientInfo(
            first_name=first_name,
            last_name=last_name,
            dob=dob,
            phone=phone,
            address=address,
            email=email,
        ),
        encounter_notes="Some notes.",
        metadata=Metadata(source="test", created_at="2024-01-01T00:00:00Z"),
    )


def test_structured_detector_emits_findings_for_patient_fields() -> None:
    detector = StructuredFieldDetector()
    record = _record()
    findings = detector.detect(record)
    field_paths = {f.field_path for f in findings}
    assert "patient.first_name" in field_paths
    assert "patient.last_name" in field_paths
    assert "patient.dob" in field_paths
    assert "patient.phone" in field_paths
    assert "patient.address" in field_paths
    assert "patient.email" in field_paths
    for f in findings:
        assert f.detector_source == "structured"
        assert f.start is None
        assert f.end is None
        assert f.confidence == 1.0


def test_structured_detector_skips_none_email() -> None:
    detector = StructuredFieldDetector()
    record = _record(email=None)
    findings = detector.detect(record)
    field_paths = {f.field_path for f in findings}
    assert "patient.email" not in field_paths
    assert "patient.first_name" in field_paths


def test_structured_detector_entity_types() -> None:
    detector = StructuredFieldDetector()
    record = _record()
    findings = detector.detect(record)
    by_path = {f.field_path: f.entity_type for f in findings}
    assert by_path.get("patient.first_name") == "NAME"
    assert by_path.get("patient.last_name") == "NAME"
    assert by_path.get("patient.dob") == "DOB"
    assert by_path.get("patient.phone") == "PHONE"
    assert by_path.get("patient.address") == "ADDRESS"
    assert by_path.get("patient.email") == "EMAIL"
