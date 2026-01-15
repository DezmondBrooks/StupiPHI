# 🧼 Stupify-PHI

**Stupify-PHI** is an AI-powered Python tool that detects and anonymizes personally identifiable information (PII) and protected health information (PHI) from structured and semi-structured data. It’s designed to let developers safely copy production datasets into dev environments while remaining HIPAA-compliant.

> ⚠️ This is an early-stage project and a work in progress. Contributions welcome!

---

## 🚀 Why Stupify-PHI?

Many teams struggle to work with real production data in dev or staging environments due to privacy concerns and regulatory risk (HIPAA, GDPR, etc.). Stupify-PHI helps solve this by removing or replacing sensitive information—without sacrificing the realism needed to find bugs or catch design drift.

---

## ✨ Features

- 🔍 **AI-Powered Free-Text Redaction**  
  Uses GPT or local LLMs to identify and redact PHI/PII in unstructured fields like notes and descriptions.

- 🧠 **Regex + Context Detection**  
  Built-in patterns for common fields like emails, SSNs, and phone numbers.

- 🎭 **Format-Preserving Anonymization**  
  Replace values with fake data using [Faker](https://faker.readthedocs.io/) while keeping realistic formatting.

- 🔧 **Configurable Rules (YAML)**  
  Customize which fields to scrub or redact per use case.

- 🧩 **Pluggable Architecture**  
  CSV support to start, with plans for PostgreSQL, MySQL, and JSON.

- 🪵 **Audit Logging (optional)**  
  View logs of what data was transformed and how.

---

## 📦 Installation

```bash
git clone https://github.com/yourusername/stupify-phi.git
cd stupify-phi
python -m venv .venv
. .venv/Scripts/activate   # or source .venv/bin/activate (Mac/Linux)
pip install -r requirements.txt
