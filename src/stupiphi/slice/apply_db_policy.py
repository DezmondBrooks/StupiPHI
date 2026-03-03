"""
Column-level sanitization policy for DB replay.

This policy controls how DB columns are handled when replaying a case slice into
the dev database. It is separate from free-text detection/redaction (CanonicalRecord
and SanitizationPipeline). If database_policy is not defined in config, all columns
are preserved (current behavior). Never log original row values.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from stupiphi.transformation.pseudonymizer import stable_pseudonym

REDACTED = "[REDACTED]"

# Map DB column names to pseudonymizer field_kind. Unknown columns use fallback in stable_pseudonym.
_COLUMN_TO_FIELD_KIND: Dict[str, str] = {
    "first_name": "first_name",
    "last_name": "last_name",
    "email": "email",
    "phone": "phone",
    "address": "address",
}


def _column_to_field_kind(column: str) -> str:
    """Return pseudonymizer field_kind for a column name; unknown columns use 'email' for fallback."""
    return _COLUMN_TO_FIELD_KIND.get(column, "email")


def apply_db_policy_to_row(
    table_name: str,
    row: Dict[str, Any],
    policy_config: Optional[Dict[str, Dict[str, str]]],
    pseudonym_salt: Optional[str],
    placeholders: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Apply database_policy to a single row. Returns a new dict; does not mutate row.

    policy_config: { table_name: { column_name: "preserve"|"redact"|"pseudonymize"|"mask"|"placeholder" } }.
    If None or table/column not defined, action is preserve.
    placeholders: For action "placeholder", { "table.column": value }. Row value is never used; if no placeholder, REDACTED.
    """
    table_policy = (policy_config or {}).get(table_name) or {}
    placeholders_map = placeholders or {}
    out: Dict[str, Any] = {}

    for col, value in row.items():
        action = (table_policy.get(col) or "preserve").strip().lower()
        if action == "preserve":
            out[col] = value
        elif action == "redact":
            out[col] = REDACTED
        elif action == "placeholder":
            key = f"{table_name}.{col}"
            out[col] = placeholders_map.get(key, REDACTED)
        elif action == "pseudonymize":
            if value is None or (isinstance(value, str) and value.strip() == ""):
                out[col] = REDACTED
            elif pseudonym_salt:
                s = str(value)
                out[col] = stable_pseudonym(
                    pseudonym_salt,
                    f"{table_name}.{col}",
                    s,
                    _column_to_field_kind(col),
                )
            else:
                out[col] = REDACTED
        elif action == "mask":
            s = str(value) if value is not None else ""
            if len(s) >= 4:
                out[col] = "*" * (len(s) - 4) + s[-4:]
            else:
                out[col] = REDACTED
        else:
            out[col] = value

    return out
