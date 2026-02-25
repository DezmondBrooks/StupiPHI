"""CLI entry point: stupiphi run-eval, stupiphi sanitize."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from stupiphi.evals.labeled_dataset import generate_labeled_records
from stupiphi.evals.metrics import evaluate_sanitization
from stupiphi.ingestion.synthetic_generator import generate_records
from stupiphi.sanitizer.pipeline import SanitizationPipeline, PipelineConfig
from stupiphi.audit.audit_log import to_dict
from stupiphi.jobs.case_transfer import (
    run_case_transfer,
    VerificationFailedError,
    DBVerificationFailedError,
)


def _run_eval(args: argparse.Namespace) -> None:
    if args.config and Path(args.config).is_file():
        pipeline = SanitizationPipeline.from_yaml(args.config)
    elif Path("config.yaml").is_file():
        pipeline = SanitizationPipeline.from_yaml("config.yaml")
    else:
        pipeline = SanitizationPipeline(PipelineConfig(hf_min_confidence=0.40, faker_seed=99))

    labeled = generate_labeled_records(
        count=args.count, seed=args.seed, difficulty=args.difficulty
    )
    sanitized = [pipeline.sanitize_record(lr.record).record for lr in labeled]
    result = evaluate_sanitization(labeled, sanitized)

    print("EVALUATION RESULTS")
    print("------------------")
    print(f"Total labels: {result.total_labels}")
    print(f"False negatives: {result.false_negatives}")
    print(f"False negative rate: {result.false_negative_rate:.3f}")
    print(
        f"Residual patterns: {result.residual_email_count} records with email, "
        f"{result.residual_phone_count} with phone"
    )
    print("")
    print("By type:")
    for t, total in result.by_type_total.items():
        fn = result.by_type_fn.get(t, 0)
        rate = (fn / total) if total else 0.0
        print(f"- {t}: total={total}, fn={fn}, fn_rate={rate:.3f}")


def _sanitize(args: argparse.Namespace) -> None:
    if args.config and Path(args.config).is_file():
        pipeline = SanitizationPipeline.from_yaml(args.config)
    elif Path("config.yaml").is_file():
        pipeline = SanitizationPipeline.from_yaml("config.yaml")
    else:
        pipeline = SanitizationPipeline(PipelineConfig(hf_min_confidence=0.40, faker_seed=99))

    record = next(generate_records(count=1, seed=args.seed))
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


def _transfer_case(args: argparse.Namespace) -> None:
    try:
        report = run_case_transfer(
            case_id=args.case_id,
            config_path=args.config,
            dry_run=args.dry_run,
            report_out=args.report_out,
            audit_out=args.audit_out,
            fail_on_verification=args.fail_on_verification,
            verify_dev=args.verify_dev,
            fail_on_db_verify=args.fail_on_db_verify,
        )
    except VerificationFailedError as e:
        print(str(e))
        if args.report_out:
            print(f"Report written to: {args.report_out}")
        if args.audit_out:
            print(f"Audit written to: {args.audit_out}")
        raise SystemExit(1)
    except DBVerificationFailedError as e:
        print(str(e))
        if args.report_out:
            print(f"Report written to: {args.report_out}")
        if args.audit_out:
            print(f"Audit written to: {args.audit_out}")
        raise SystemExit(1)

    print(f"Case {report.case_id} transfer summary")
    print("------------------------------")
    print("Extracted:")
    for table, count in report.rows_extracted.items():
        print(f"  {table}: {count}")
    print("Inserted:")
    for table, count in report.rows_inserted.items():
        print(f"  {table}: {count}")
    print(f"Verification failures: {report.verification_failures}")
    print(f"Audit events: {report.audit_events}")
    if report.replay_skipped and report.replay_skip_reason:
        print(f"Replay skipped: {report.replay_skip_reason}")
    if report.db_verification_ok:
        print("DB verification: ok")
    else:
        print(f"DB verification: FAILED ({report.db_findings_count} finding(s))")
        if report.db_findings_by_table:
            parts = [f"{t}={c}" for t, c in report.db_findings_by_table.items()]
            print(f"Findings by table: {', '.join(parts)}")
    if args.report_out:
        print(f"Report written to: {args.report_out}")
    if args.audit_out:
        print(f"Audit written to: {args.audit_out}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="stupiphi", description="StupiPHI sanitization engine CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    eval_parser = subparsers.add_parser("run-eval", help="Run evaluation harness")
    eval_parser.add_argument("--config", type=str, default=None, help="Path to YAML config")
    eval_parser.add_argument("--difficulty", choices=["easy", "hard"], default="easy")
    eval_parser.add_argument("--count", type=int, default=100)
    eval_parser.add_argument("--seed", type=int, default=123)
    eval_parser.set_defaults(func=_run_eval)

    sanitize_parser = subparsers.add_parser("sanitize", help="Sanitize one synthetic record (smoke test)")
    sanitize_parser.add_argument("--config", type=str, default=None, help="Path to YAML config")
    sanitize_parser.add_argument("--seed", type=int, default=42)
    sanitize_parser.set_defaults(func=_sanitize)

    transfer_parser = subparsers.add_parser(
        "transfer-case", help="Transfer and sanitize a case slice from prod_db to dev_db"
    )
    transfer_parser.add_argument("--case-id", type=int, required=True, help="Case ID to transfer")
    transfer_parser.add_argument(
        "--config", type=str, default=None, help="Optional path to YAML config for the pipeline"
    )
    transfer_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run extract, map, sanitize and optional artifacts; do not write to dev DB",
    )
    transfer_parser.add_argument(
        "--report-out", type=str, default=None, help="Write TransferReport JSON to this path"
    )
    transfer_parser.add_argument(
        "--audit-out", type=str, default=None, help="Write audit events as JSONL to this path"
    )
    transfer_parser.add_argument(
        "--fail-on-verification",
        action="store_true",
        help="Abort before replay if any sanitized record fails verification",
    )
    transfer_parser.add_argument(
        "--verify-dev",
        action="store_true",
        default=True,
        help="Run DB verification on dev after replay (default: on)",
    )
    transfer_parser.add_argument(
        "--no-verify-dev",
        action="store_false",
        dest="verify_dev",
        help="Skip DB verification on dev after replay",
    )
    transfer_parser.add_argument(
        "--fail-on-db-verify",
        action="store_true",
        help="Exit non-zero if DB verification finds residual email/phone patterns in dev",
    )
    transfer_parser.set_defaults(func=_transfer_case)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
