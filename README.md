# StupiPHI

StupiPHI is an open-source sanitization engine that safely transforms sensitive healthcare-like data into development-ready datasets without exposing PHI/PII. It detects identifiers (structured and in free text), applies conservative transformations (redact or pseudonymize), preserves schema and relational structure, and produces auditable, verifiable outputs. It is designed for use in HIPAA-regulated environments as a technical safeguard; **StupiPHI does not claim HIPAA compliance**—deploy and operate it within your own compliance framework.

---

## Quick start

**Install (editable):**

```bash
pip install -e .
```

**Optional:** Copy the example config and adjust if needed:

```bash
cp config/example.yaml config.yaml
```

**Run evaluation** (labeled synthetic records, false-negative and residual metrics):

```bash
stupiphi run-eval
# Or with options:
stupiphi run-eval --config config.yaml --difficulty easy --count 100 --seed 123
```

**Sanitize one synthetic record** (smoke test: pipeline + audit + verification):

```bash
stupiphi sanitize
stupiphi sanitize --config config.yaml --seed 42
```

Or via Python (see `examples/quickstart.py` for a full script):

```python
from stupiphi import SanitizationPipeline, PipelineConfig

cfg = PipelineConfig(hf_min_confidence=0.40, faker_seed=99)
pipeline = SanitizationPipeline(cfg)
result = pipeline.sanitize_record(record)
print(result.record)
print(result.verification_ok, result.verification_issues)
print(result.audit_event.to_dict())
```

---

## Demo checklist (internal use)

- **Python + deps:**
  - Python >= 3.10 installed.
  - Run `pip install -e .` from the repo root.
  - First run will download a Hugging Face NER model (`dslim/bert-base-NER`) and load Torch weights; do this **before** the live demo to avoid waiting.
- **CLI invocation:**
  - On Unix/macOS, you can use the `stupiphi` entrypoint directly (e.g. `stupiphi sanitize`).
  - On Windows, if `stupiphi` is not on `PATH`, use `python -m stupiphi.cli ...` instead:
    - `python -m stupiphi.cli sanitize --seed 42`
    - `python -m stupiphi.cli run-eval --count 20 --difficulty hard`
- **Config:**
  - For most demos you can rely on defaults; optionally copy `src/stupiphi/config/example.yaml` to `config.yaml` and tweak thresholds or detector toggles.
- **Postgres / transfer-case (optional):**
  - The `transfer-case` command requires Postgres env vars:
    - `PROD_DB_USER`, `PROD_DB_DBNAME` (and optionally `PROD_DB_HOST`, `PROD_DB_PORT`, `PROD_DB_PASSWORD` or a single `PROD_DB_DSN`).
    - `DEV_DB_USER`, `DEV_DB_DBNAME` (and optionally `DEV_DB_HOST`, `DEV_DB_PORT`, `DEV_DB_PASSWORD` or `DEV_DB_DSN`).
  - If these are missing, the CLI will fail fast with:
    - `RuntimeError: PROD_DB_USER and PROD_DB_DBNAME must be set (or PROD_DB_DSN) for Postgres connection`
  - For a safe demo without a DB, prefer running only `sanitize` and `run-eval`, and describe `transfer-case` verbally.

**Using the API in code:**

```python
from stupiphi import SanitizationPipeline, PipelineConfig, verify_basic

cfg = PipelineConfig(hf_min_confidence=0.40, faker_seed=99)
pipeline = SanitizationPipeline(cfg)
result = pipeline.sanitize_record(record)
# result.record, result.audit_event, result.verification_ok, result.verification_issues

# Or load from YAML:
pipeline = SanitizationPipeline.from_yaml("config.yaml")
```

---

## Public API summary

| Import from `stupiphi` | Purpose |
|------------------------|--------|
| `SanitizationPipeline`, `PipelineConfig`, `SanitizeResult` | Run detection → plan → apply; get sanitized record plus audit and verification. |
| `PipelineConfig`, `SanitizationPipeline.from_yaml(path)` | Configure via code or YAML (see [Configuration reference](#configuration-reference)). |
| `verify_basic(record)` | Post-sanitization check: returns `(ok, issues)` for residual email/phone patterns in free text. |
| `build_audit_event`, `AuditEvent`, `to_dict` | Build and serialize audit events (no raw PHI). |
| `CanonicalRecord`, `PatientInfo`, `Metadata` | Canonical record model. |
| `Finding`, `EntityType` | Detection result type. |
| `EvalResult`, `evaluate_sanitization` | Evaluation harness: compare labeled vs sanitized, get FN rate and residual counts. |

For more detail on data flow and architecture, see [DATA_FLOW.txt](DATA_FLOW.txt) and [SYSTEM_OVERVIEW.txt](SYSTEM_OVERVIEW.txt).

---

## Evaluation

The evaluation harness uses **synthetic records with injected PHI-like tokens** as ground truth. It measures:

- **False negative rate:** Injected tokens that still appear verbatim after sanitization. Lower is better; the pipeline is tuned to prefer false positives over false negatives.
- **Residual pattern counts:** Number of records where email or phone patterns still appear in `encounter_notes` after sanitization. These are safety signals, not a compliance guarantee.

Run with `--difficulty easy` (single trailing snippet) or `--difficulty hard` (mid-text injection, repeated identifiers, format variants). Current labels are injection-based; **precision** (e.g. “redacted span did not overlap any label”) would require span-level ground truth and is not computed here.

---

## Configuration reference

Pipeline behavior is controlled by `PipelineConfig` or a YAML file (e.g. `config/example.yaml`). Key options:

| Key | Type | Default | Description |
|-----|------|---------|--------------|
| `detectors.hf.enabled` | bool | `true` | Use Hugging Face NER on `encounter_notes`. |
| `detectors.hf.min_confidence` | float | `0.40` | Minimum entity confidence for HF detector. |
| `detectors.rule.enabled` | bool | `true` | Use rule-based detector (email, phone in notes). |
| `detectors.structured.enabled` | bool | `true` | Report structured patient fields (DOB, address, phone, email, name) as findings for audit. |
| `faker_seed` | int | `99` | Seed for Faker-based pseudonymization (deterministic per run when `pseudonym_salt` is not set). |
| `pseudonym_salt` | str \| null | `null` | If set, same original value maps to the same pseudonym across records (cross-record consistency). |

Example YAML (see `config/example.yaml`):

```yaml
detectors:
  hf:
    enabled: true
    min_confidence: 0.40
  rule:
    enabled: true
  structured:
    enabled: true
faker_seed: 99
# pseudonym_salt: "my-secret-salt"   # optional: stable cross-record mapping
```

### Security & deployment

StupiPHI is a **library and CLI**, not an access-control system. Run it in a locked-down environment with least-privilege access:

- **Database access**:
  - Use a dedicated DB role for StupiPHI with **read-only access to prod** and write access only to the specific dev tables used by `transfer-case`.
  - Configure `database_policy` so sensitive columns (e.g. `password_hash`, `ssn`, `token`) are **never preserved**; the loader automatically downgrades `preserve` on dangerous column names to `redact`.
- **Prod → dev transfer guardrail**:
  - The `transfer-case` job refuses to run unless `STUPIPHI_ALLOW_PROD_TO_DEV` is set in the environment to `true` / `1` / `yes`. This is a coarse-grained safety switch to avoid accidental prod-to-dev copies.
- **Audit data handling**:
  - The core pipeline does **not** store audit data; it only calls a user-provided `audit_sink` with a JSON-serializable payload (no raw PHI).
  - If you want file-based audit, use `file_audit_sink(path)` from `stupiphi.audit.audit_log` in your code or CLI wiring. Do not send audit payloads to external services unless they are approved for PHI/PII metadata.

### Edge cases: usernames and passwords

When copying records from prod to dev (e.g. case transfer), auth-related columns need special handling:

- **Usernames** are PII. In `database_policy`, set **`pseudonymize`** or **`redact`** for username columns so dev data does not contain real credentials. Never use `preserve` for prod usernames.
- **Passwords / hashed columns** (e.g. `password_hash`) must **never** be copied. Do not use `preserve` or `pseudonymize` for these columns. Use either:
  - **`redact`**: the column becomes `[REDACTED]`; dev must treat these as “password reset required” or use a separate dev-auth path.
  - **`placeholder`**: replace the value with a single configured dev-only string (e.g. a precomputed bcrypt hash of a known dev password). Configure the value under `database_policy.placeholders` with key `table.column` (e.g. `users.password_hash`). If no placeholder is configured for that column, the tool falls back to redacting. The placeholder value is for dev only; do not use prod hashes, and do not deploy placeholder config to prod.

---

## Legacy CLI and config

The **Legacy** CLI and config under `Legacy/` (e.g. `Legacy/stupify_phi/config.py`, `Legacy/cli.py`) are **deprecated**. The active pipeline lives in the `sanitizer` package and is configured via the YAML schema above (and `config/load.py`). Use `stupiphi run-eval` and `stupiphi sanitize` (or the programmatic API) for new use.

---

## Project overview

Healthcare teams often cannot use real production data in development due to privacy regulations. StupiPHI helps by detecting PHI/PII (ML + rules + structured fields), applying conservative redaction and pseudonymization, and preserving structure for realistic dev/test. The system is modular (ingestion → detection → plan → apply), with audit and verification on every sanitized record. Safety is first-class: we minimize false negatives and never persist raw PHI in audit logs.

For architecture and data flow, see [DATA_FLOW.txt](DATA_FLOW.txt) and [SYSTEM_OVERVIEW.txt](SYSTEM_OVERVIEW.txt).

---

## Running tests

From the project root (with dependencies installed, including optional `transformers` for full integration tests):

```bash
python -m pytest tests/ -v
```

Unit tests (plan, apply, verify, audit) run without `transformers`. Integration and config tests are skipped if `transformers` is not installed.
