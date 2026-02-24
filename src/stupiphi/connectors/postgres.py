"""Postgres connector utilities for StupiPHI.

V1 is intentionally small and focused:
- thin PostgresClient wrapper around psycopg3
- DSN helpers that read PROD_DB_* and DEV_DB_* environment variables

IMPORTANT: This module must never log raw PHI-like values. It may log
only table names, counts, and numeric IDs.
"""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

import psycopg
from psycopg.rows import dict_row


logger = logging.getLogger(__name__)

Params = Union[Sequence[Any], Mapping[str, Any], None]


@dataclass
class PostgresClient:
    """Small psycopg3 wrapper.

    This wrapper is intentionally minimal: it is not an ORM. It is used
    by slice-extraction and replay code paths and is safe to use inside
    context managers.
    """

    dsn: str
    _conn: Optional[psycopg.Connection] = None

    def connect(self) -> None:
        if self._conn is None or self._conn.closed:
            self._conn = psycopg.connect(self.dsn, row_factory=dict_row)

    @property
    def conn(self) -> psycopg.Connection:
        if self._conn is None or self._conn.closed:
            self.connect()
        assert self._conn is not None  # for type checkers
        return self._conn

    def close(self) -> None:
        if self._conn is not None and not self._conn.closed:
            self._conn.close()

    def fetch_one(self, query: str, params: Params = None) -> Optional[Dict[str, Any]]:
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            return dict(row) if row is not None else None

    def fetch_all(self, query: str, params: Params = None) -> List[Dict[str, Any]]:
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    def execute(self, query: str, params: Params = None) -> None:
        with self.conn.cursor() as cur:
            cur.execute(query, params)

    def executemany(self, query: str, params_list: Iterable[Params]) -> None:
        with self.conn.cursor() as cur:
            for params in params_list:
                cur.execute(query, params)

    @contextmanager
    def transaction(self):
        """Run a group of operations in a single transaction.

        Usage:
            with client.transaction():
                client.execute(...)
                client.execute(...)
        """
        conn = self.conn
        try:
            with conn.transaction():
                yield self
        except Exception:
            # psycopg will roll back on context manager exit for transaction(),
            # but we log the fact that an error occurred (without PHI).
            logger.exception("Postgres transaction failed")  # no PHI; message only
            raise


def _build_dsn_from_components(prefix: str) -> str:
    host = os.getenv(f"{prefix}_HOST", "localhost")
    port = os.getenv(f"{prefix}_PORT", "5432")
    user = os.getenv(f"{prefix}_USER")
    password = os.getenv(f"{prefix}_PASSWORD")
    dbname = os.getenv(f"{prefix}_DBNAME")

    if not user or not dbname:
        raise RuntimeError(
            f"{prefix}_USER and {prefix}_DBNAME must be set (or {prefix}_DSN) for Postgres connection"
        )

    # We avoid logging actual connection details beyond which prefix is used.
    return f"postgresql://{user}:{password or ''}@{host}:{port}/{dbname}"


def build_dsn_from_env(prefix: str) -> str:
    """Build a Postgres DSN from environment variables.

    Precedence:
    - {prefix}_DSN (e.g. PROD_DB_DSN, DEV_DB_DSN)
    - components: {prefix}_HOST, {prefix}_PORT, {prefix}_USER, {prefix}_PASSWORD, {prefix}_DBNAME
    """
    dsn = os.getenv(f"{prefix}_DSN")
    if dsn:
        return dsn
    return _build_dsn_from_components(prefix)


def get_prod_client() -> PostgresClient:
    """Create a connected client for the prod DB slice source."""
    dsn = build_dsn_from_env("PROD_DB")
    client = PostgresClient(dsn=dsn)
    client.connect()
    return client


def get_dev_client() -> PostgresClient:
    """Create a connected client for the dev DB slice sink."""
    dsn = build_dsn_from_env("DEV_DB")
    client = PostgresClient(dsn=dsn)
    client.connect()
    return client

