"""CLI entry point: stupiphi run-eval, stupiphi sanitize."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from evals.labeled_dataset import generate_labeled_records
from evals.metrics import evaluate_sanitization
from ingestion.synthetic_generator import generate_records
from sanitizer.pipeline import SanitizationPipeline, PipelineConfig
from audit.audit_log import to_dict


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

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
