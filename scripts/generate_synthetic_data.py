from pathlib import Path

from ingestion.synthetic_generator import generate_to_file


def main() -> None:
    out = generate_to_file(count=25, output_path=Path("data/synthetic_records.jsonl"), seed=42)
    print(f"Wrote synthetic data to: {out}")

    # Print the first line so you know it's real JSONL
    with out.open("r", encoding="utf-8") as f:
        first_line = f.readline().strip()
    print("First record:")
    print(first_line)


if __name__ == "__main__":
    main()
