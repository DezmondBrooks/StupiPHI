# StupiPHI — System Design (Minimum Viable Design)

## 1. Problem Statement
Describe what the system is and why it exists.

Example:
StupiPHI is an AI-assisted data sanitization system designed to safely transform sensitive healthcare records into development-ready datasets without exposing PHI/PII. It enables realistic debugging and testing workflows while respecting privacy and security constraints.

---

## 2. Non-Goals
Explicitly state what this system does NOT attempt to do.

- This system does not modify production databases directly.
- This system does not claim regulatory compliance (e.g., HIPAA certification).
- This system does not attempt to perfectly preserve statistical distributions.
- This system is not a real-time production inference service.

---

## 3. Users and Use Cases
Who uses this system and for what purpose?

- Backend engineers debugging production issues in dev/staging
- Data engineers generating safe test datasets
- Platform teams validating PHI-handling workflows

Primary use case:
- Transform sensitive production-like records into safe, sanitized equivalents for non-production environments.

---

## 4. Inputs and Outputs

### Inputs
- Production mode: streamed records from a secure source database connector
- Dev/Test mode: synthetic JSONL or local database with fake data

### Outputs
- Sanitized records (JSONL and/or dev database)
- Audit logs describing transformations and risk decisions
- Optional evaluation artifacts (metrics, summaries)

---

## 5. Trust Boundary and Threat Model
Where sensitive data exists and how risk is controlled.

- Raw PHI exists only in memory during processing.
- Raw input records are never persisted to disk in production mode.
- Sanitized output must not contain identifiable PHI/PII.
- When detection confidence is low, conservative redaction or escalation is required.

Dangerous outcome:
- PHI remains in sanitized output.

---

## 6. Core System Components
High-level components (implementation details deferred).

- Ingestion (source connectors)
- Detection (Hugging Face models, LLMs)
- Policy Store (retrieval-augmented rules)
- Planning / Decision Layer (agent logic)
- Transformation Engine (redact, mask, fake)
- Audit Logger
- Evaluation Harness

---

## 7. Agent Control Loop
Describe the agent’s reasoning loop at a high level.

1. Observe: load record and metadata
2. Detect: identify PHI/PII entities
3. Retrieve: fetch relevant policies and rules
4. Plan: decide transformation strategy
5. Act: apply transformations
6. Verify: check for remaining PHI
7. Escalate: flag record if uncertainty remains
8. Output: write sanitized record and audit log

---

## 8. Data Flow
See `DATA_FLOW.txt` for detailed flows.

- Production mode: secure DB → in-memory sanitize → dev DB
- Dev/Test mode: synthetic input → local sanitize → local output

---

## 9. MVP Scope
What will be built first.

- Synthetic data generator
- Hugging Face-based PHI detector
- Conservative transformation engine
- Audit log generation
- Basic evaluation (focus on false negatives)

Deferred:
- LLM-based detection
- Policy RAG
- Long-term memory
- Multi-agent orchestration

---

## 10. Open Questions
Unknowns to resolve during development.

- How strict should confidence thresholds be?
- What is the best balance between redaction and faking?
- How should human review be represented?
- How should multi-record relationships be handled?

