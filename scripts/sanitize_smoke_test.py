import json

from ingestion.synthetic_generator import generate_records
from detection.hf_detector import HFDetector
from transformation.plan import build_conservative_plan
from transformation.apply import apply_plan
from audit.audit_log import build_audit_event, to_dict
from verification.verify import verify_basic
from detection.rule_detector import RuleBasedDetector


def main() -> None:
    record = next(generate_records(count=1, seed=42))

    hf = HFDetector(min_confidence=0.40)
    rules = RuleBasedDetector()

    findings = hf.detect(record) + rules.detect(record)

    plan = build_conservative_plan(record_id=record.record_id, findings=findings)
    sanitized, redaction_count = apply_plan(record, plan, seed=99)

    ok, issues = verify_basic(sanitized)
    audit = build_audit_event(
        record_id=record.record_id,
        findings=findings,
        plan=plan,
        redaction_count=redaction_count,
    )

    print("ORIGINAL:")
    print(record.encounter_notes)
    print("\nSANITIZED:")
    print(sanitized.encounter_notes)

    print("\nVERIFY_OK:", ok)
    if issues:
        print("ISSUES:", issues)

    print("\nAUDIT_EVENT:")
    print(json.dumps(to_dict(audit), indent=2))


if __name__ == "__main__":
    main()
