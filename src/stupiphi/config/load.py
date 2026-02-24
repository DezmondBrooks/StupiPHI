"""
Load pipeline configuration from YAML.
Schema: detectors (hf.enabled, hf.min_confidence, rule.enabled), faker_seed, database_policy.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

from stupiphi.sanitizer.pipeline import PipelineConfig, VALID_DB_POLICY_ACTIONS


def load_config(path: str | Path) -> PipelineConfig:
    """Load PipelineConfig from a YAML file. Missing keys use PipelineConfig defaults."""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return _dict_to_config(data)


def _parse_database_policy(data: Dict[str, Any]) -> Dict[str, Dict[str, str]] | None:
    """Parse database_policy.tables into { table: { column: action } }. Invalid actions -> preserve."""
    db_policy = data.get("database_policy") or {}
    tables = db_policy.get("tables") or {}
    if not tables or not isinstance(tables, dict):
        return None
    result: Dict[str, Dict[str, str]] = {}
    for table_name, table_cfg in tables.items():
        if not isinstance(table_cfg, dict):
            continue
        cols = table_cfg.get("columns") or {}
        if not isinstance(cols, dict):
            continue
        result[table_name] = {}
        for col, action in cols.items():
            a = str(action).strip().lower() if action is not None else "preserve"
            result[table_name][col] = a if a in VALID_DB_POLICY_ACTIONS else "preserve"
    return result if result else None


def _dict_to_config(data: Dict[str, Any]) -> PipelineConfig:
    detectors = data.get("detectors") or {}
    hf = detectors.get("hf") or {}
    rule = detectors.get("rule") or {}

    structured = data.get("detectors", {}).get("structured") or {}
    database_policy = _parse_database_policy(data)
    return PipelineConfig(
        hf_min_confidence=float(hf.get("min_confidence", 0.40)),
        faker_seed=int(data.get("faker_seed", 99)),
        enable_hf=bool(hf.get("enabled", True)),
        enable_rule=bool(rule.get("enabled", True)),
        enable_structured=bool(structured.get("enabled", True)),
        pseudonym_salt=data.get("pseudonym_salt"),
        database_policy=database_policy,
    )
