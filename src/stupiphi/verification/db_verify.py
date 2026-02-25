"""
DB-level verification: scan dev DB text columns for residual email/phone patterns.

Uses COUNT(*) queries only; never fetches or logs row values. Safe issue strings
contain only table name, column name, count, and pattern name.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from stupiphi.connectors.postgres import PostgresClient

# Default tables to scan (transfer-case schema)
DEFAULT_TABLES = ["patients", "cases", "therapists", "payments", "appointments"]

# PostgreSQL-compatible regex patterns (case-insensitive via ~*). No Python \b.
# Email: local@domain.tld
PG_EMAIL_PATTERN = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
# Phone: 3-3-4 with optional separators and ext
PG_PHONE_PATTERN = r"[0-9]{3}[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}(?:\s*(?:x|ext\.?|extension)\s*[0-9]+)?"

# V1 default: (pattern_name, pattern_string)
DEFAULT_PATTERNS = [
    ("email-like", PG_EMAIL_PATTERN),
    ("phone-like", PG_PHONE_PATTERN),
]


@dataclass
class DBVerifyResult:
    ok: bool
    findings_count: int
    findings_by_table: Dict[str, int] = field(default_factory=dict)
    findings_by_column: Dict[str, int] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)


_INFO_SCHEMA_COLUMNS_QUERY = """
    SELECT table_name, column_name
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = ANY(%s)
      AND data_type IN ('text', 'character varying', 'character')
    ORDER BY table_name, ordinal_position
"""


def _get_text_columns(dev_client: PostgresClient, tables: List[str]) -> List[Tuple[str, str]]:
    """Return (table_name, column_name) for text-like columns in the given tables."""
    if not tables:
        return []
    rows = dev_client.fetch_all(_INFO_SCHEMA_COLUMNS_QUERY, (tables,))
    return [(r["table_name"], r["column_name"]) for r in rows if r]


def _count_matches(
    dev_client: PostgresClient,
    table_name: str,
    column_name: str,
    pattern: str,
) -> int:
    """Return COUNT(*) of rows where column ~* pattern. Uses composed SQL for identifiers."""
    from psycopg import sql

    q = sql.SQL("SELECT COUNT(*) AS c FROM {tbl} WHERE {col} IS NOT NULL AND {col} ~* %s").format(
        tbl=sql.Identifier(table_name),
        col=sql.Identifier(column_name),
    )
    with dev_client.conn.cursor() as cur:
        cur.execute(q, (pattern,))
        row = cur.fetchone()
    if row is None:
        return 0
    return int(row["c"]) if hasattr(row, "get") else int(row[0])


def verify_dev_db(
    dev_client: PostgresClient,
    tables: Optional[List[str]] = None,
    policy: Optional[Dict[str, Any]] = None,
    patterns: Optional[Dict[str, Any]] = None,
) -> DBVerifyResult:
    """
    Scan dev DB text columns for email/phone-like patterns. Returns counts only; no row values.

    tables: If None, use DEFAULT_TABLES.
    policy: Reserved (V1: ignored).
    patterns: Reserved (V1: use DEFAULT_PATTERNS).
    """
    table_list = tables if tables is not None else list(DEFAULT_TABLES)
    pattern_list: List[Tuple[str, str]] = (
        DEFAULT_PATTERNS if patterns is None else [(k, v) for k, v in (patterns or {}).items() if isinstance(v, str)]
    )

    columns = _get_text_columns(dev_client, table_list)
    findings_by_table: Dict[str, int] = defaultdict(int)
    findings_by_column: Dict[str, int] = defaultdict(int)
    issues: List[str] = []

    for table_name, column_name in columns:
        col_key = f"{table_name}.{column_name}"
        for pattern_name, pattern_str in pattern_list:
            if isinstance(pattern_str, (list, tuple)):
                pattern_str = pattern_str[0] if pattern_str else ""
            count = _count_matches(dev_client, table_name, column_name, pattern_str)
            if count > 0:
                findings_by_table[table_name] += count
                findings_by_column[col_key] = findings_by_column[col_key] + count
                issues.append(
                    f"{table_name}.{column_name}: {count} row(s) match {pattern_name} pattern"
                )

    total = sum(findings_by_column.values())
    return DBVerifyResult(
        ok=(total == 0),
        findings_count=total,
        findings_by_table=dict(findings_by_table),
        findings_by_column=dict(findings_by_column),
        issues=issues,
    )
