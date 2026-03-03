"""Tests for YAML config loading and pipeline from_yaml."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

pytest.importorskip("transformers", reason="pipeline imports HF detector which needs transformers")
pytest.importorskip("yaml", reason="PyYAML needed for config")

from stupiphi.config.load import load_config
from stupiphi.sanitizer.pipeline import SanitizationPipeline, PipelineConfig


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
        assert cfg.enable_structured is True
        assert cfg.pseudonym_salt is None
        assert cfg.database_policy is None
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


def test_load_config_enable_structured_and_pseudonym_salt() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(
            "detectors:\n  structured:\n    enabled: false\n"
            "faker_seed: 1\npseudonym_salt: my-secret-salt\n"
        )
        path = f.name
    try:
        cfg = load_config(path)
        assert cfg.enable_structured is False
        assert cfg.pseudonym_salt == "my-secret-salt"
    finally:
        Path(path).unlink(missing_ok=True)


def test_load_config_database_policy() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(
            "faker_seed: 1\n"
            "database_policy:\n"
            "  tables:\n"
            "    therapists:\n"
            "      columns:\n"
            "        first_name: pseudonymize\n"
            "        email: redact\n"
            "    payments:\n"
            "      columns:\n"
            "        last4: preserve\n"
            "    users:\n"
            "      columns:\n"
            "        password_hash: preserve\n"
            "        ssn: preserve\n"
        )
        path = f.name
    try:
        cfg = load_config(path)
        assert cfg.database_policy is not None
        assert cfg.database_policy["therapists"]["first_name"] == "pseudonymize"
        assert cfg.database_policy["therapists"]["email"] == "redact"
        # Non-sensitive column name can still be preserved.
        assert cfg.database_policy["payments"]["last4"] == "preserve"
        assert getattr(cfg, "database_policy_placeholders", None) is None
    finally:
        Path(path).unlink(missing_ok=True)


def test_load_config_database_policy_placeholders() -> None:
    """database_policy.placeholders is parsed into database_policy_placeholders (table.column -> value)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(
            "faker_seed: 1\n"
            "database_policy:\n"
            "  placeholders:\n"
            "    users.password_hash: \"$2b$12$devhash\"\n"
            "  tables:\n"
            "    users:\n"
            "      columns:\n"
            "        username: pseudonymize\n"
            "        password_hash: placeholder\n"
        )
        path = f.name
    try:
        cfg = load_config(path)
        assert getattr(cfg, "database_policy_placeholders", None) is not None
        assert cfg.database_policy_placeholders["users.password_hash"] == "$2b$12$devhash"
        # Placeholder action remains, but dangerous column can never be preserved.
        assert cfg.database_policy["users"]["password_hash"] == "placeholder"
        assert cfg.database_policy["users"]["username"] == "pseudonymize"
    finally:
        Path(path).unlink(missing_ok=True)


def test_pipeline_from_yaml() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("detectors:\n  hf:\n    enabled: true\n    min_confidence: 0.35\n  rule:\n    enabled: true\n  structured:\n    enabled: true\nfaker_seed: 100\n")
        path = f.name
    try:
        pipeline = SanitizationPipeline.from_yaml(path)
        assert pipeline.cfg.faker_seed == 100
        assert pipeline.cfg.hf_min_confidence == 0.35
        assert pipeline.hf is not None
        assert pipeline.rules is not None
        assert pipeline.structured is not None
    finally:
        Path(path).unlink(missing_ok=True)
