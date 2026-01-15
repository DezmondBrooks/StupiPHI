import argparse
from stupify_phi.runner import process_csv

def main():
    parser = argparse.ArgumentParser(description="Stupify-PHI - PII/PHI redaction tool")
    parser.add_argument("--config", required=True, help="Path to YAML config")
    parser.add_argument("--input", required=True, help="Path to input CSV file")
    parser.add_argument("--output", required=True, help="Path to write anonymized data")
    parser.add_argument("--no-ai", action="store_true", help="Disable AI redaction")

    args = parser.parse_args()

    process_csv(
        input_file=args.input,
        output_file=args.output,
        config_path=args.config,
        use_ai=not args.no_ai
    )

if __name__ == "__main__":
    main()
