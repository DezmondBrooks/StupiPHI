"""Canonical data model and HF runner."""
from stupiphi.models.canonical_record import CanonicalRecord, PatientInfo, Metadata

# HFTokenClassifier, HFEntity: use \"from stupiphi.models.hf_runner import ...\" to avoid pulling in transformers
# when only canonical_record is needed (e.g. in tests).

__all__ = ["CanonicalRecord", "PatientInfo", "Metadata"]
