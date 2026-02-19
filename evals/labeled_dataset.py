from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal

from faker import Faker

from ingestion.synthetic_generator import generate_records
from models.canonical_record import CanonicalRecord
from evals.labels import InjectedLabel

Difficulty = Literal["easy", "hard"]


@dataclass(frozen=True)
class LabeledRecord:
    record: CanonicalRecord
    labels: List[InjectedLabel]


def _inject_easy(
    fake: Faker,
    rec: CanonicalRecord,
) -> tuple[str, List[InjectedLabel]]:
    """Single trailing snippet: CONTACT: name | phone | email."""
    inj_name = f"{fake.first_name()} {fake.last_name()}"
    inj_phone = fake.phone_number()
    inj_email = fake.email()
    snippet = f" CONTACT: {inj_name} | {inj_phone} | {inj_email}."
    new_notes = rec.encounter_notes + snippet
    labels = [
        InjectedLabel(label_type="NAME", value=inj_name),
        InjectedLabel(label_type="PHONE", value=inj_phone),
        InjectedLabel(label_type="EMAIL", value=inj_email),
    ]
    return new_notes, labels


def _inject_hard(
    fake: Faker,
    rec: CanonicalRecord,
) -> tuple[str, List[InjectedLabel]]:
    """Mid-text injection, repeated identifiers, and formatting variation (phone with/without spaces)."""
    inj_name = f"{fake.first_name()} {fake.last_name()}"
    raw_phone = fake.numerify(text="##########")
    inj_phone_formatted = f"({raw_phone[:3]}) {raw_phone[3:6]}-{raw_phone[6:]}"
    inj_email = fake.email()

    notes = rec.encounter_notes
    mid = max(0, len(notes) // 2)

    # Inject in the middle and again at the end; repeat name once more in narrative form
    prefix, suffix = notes[:mid], notes[mid:]
    block1 = f" Refer to Dr. {inj_name} for follow-up. Tel: {inj_phone_formatted} or {inj_email}. "
    block2 = f" CONTACT: {inj_name} | {inj_phone_formatted} | {inj_email}."
    new_notes = prefix + block1 + suffix + block2

    # Labels: name appears twice, phone (both raw and formatted for detection flexibility), email twice
    labels = [
        InjectedLabel(label_type="NAME", value=inj_name),
        InjectedLabel(label_type="NAME", value=inj_name),
        InjectedLabel(label_type="PHONE", value=inj_phone_formatted),
        InjectedLabel(label_type="PHONE", value=raw_phone),
        InjectedLabel(label_type="EMAIL", value=inj_email),
        InjectedLabel(label_type="EMAIL", value=inj_email),
    ]
    return new_notes, labels


def generate_labeled_records(
    count: int = 100,
    seed: int = 123,
    difficulty: Difficulty = "easy",
) -> List[LabeledRecord]:
    """
    Generate synthetic records and inject known tokens into encounter_notes.
    These injected tokens become ground truth for evaluation.

    difficulty:
      - "easy": single trailing snippet (CONTACT: name | phone | email).
      - "hard": mid-text injection, repeated identifiers, phone formatting variation.

    IMPORTANT:
    - tokens are synthetic (not real PHI)
    - injection makes it easy to test detection/transformation
    """
    fake = Faker("en_US")
    fake.seed_instance(seed)

    labeled: List[LabeledRecord] = []
    base_records = generate_records(count=count, seed=seed)

    inject_fn = _inject_easy if difficulty == "easy" else _inject_hard

    for rec in base_records:
        new_notes, labels = inject_fn(fake, rec)
        new_rec = CanonicalRecord(
            record_id=rec.record_id,
            patient=rec.patient,
            encounter_notes=new_notes,
            metadata=rec.metadata,
        )
        labeled.append(LabeledRecord(record=new_rec, labels=labels))

    return labeled
