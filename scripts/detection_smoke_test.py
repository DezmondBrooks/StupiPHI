from ingestion.synthetic_generator import generate_records
from detection.hf_detector import HFDetector


def main() -> None:
    detector = HFDetector(min_confidence=0.50)

    record = next(generate_records(count=1, seed=42))

    print("RECORD_ID:", record.record_id)
    print("TEXT:", record.encounter_notes)
    print("\nFINDINGS:")
    findings = detector.detect(record)
    for f in findings:
        print(
            f"- {f.entity_type} | {f.text!r} | conf={f.confidence:.3f} "
            f"| field={f.field_path} | span=({f.start},{f.end}) | src={f.detector_source}"
        )

    if not findings:
        print("(no findings above threshold)")


if __name__ == "__main__":
    main()
