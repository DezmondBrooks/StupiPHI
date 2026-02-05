from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from faker import Faker

from ingestion.synthetic_generator import generate_records
from models.canonical_record import CanonicalRecord
from evals.labels import InjectedLabel


@dataclass(frozen=True)
class LabeledRecord:
    record: CanonicalRecord
    labels: List[InjectedLabel]


def generate_labeled_records(
    count: int = 100,
    seed: int = 123,
) -> List[LabeledRecord]:
    """
    Generate synthetic records and inject known tokens into encounter_notes.
    These injected tokens become ground truth for evaluation.

    IMPORTANT:
    - tokens are synthetic (not real PHI)
    - injection makes it easy to test detection/transformation
    """
    fake = Faker("en_US")
    fake.seed_instance(seed)

    labeled: List[LabeledRecord] = []

    # Use your existing generator for baseline realism
    base_records = generate_records(count=count, seed=seed)

    for rec in base_records:
        # Create injected tokens
        inj_name = f"{fake.first_name()} {fake.last_name()}"
        inj_phone = fake.phone_number()
        inj_email = fake.email()

        # Inject into notes in a consistent, easy-to-search way
        injected_snippet = (
            f" CONTACT: {inj_name} | {inj_phone} | {inj_email}."
        )

        new_notes = rec.encounter_notes + injected_snippet

        new_rec = CanonicalRecord(
            record_id=rec.record_id,
            patient=rec.patient,
            encounter_notes=new_notes,
            metadata=rec.metadata,
        )

        labels = [
            InjectedLabel(label_type="NAME", value=inj_name),
            InjectedLabel(label_type="PHONE", value=inj_phone),
            InjectedLabel(label_type="EMAIL", value=inj_email),
        ]

        labeled.append(LabeledRecord(record=new_rec, labels=labels))

    return labeled
