from __future__ import annotations

import argparse
from pathlib import Path

from evals.labeled_dataset import generate_labeled_records
from evals.metrics import evaluate_sanitization
from sanitizer.pipeline import SanitizationPipeline, PipelineConfig


def main() -> None:
    parser = argparse.ArgumentParser(description="Run StupiPHI evaluation harness.")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to YAML config (default: config.yaml in cwd if present, else built-in defaults)",
    )
    parser.add_argument(
        "--difficulty",
        type=str,
        choices=["easy", "hard"],
        default="easy",
        help="Injection difficulty: easy (trailing snippet) or hard (mid-text, repeated, format variants)",
    )
    parser.add_argument("--count", type=int, default=100, help="Number of labeled records to generate")
    parser.add_argument("--seed", type=int, default=123, help="Random seed for labeled record generation")
    args = parser.parse_args()

    if args.config and Path(args.config).is_file():
        pipeline = SanitizationPipeline.from_yaml(args.config)
    elif Path("config.yaml").is_file():
        pipeline = SanitizationPipeline.from_yaml("config.yaml")
    else:
        pipeline = SanitizationPipeline(PipelineConfig(hf_min_confidence=0.40, faker_seed=99))

    labeled = generate_labeled_records(count=args.count, seed=args.seed, difficulty=args.difficulty)
    sanitized = [pipeline.sanitize_record(lr.record).record for lr in labeled]

    result = evaluate_sanitization(labeled, sanitized)

    print("EVALUATION RESULTS")
    print("------------------")
    print(f"Total labels: {result.total_labels}")
    print(f"False negatives: {result.false_negatives}")
    print(f"False negative rate: {result.false_negative_rate:.3f}")
    print(f"Residual patterns: {result.residual_email_count} records with email, {result.residual_phone_count} with phone")
    print("")
    print("By type:")
    for t, total in result.by_type_total.items():
        fn = result.by_type_fn.get(t, 0)
        rate = (fn / total) if total else 0.0
        print(f"- {t}: total={total}, fn={fn}, fn_rate={rate:.3f}")


if __name__ == "__main__":
    main()
