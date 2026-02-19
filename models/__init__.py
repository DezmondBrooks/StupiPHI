"""Canonical data model and HF runner."""
from models.canonical_record import CanonicalRecord, PatientInfo, Metadata

# HFTokenClassifier, HFEntity: use "from models.hf_runner import ..." to avoid pulling in transformers
# when only canonical_record is needed (e.g. in tests).

__all__ = ["CanonicalRecord", "PatientInfo", "Metadata"]
