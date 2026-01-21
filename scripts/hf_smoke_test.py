from ingestion.synthetic_generator import generate_records
from models.hf_runner import HFTokenClassifier


def main() -> None:
    clf = HFTokenClassifier(model_name="dslim/bert-base-NER", device=-1)

    record = next(generate_records(count=1, seed=42))
    text = record.encounter_notes

    print("TEXT:")
    print(text)
    print("\nENTITIES:")
    for ent in clf.predict(text):
        print(f"- {ent.label} | {ent.text!r} | score={ent.score:.3f} | span=({ent.start},{ent.end})")


if __name__ == "__main__":
    main()
