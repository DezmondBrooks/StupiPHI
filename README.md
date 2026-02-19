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
