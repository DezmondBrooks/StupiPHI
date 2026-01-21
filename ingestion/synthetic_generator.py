from __future__ import annotations

import json
import random
from dataclasses import asdict
from pathlib import Path
from typing import Iterator, Optional

from faker import Faker

from models.canonical_record import CanonicalRecord, PatientInfo, Metadata


DEFAULT_DATA_DIR = Path("data")
DEFAULT_OUTPUT_PATH = DEFAULT_DATA_DIR / "synthetic_records.jsonl"


def _seed_everything(seed: int) -> None:
    random.seed(seed)


def generate_record(fake: Faker, record_id: str) -> CanonicalRecord:
    """
    Generate ONE synthetic CanonicalRecord.

    Notes:
    - All fields are fake.
    - We intentionally inject some identifiers into encounter_notes so the detector has something to find.
    """
    first = fake.first_name()
    last = fake.last_name()
    phone = fake.phone_number()
    address = fake.address().replace("\n", ", ")
    email = fake.email()
    dob = fake.date_of_birth(minimum_age=18, maximum_age=90).isoformat()

    # Make notes realistically include identifiers (names, phone, address)
    complaint = random.choice(
        [
            "headache for 3 days",
            "trouble sleeping",
            "feeling anxious",
            "nausea and dizziness",
            "back pain after lifting",
        ]
    )
    encounter_notes = (
        f"Patient {first} {last} reports {complaint}. "
        f"Call {phone}. Address on file: {address}."
    )

    return CanonicalRecord(
        record_id=record_id,
        patient=PatientInfo(
            first_name=first,
            last_name=last,
            dob=dob,
            phone=phone,
            address=address,
            email=email,
        ),
        encounter_notes=encounter_notes,
        metadata=Metadata(
            source="synthetic",
            created_at=CanonicalRecord.now_iso(),
        ),
    )


def generate_records(
    count: int,
    seed: int = 1337,
    locale: str = "en_US",
) -> Iterator[CanonicalRecord]:
    """
    Generate MANY synthetic records deterministically via seed.
    """
    _seed_everything(seed)
    fake = Faker(locale)
    fake.seed_instance(seed)

    for i in range(count):
        yield generate_record(fake=fake, record_id=f"rec_{i:06d}")


def write_jsonl(
    records: Iterator[CanonicalRecord],
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> None:
    """
    Write records to JSONL: one JSON object per line.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")


def generate_to_file(
    count: int,
    output_path: Optional[Path] = None,
    seed: int = 1337,
    locale: str = "en_US",
) -> Path:
    """
    Convenience function to generate records and write them to a file.
    Returns the output path.
    """
    out = output_path or DEFAULT_OUTPUT_PATH
    records = generate_records(count=count, seed=seed, locale=locale)
    write_jsonl(records, output_path=out)
    return out
