import json

from ingestion.synthetic_generator import generate_records
from sanitizer.pipeline import SanitizationPipeline, PipelineConfig
from audit.audit_log import to_dict


def main() -> None:
    record = next(generate_records(count=1, seed=42))
    cfg = PipelineConfig(hf_min_confidence=0.40, faker_seed=99)
    pipeline = SanitizationPipeline(cfg)

    result = pipeline.sanitize_record(record)

    print("ORIGINAL:")
    print(record.encounter_notes)
    print("\nSANITIZED:")
    print(result.record.encounter_notes)

    print("\nVERIFY_OK:", result.verification_ok)
    if result.verification_issues:
        print("ISSUES:", result.verification_issues)

    print("\nAUDIT_EVENT:")
    print(json.dumps(to_dict(result.audit_event), indent=2))


if __name__ == "__main__":
    main()
