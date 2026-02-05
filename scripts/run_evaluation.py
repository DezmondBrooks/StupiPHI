from __future__ import annotations

from evals.labeled_dataset import generate_labeled_records
from evals.metrics import evaluate_sanitization
from sanitizer.pipeline import SanitizationPipeline, PipelineConfig


def main() -> None:
    cfg = PipelineConfig(hf_min_confidence=0.40, faker_seed=99)
    pipeline = SanitizationPipeline(cfg)

    labeled = generate_labeled_records(count=100, seed=123)
    sanitized = [pipeline.sanitize_record(lr.record) for lr in labeled]

    result = evaluate_sanitization(labeled, sanitized)

    print("EVALUATION RESULTS")
    print("------------------")
    print(f"Total labels: {result.total_labels}")
    print(f"False negatives: {result.false_negatives}")
    print(f"False negative rate: {result.false_negative_rate:.3f}")
    print("")
    print("By type:")
    for t, total in result.by_type_total.items():
        fn = result.by_type_fn.get(t, 0)
        rate = (fn / total) if total else 0.0
        print(f"- {t}: total={total}, fn={fn}, fn_rate={rate:.3f}")


if __name__ == "__main__":
    main()
