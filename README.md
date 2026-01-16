# StupiPHI

StupiPHI is an AI-assisted data sanitization system designed to safely transform sensitive healthcare records into development-ready datasets without exposing PHI/PII.

---

## Project Overview
This project explores how AI agents can sanitize sensitive healthcare data to enable realistic development and debugging workflows while respecting privacy and security constraints.

The system is designed as a production-style pipeline with explicit safety, auditability, and evaluation guarantees.

---

## Why This Exists
Healthcare teams often cannot use real production data in development environments due to privacy regulations, leading to reduced test coverage and difficult debugging.

StupiPHI aims to bridge this gap by depersonalizing sensitive fields while preserving structural and behavioral fidelity.

---

## System Architecture
The system is structured as a modular pipeline consisting of ingestion, detection, policy reasoning, transformation, and auditing stages.

It is designed to support streaming, in-memory processing and multiple deployment modes (production-secure vs development/testing).

---

## Safety & Guardrails
Safety is treated as a first-class concern, with explicit handling for uncertainty, confidence thresholds, and conservative fallback behavior.

The system prioritizes minimizing false negatives and supports escalation when confidence is insufficient.

---

## Evaluation Strategy
StupiPHI includes an evaluation harne
