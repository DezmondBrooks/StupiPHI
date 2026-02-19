"""
Load pipeline configuration from YAML.
Schema: detectors (hf.enabled, hf.min_confidence, rule.enabled), faker_seed.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

from sanitizer.pipeline import PipelineConfig


def load_config(path: str | Path) -> PipelineConfig:
    """Load PipelineConfig from a YAML file. Missing keys use PipelineConfig defaults."""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return _dict_to_config(data)


def _dict_to_config(data: Dict[str, Any]) -> PipelineConfig:
    detectors = data.get("detectors") or {}
    hf = detectors.get("hf") or {}
    rule = detectors.get("rule") or {}

    structured = data.get("detectors", {}).get("structured") or {}
    return PipelineConfig(
        hf_min_confidence=float(hf.get("min_confidence", 0.40)),
        faker_seed=int(data.get("faker_seed", 99)),
        enable_hf=bool(hf.get("enabled", True)),
        enable_rule=bool(rule.get("enabled", True)),
        enable_structured=bool(structured.get("enabled", True)),
        pseudonym_salt=data.get("pseudonym_salt"),
    )
