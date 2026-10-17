"""Postgres access (Neon). Retries once on a dropped connection, since Neon's free tier sleeps when idle."""
import os
import psycopg2
import psycopg2.extras
from psycopg2 import pool

_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        _pool = pool.SimpleConnectionPool(
            1, 5, os.environ["DATABASE_URL"],
            options="-c search_path=departures,public",
            connect_timeout=15,
        )
    return _pool


def _run(sql, params, fetch):
    p = _get_pool()
    conn = p.getconn()
    broken = False
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = None
            if fetch == "all":
                rows = [dict(r) for r in cur.fetchall()]
            elif fetch == "one":
                r = cur.fetchone()
                rows = dict(r) if r else None
        conn.commit()
        return rows
    except (psycopg2.OperationalError, psycopg2.InterfaceError):
        broken = True
        raise
    except Exception:
        try:
            conn.rollback()
        except Exception:
            broken = True
        raise
    finally:
        p.putconn(conn, close=broken)


def _with_retry(sql, params, fetch):
    try:
        return _run(sql, params, fetch)
    except (psycopg2.OperationalError, psycopg2.InterfaceError):
        return _run(sql, params, fetch)


def all(sql, params=None):
    return _with_retry(sql, params, "all")


def one(sql, params=None):
    return _with_retry(sql, params, "one")


def run(sql, params=None):
    return _with_retry(sql, params, None)
