from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from evals.labels import InjectedLabel
from evals.labeled_dataset import LabeledRecord
from models.canonical_record import CanonicalRecord
from verification.verify import EMAIL_RE, PHONE_RE


@dataclass(frozen=True)
class EvalResult:
    total_labels: int
    false_negatives: int
    false_negative_rate: float
    by_type_total: Dict[str, int]
    by_type_fn: Dict[str, int]
    residual_email_count: int = 0
    residual_phone_count: int = 0


def _count_residual_patterns(records: List[CanonicalRecord]) -> tuple[int, int]:
    """Return (number of records with ≥1 email pattern, number with ≥1 phone pattern)."""
    email_count = sum(1 for r in records if EMAIL_RE.search(r.encounter_notes))
    phone_count = sum(1 for r in records if PHONE_RE.search(r.encounter_notes))
    return email_count, phone_count


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

    residual_email_count, residual_phone_count = _count_residual_patterns(sanitized_records)

    return EvalResult(
        total_labels=total,
        false_negatives=fn,
        false_negative_rate=rate,
        by_type_total=by_type_total,
        by_type_fn=by_type_fn,
        residual_email_count=residual_email_count,
        residual_phone_count=residual_phone_count,
    )
