"""SQLite storage.  One small file; swap for Postgres when one machine is no longer enough."""
from __future__ import annotations

import os
import sqlite3
import time
from contextlib import contextmanager

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY,
    email         TEXT NOT NULL UNIQUE,
    pw_hash       TEXT NOT NULL,
    plan          TEXT NOT NULL DEFAULT 'free',        -- free | pro
    credits       INTEGER NOT NULL DEFAULT 0,          -- from credit packs: one per clean or animated export
    stripe_customer     TEXT UNIQUE,
    stripe_subscription TEXT,
    created       INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token    TEXT PRIMARY KEY,
    user_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires  INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS stickers (
    id       INTEGER PRIMARY KEY,
    user_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    prompt   TEXT NOT NULL DEFAULT '',
    spec     TEXT NOT NULL,
    created  INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS usage (
    user_id  INTEGER NOT NULL,
    day      TEXT NOT NULL,
    kind     TEXT NOT NULL,                          -- export | llm
    n        INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, day, kind)
);
CREATE TABLE IF NOT EXISTS stripe_events (
    id       TEXT PRIMARY KEY,                       -- Stripe event id: each event is applied once
    type     TEXT NOT NULL,
    received INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS fulfilled (
    session_id TEXT PRIMARY KEY,                     -- Checkout Session id: a credit pack is granted once
    user_id    INTEGER NOT NULL,
    created    INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS reset_tokens (
    token    TEXT PRIMARY KEY,                       -- sha256 of the emailed token
    user_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires  INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS invites (
    code      TEXT PRIMARY KEY,
    max_uses  INTEGER NOT NULL DEFAULT 1,
    uses      INTEGER NOT NULL DEFAULT 0,
    note      TEXT NOT NULL DEFAULT '',
    created   INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS waitlist (
    email    TEXT PRIMARY KEY,
    source   TEXT NOT NULL DEFAULT '',
    invite   TEXT,                                   -- code sent to them, once invited
    created  INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS feedback (
    id       INTEGER PRIMARY KEY,
    user_id  INTEGER,
    kind     TEXT NOT NULL,                          -- wrong | idea | bug
    prompt   TEXT NOT NULL DEFAULT '',
    spec     TEXT NOT NULL DEFAULT '',
    note     TEXT NOT NULL DEFAULT '',
    created  INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    day   TEXT NOT NULL,                             -- daily counts only: no user ids, no prompts
    kind  TEXT NOT NULL,
    n     INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (day, kind)
);
CREATE TABLE IF NOT EXISTS misses (
    id       INTEGER PRIMARY KEY,
    prompt   TEXT NOT NULL,
    unknown  TEXT NOT NULL DEFAULT '[]',              -- words the rules didn't know, as JSON
    created  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS stickers_user ON stickers(user_id, created);
"""

# columns added after a database was first created: (table, column, definition)
MIGRATIONS = [
    ("users", "invite", "TEXT"),
]

_path = None
_d1 = None          # "proxy:http://d1.internal" or "rest:<account>/<database>" (see d1.py); None = local SQLite file


def init(path, d1=None):
    global _path, _d1
    _path, _d1 = path, d1 or os.environ.get("STUDIO_D1") or None
    if not _d1 and path != ":memory:":
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with connect() as c:
        c.executescript(SCHEMA)
        for table, col, decl in MIGRATIONS:
            have = {r["name"] for r in c.execute(f"PRAGMA table_info({table})")}
            if col not in have:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")


@contextmanager
def connect():
    if _d1:
        from .d1 import Connection
        yield Connection(_d1)
        return
    c = sqlite3.connect(_path, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    try:
        yield c
        c.commit()
    finally:
        c.close()


def now():
    return int(time.time())


def today():
    return time.strftime("%Y-%m-%d", time.gmtime())


def usage_today(c, user_id, kind):
    r = c.execute("SELECT n FROM usage WHERE user_id=? AND day=? AND kind=?", (user_id, today(), kind)).fetchone()
    return r["n"] if r else 0


def add_usage(c, user_id, kind, n=1):
    c.execute("INSERT INTO usage (user_id, day, kind, n) VALUES (?, ?, ?, ?) "
              "ON CONFLICT(user_id, day, kind) DO UPDATE SET n = n + excluded.n", (user_id, today(), kind, n))


def bump(kind, n=1):
    """Count something that happened today (signups, downloads by format, packs...)."""
    with connect() as c:
        c.execute("INSERT INTO events (day, kind, n) VALUES (?, ?, ?) "
                  "ON CONFLICT(day, kind) DO UPDATE SET n = n + excluded.n", (today(), kind, n))
