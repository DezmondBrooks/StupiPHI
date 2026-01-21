from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, Optional
import json


@dataclass(frozen=True)
class PatientInfo:
    """
    Structured patient fields.
    NOTE: In this project, these values should be synthetic (fake), never real PHI.
    """
    first_name: str
    last_name: str
    dob: str  # ISO date string: "YYYY-MM-DD"
    phone: str
    address: str
    email: Optional[str] = None


@dataclass(frozen=True)
class Metadata:
    """
    Non-sensitive metadata used for auditing and debugging.
    """
    source: str                 # e.g. "synthetic", "dev_db", "prod_stream"
    created_at: str             # ISO datetime string
    schema_version: str = "1.0" # allows safe evolution of record shape


@dataclass(frozen=True)
class CanonicalRecord:
    """
    The canonical internal shape that all connectors normalize into.

    This should remain stable even if input formats vary (CSV, JSONL, DB rows).
    """
    record_id: str
    patient: PatientInfo
    encounter_notes: str
    metadata: Metadata

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to a JSON-serializable dictionary.
        """
        return asdict(self)

    def to_json(self) -> str:
        """
        Serialize to a JSON string.
        """
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @staticmethod
    def now_iso() -> str:
        return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
