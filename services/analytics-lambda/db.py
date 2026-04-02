"""Psycopg2 connection management for analytics_db.

Provides a context-managed connection for use within Lambda invocations.
Connections are not pooled — Lambda concurrency is capped at 10.
"""

import os
from contextlib import contextmanager

import psycopg2
import psycopg2.extras

_db_url = os.environ.get(
    "ANALYTICS_DB_URL", "postgresql://postgres:devpass@localhost:5432/analytics_db"
)


@contextmanager
def get_connection():
    """Yield a psycopg2 connection that auto-commits on success and rolls back on error."""
    conn = psycopg2.connect(_db_url)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def dict_cursor(conn):
    """Return a RealDictCursor for the given connection."""
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
