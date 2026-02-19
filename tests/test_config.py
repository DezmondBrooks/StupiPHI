"""Tests for YAML config loading and pipeline from_yaml."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

pytest.importorskip("transformers", reason="pipeline imports HF detector which needs transformers")
pytest.importorskip("yaml", reason="PyYAML needed for config")

from config.load import load_config
from sanitizer.pipeline import SanitizationPipeline, PipelineConfig


def test_load_config_missing_file_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/config.yaml")


def test_load_config_defaults() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("{}")
        path = f.name
    try:
        cfg = load_config(path)
        assert cfg.hf_min_confidence == 0.40
        assert cfg.faker_seed == 99
        assert cfg.enable_hf is True
        assert cfg.enable_rule is True
    finally:
        Path(path).unlink(missing_ok=True)


def test_load_config_custom_values() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("detectors:\n  hf:\n    enabled: false\n    min_confidence: 0.5\n  rule:\n    enabled: true\nfaker_seed: 42\n")
        path = f.name
    try:
        cfg = load_config(path)
        assert cfg.enable_hf is False
        assert cfg.enable_rule is True
        assert cfg.hf_min_confidence == 0.5
        assert cfg.faker_seed == 42
    finally:
        Path(path).unlink(missing_ok=True)


def test_pipeline_from_yaml() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("detectors:\n  hf:\n    enabled: true\n    min_confidence: 0.35\n  rule:\n    enabled: true\nfaker_seed: 100\n")
        path = f.name
    try:
        pipeline = SanitizationPipeline.from_yaml(path)
        assert pipeline.cfg.faker_seed == 100
        assert pipeline.cfg.hf_min_confidence == 0.35
        assert pipeline.hf is not None
        assert pipeline.rules is not None
    finally:
        Path(path).unlink(missing_ok=True)
