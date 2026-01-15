import csv
from stupify_phi.config import load_config
from stupify_phi.detector import detect_fields
from stupify_phi.anonymizer import anonymize
from stupify_phi.ai_redactor import AIRedactor

def process_csv(input_file: str, output_file: str, config_path: str, use_ai: bool = True):
    config = load_config(config_path)
    ai = AIRedactor() if use_ai else None

    with open(input_file, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        rows = list(reader)

    processed = []
    for row in rows:
        # 1. Redact fields detected by regex/patterns
        detected = detect_fields(row)
        for field, kind in detected.items():
            row[field] = anonymize(row[field], kind)

        # 2. Fallback redaction for AI fields
        for field in config.get("ai_fields", []):
            if field in row:
                if use_ai:
                    row[field] = ai.redact_text(row[field])
                else:
                    row[field] = "[REDACTED]"

        processed.append(row)

    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(processed)
