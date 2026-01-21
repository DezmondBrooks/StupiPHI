from models.canonical_record import CanonicalRecord, PatientInfo, Metadata


def main() -> None:
    record = CanonicalRecord(
        record_id="rec_0001",
        patient=PatientInfo(
            first_name="John",
            last_name="Doe",
            dob="1990-01-01",
            phone="555-123-4567",
            address="123 Main St, Springfield, CA",
            email="john.doe@example.com",
        ),
        encounter_notes="Patient John Doe reports headache for 3 days. Call 555-123-4567.",
        metadata=Metadata(
            source="synthetic",
            created_at=CanonicalRecord.now_iso(),
        ),
    )

    print(record.to_json())


if __name__ == "__main__":
    main()
