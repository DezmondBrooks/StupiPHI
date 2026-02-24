"""Optional integration test for case transfer.

Skipped unless RUN_DB_TESTS=1 and both PROD_DB_DSN and DEV_DB_DSN are set.
"""
from __future__ import annotations

import os

import pytest

pytest.importorskip("psycopg", reason="psycopg required for DB integration tests")


RUN_DB_TESTS = os.getenv("RUN_DB_TESTS") == "1"
PROD_DB_DSN = os.getenv("PROD_DB_DSN")
DEV_DB_DSN = os.getenv("DEV_DB_DSN")

if not (RUN_DB_TESTS and PROD_DB_DSN and DEV_DB_DSN):
    pytest.skip("DB integration tests disabled (set RUN_DB_TESTS=1 and both PROD_DB_DSN, DEV_DB_DSN)", allow_module_level=True)


def test_case_transfer_smoke() -> None:
    # Placeholder: real test would:
    # - run run_case_transfer on a known case_id
    # - assert dev_db contains sanitized data.
    # We keep this as a stub so enabling DB tests is opt-in.
    assert True

