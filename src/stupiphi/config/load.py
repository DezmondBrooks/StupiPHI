"""
Load pipeline configuration from YAML.
Schema: detectors (hf.enabled, hf.min_confidence, rule.enabled), faker_seed, database_policy.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

import yaml

from stupiphi.sanitizer.pipeline import PipelineConfig, VALID_DB_POLICY_ACTIONS


# Column-name substrings that should never be preserved in database_policy.
_DANGEROUS_DB_COLUMN_SUBSTRINGS = (
    "password",
    "passwd",
    "pwd",
    "password_hash",
    "pass_hash",
    "token",
    "secret",
    "ssn",
    "social_security",
)


def _is_dangerous_db_column(column_name: str) -> bool:
    name = column_name.lower()
    return any(substr in name for substr in _DANGEROUS_DB_COLUMN_SUBSTRINGS)


def load_config(path: str | Path) -> PipelineConfig:
    """Load PipelineConfig from a YAML file. Missing keys use PipelineConfig defaults."""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return _dict_to_config(data)


def _parse_database_policy(data: Dict[str, Any]) -> Tuple[Dict[str, Dict[str, str]] | None, Dict[str, str]]:
    """Parse database_policy.tables and placeholders. Returns (tables_policy, placeholders).

    For safety, certain high-risk columns (e.g. password, token, ssn) are never allowed
    to use the 'preserve' action; if configured as preserve (or mapped to it), they are
    forced to 'redact'.
    """
    db_policy = data.get("database_policy") or {}
    tables = db_policy.get("tables") or {}
    result: Dict[str, Dict[str, str]] | None = None
    if tables and isinstance(tables, dict):
        result = {}
        for table_name, table_cfg in tables.items():
            if not isinstance(table_cfg, dict):
                continue
            cols = table_cfg.get("columns") or {}
            if not isinstance(cols, dict):
                continue
            result[table_name] = {}
            for col, action in cols.items():
                a = str(action).strip().lower() if action is not None else "preserve"
                if a not in VALID_DB_POLICY_ACTIONS:
                    a = "preserve"
                if a == "preserve" and _is_dangerous_db_column(col):
                    a = "redact"
                result[table_name][col] = a
        if not result:
            result = None

    placeholders_raw = db_policy.get("placeholders") or {}
    placeholders: Dict[str, str] = {}
    if isinstance(placeholders_raw, dict):
        for k, v in placeholders_raw.items():
            if isinstance(k, str) and v is not None:
                placeholders[k.strip()] = str(v)
    return result, placeholders


def _dict_to_config(data: Dict[str, Any]) -> PipelineConfig:
    detectors = data.get("detectors") or {}
    hf = detectors.get("hf") or {}
    rule = detectors.get("rule") or {}

    structured = data.get("detectors", {}).get("structured") or {}
    database_policy, database_policy_placeholders = _parse_database_policy(data)
    return PipelineConfig(
        hf_min_confidence=float(hf.get("min_confidence", 0.40)),
        faker_seed=int(data.get("faker_seed", 99)),
        enable_hf=bool(hf.get("enabled", True)),
        enable_rule=bool(rule.get("enabled", True)),
        enable_structured=bool(structured.get("enabled", True)),
        pseudonym_salt=data.get("pseudonym_salt"),
        database_policy=database_policy,
        database_policy_placeholders=database_policy_placeholders if database_policy_placeholders else None,
    )
