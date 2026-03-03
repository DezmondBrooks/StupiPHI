## StupiPHI demo script (internal engineering)

This is a 3–5 minute path you can follow live. All commands assume you are in the `StupiPHI` repo root with Python 3.10+ and dependencies installed.

---

### 1. Environment warm‑up (do **before** the demo)

```bash
python -m pip install -e .

# Optional but recommended: run once to download the HF model + warm Torch
python -m stupiphi.cli sanitize --seed 42
```

On Windows, if the `stupiphi` command is not found on `PATH`, prefer the `python -m stupiphi.cli ...` form used below.

---

### 2. Story framing (30–60 seconds)

- **Problem**: PHI/PII makes it hard to use realistic production‑like data in dev and staging.
- **StupiPHI**: a sanitization engine that detects identifiers (ML + rules + structured fields), redacts/pseudonymizes, and keeps schema + relationships intact.
- **What we’ll show**:
  - One record before/after sanitization + verification + audit.
  - A small evaluation run with FN rate and residual PHI patterns.

---

### 3. Single‑record sanitization (1–2 minutes)

Command (in terminal):

```bash
python -m stupiphi.cli sanitize --seed 42
```

Talking points:

- The system generates a **synthetic CanonicalRecord** with obviously PHI‑like content (name, phone, address, email) in `encounter_notes` and structured fields.
- The CLI prints:
  - **ORIGINAL**: raw notes with PHI‑like tokens.
  - **SANITIZED**: redacted / pseudonymized version.
  - **VERIFY_OK** and optional **ISSUES** from `verify_basic`.
  - **AUDIT_EVENT** as JSON (no raw PHI), including detector sources and counts by type/action.
- Call out that this is the **same pipeline** used in production modes; here it is wired to a synthetic generator for safe demos.

Expected output shape (abbreviated):

- `ORIGINAL: Patient Danielle Johnson ... Call 533-... Address on file: ...`
- `SANITIZED: Patient [REDACTED] ... Call [REDACTED] ...`
- `VERIFY_OK: True`
- `AUDIT_EVENT: { "record_id": "rec_000000", "detector_sources": [...], ... }`

---

### 4. Evaluation run (1–2 minutes)

Command:

```bash
python -m stupiphi.cli run-eval --count 20 --difficulty hard
```

Talking points:

- This uses the **evaluation harness** with labeled synthetic records (tokens injected into notes as ground truth).
- Output includes:
  - **Total labels** (how many PHI‑like tokens were injected).
  - **False negatives** and **false negative rate**.
  - **Residual patterns**: number of records where email/phone patterns remain after sanitization.
  - Breakdown **by type** (NAME, PHONE, EMAIL).
- Emphasize that the system is tuned to **prefer false positives over false negatives**; evaluation focuses on safety, not user‑visible precision.

Expected output shape (abbreviated):

```text
EVALUATION RESULTS
------------------
Total labels: 120
False negatives: 0
False negative rate: 0.000
Residual patterns: 0 records with email, 0 with phone

By type:
- NAME: total=40, fn=0, fn_rate=0.000
- PHONE: total=40, fn=0, fn_rate=0.000
- EMAIL: total=40, fn=0, fn_rate=0.000
```

---

### 5. Case transfer (describe only, optional 30–60 seconds)

If you do **not** have Postgres env vars configured, do **not** run this live; just show the command and explain.

Command to show:

```bash
python -m stupiphi.cli transfer-case --case-id 123 --dry-run
```

Talking points:

- This is the **production‑like** path: pull a case slice from `prod_db`, sanitize via the same pipeline, then replay into `dev_db` with audit and optional DB‑level verification.
- `--dry-run` avoids writing to dev DB; you can still emit a transfer report and audit events.
- If the required Postgres env vars are missing, the CLI fails with a clear error:
  - `RuntimeError: PROD_DB_USER and PROD_DB_DBNAME must be set (or PROD_DB_DSN) for Postgres connection`

---

### 6. API usage follow‑up (optional quick reference)

If engineers want to see the Python API after the CLI demo, you can sketch:

```python
from stupiphi import SanitizationPipeline, PipelineConfig
from stupiphi.ingestion.synthetic_generator import generate_records

cfg = PipelineConfig(hf_min_confidence=0.40, faker_seed=99)
pipeline = SanitizationPipeline(cfg)
record = next(generate_records(count=1, seed=42))
result = pipeline.sanitize_record(record)
print(result.record.encounter_notes, result.verification_ok)
```

Mention that the public API is summarized in `README.md` (Pipeline, config, verify, audit, eval) and that architecture/data‑flow details live in `SYSTEM_OVERVIEW.txt` and `DATA_FLOW.txt`.

