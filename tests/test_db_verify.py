"""Unit tests for DB verification (verify_dev_db)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest

pytest.importorskip("psycopg", reason="psycopg required to import db_verify")

from stupiphi.verification.db_verify import (
    DBVerifyResult,
    verify_dev_db,
)


class FakeCursor:
    """Cursor that returns canned COUNT(*) values in order (shared list, consumed by pop(0))."""

    def __init__(self, count_returns: List[int]) -> None:
        self._count_returns = count_returns  # do not copy; share so multiple cursors consume in order

    def execute(self, query: Any, params: Any = None) -> None:
        pass

    def fetchone(self) -> Optional[Dict[str, Any]]:
        if not self._count_returns:
            return {"c": 0}
        return {"c": self._count_returns.pop(0)}

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *args: Any) -> None:
        pass


class FakeConn:
    def __init__(self, count_returns: List[int]) -> None:
        self._count_returns = count_returns

    def cursor(self) -> FakeCursor:
        return FakeCursor(self._count_returns)


class FakeClient:
    """PostgresClient-like object: fetch_all returns fixed columns; conn.cursor() returns canned COUNTs."""

    def __init__(
        self,
        columns: List[tuple[str, str]],
        count_returns: Optional[List[int]] = None,
    ) -> None:
        self._columns = columns
        self._count_returns = count_returns if count_returns is not None else [0] * (len(columns) * 2)

    def fetch_all(self, query: str, params: Any = None) -> List[Dict[str, Any]]:
        return [{"table_name": t, "column_name": c} for t, c in self._columns]

    @property
    def conn(self) -> FakeConn:
        return FakeConn(self._count_returns)


def test_verify_dev_db_ok_when_all_zero() -> None:
    columns = [("patients", "email"), ("patients", "phone")]
    client = FakeClient(columns, count_returns=[0, 0, 0, 0])
    result = verify_dev_db(client, tables=["patients"])
    assert result.ok is True
    assert result.findings_count == 0
    assert result.findings_by_table == {}
    assert result.findings_by_column == {}
    assert result.issues == []


def test_verify_dev_db_fail_when_any_non_zero() -> None:
    columns = [("patients", "email"), ("patients", "phone"), ("therapists", "email")]
    # 2 patterns per column: email-like, phone-like. Return 2 for patients.email, 0 for rest, 1 for therapists.email
    count_returns = [2, 0, 0, 0, 1, 0]
    client = FakeClient(columns, count_returns=count_returns)
    result = verify_dev_db(client, tables=["patients", "therapists"])
    assert result.ok is False
    assert result.findings_count == 3  # 2 + 1
    assert result.findings_by_table.get("patients", 0) == 2
    assert result.findings_by_table.get("therapists", 0) == 1
    assert result.findings_by_column.get("patients.email", 0) == 2
    assert result.findings_by_column.get("therapists.email", 0) == 1
    assert len(result.issues) >= 1
    for issue in result.issues:
        assert "row(s) match" in issue
        assert "pattern" in issue
        # Safe: no @ (email value), no raw phone digits, no "Patient " literal
        assert "@" not in issue or "pattern" in issue.lower()
        assert "Patient " not in issue


def test_verify_dev_db_issues_safe_strings_only() -> None:
    """Issues must be safe: no @, no raw digits like 555, no 'Patient '."""
    columns = [("patients", "email")]
    client = FakeClient(columns, count_returns=[1, 0])
    result = verify_dev_db(client, tables=["patients"])
    assert not result.ok
    for issue in result.issues:
        assert "row(s) match" in issue
        assert "pattern" in issue
        assert "@" not in issue
        assert "555" not in issue
        assert "Patient " not in issue


def test_verify_dev_db_aggregates_by_table_and_column() -> None:
    columns = [("payments", "last4"), ("payments", "method")]
    count_returns = [3, 0, 0, 0]  # payments.last4 email 3, rest 0
    client = FakeClient(columns, count_returns=count_returns)
    result = verify_dev_db(client, tables=["payments"])
    assert result.ok is False
    assert result.findings_by_table == {"payments": 3}
    assert result.findings_by_column.get("payments.last4", 0) == 3
