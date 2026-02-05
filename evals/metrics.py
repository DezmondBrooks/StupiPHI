from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from evals.labels import InjectedLabel
from evals.labeled_dataset import LabeledRecord
from models.canonical_record import CanonicalRecord


@dataclass(frozen=True)
class EvalResult:
    total_labels: int
    false_negatives: int
    false_negative_rate: float
    by_type_total: Dict[str, int]
    by_type_fn: Dict[str, int]


def _label_present_in_record(label: InjectedLabel, sanitized: CanonicalRecord) -> bool:
    """
    v1 check: does the injected token still appear verbatim in encounter_notes?
    This is a strict check and good for catching failures.
    """
    if label.field_path != "encounter_notes":
        return False
    return label.value in sanitized.encounter_notes


def evaluate_sanitization(
    labeled_records: List[LabeledRecord],
    sanitized_records: List[CanonicalRecord],
) -> EvalResult:
    """
    Compare injected ground-truth labels against sanitized output.
    False negative = label still present after sanitization.
    """
    assert len(labeled_records) == len(sanitized_records), "Record count mismatch"

    total = 0
    fn = 0

    by_type_total: Dict[str, int] = {}
    by_type_fn: Dict[str, int] = {}

    for lr, sr in zip(labeled_records, sanitized_records):
        for label in lr.labels:
            total += 1
            by_type_total[label.label_type] = by_type_total.get(label.label_type, 0) + 1

            leaked = _label_present_in_record(label, sr)
            if leaked:
                fn += 1
                by_type_fn[label.label_type] = by_type_fn.get(label.label_type, 0) + 1

    rate = (fn / total) if total else 0.0

    return EvalResult(
        total_labels=total,
        false_negatives=fn,
        false_negative_rate=rate,
        by_type_total=by_type_total,
        by_type_fn=by_type_fn,
    )
