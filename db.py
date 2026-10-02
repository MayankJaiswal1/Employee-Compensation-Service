"""Thin SQL Server access layer. The connection string comes from an app setting, never from source."""
import os
from contextlib import contextmanager

import pyodbc


@contextmanager
def connection():
    conn_str = os.environ.get("SQL_CONNECTION_STRING")
    if not conn_str:
        raise RuntimeError("SQL_CONNECTION_STRING app setting is not configured")
    conn = pyodbc.connect(conn_str, timeout=15)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetch_all(sql, params=()):
    """Run a statement that returns rows (SELECT, or INSERT/UPDATE with OUTPUT)."""
    with connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def fetch_one(sql, params=()):
    rows = fetch_all(sql, params)
    return rows[0] if rows else None


def execute(sql, params=()) -> int:
    """Run a statement that returns no rows; returns affected row count."""
    with connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur.rowcount
