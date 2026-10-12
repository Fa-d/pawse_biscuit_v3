"""Cloudflare D1 behind the small part of the sqlite3 API the app uses (execute, fetchone, fetchall, rowcount,
lastrowid, executescript).  D1 is SQLite, so every query in the app runs unchanged.

Two ways to reach it, chosen by STUDIO_D1:
  proxy:http://d1.internal     inside the Cloudflare Container: the Worker intercepts requests to this made-up host
                               and runs them on its D1 binding (see cloudflare/src/index.js)
  rest:<account id>/<db id>    from anywhere else (the admin tool on your laptop): Cloudflare's D1 REST API, with the
                               token in CLOUDFLARE_API_TOKEN

Each statement commits on its own (D1 has no open transactions over HTTP).  The app's multi-step writes are written
so that a statement failing half-way leaves nothing unsafe: one-time grants are guarded by unique keys.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


class D1Error(RuntimeError):
    pass


class Cursor:
    def __init__(self, rows, changes=0, last_row_id=None):
        self._rows = [dict(r) for r in rows]
        self.rowcount = changes
        self.lastrowid = last_row_id

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)

    def __iter__(self):
        return iter(self._rows)


def _post(url, body, headers=None, timeout=20):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:500]
        raise D1Error(f"D1 {e.code}: {detail}") from None


class Connection:
    """One logical connection.  commit() and close() exist so `with db.connect() as c` reads the same as sqlite3."""

    def __init__(self, target: str):
        kind, _, rest = target.partition(":")
        self.kind = kind
        if kind == "proxy":
            self.base = rest.rstrip("/")
        elif kind == "rest":
            account, _, database = rest.partition("/")
            token = os.environ.get("CLOUDFLARE_API_TOKEN", "")
            if not (account and database and token):
                raise D1Error("STUDIO_D1=rest:<account id>/<database id> also needs CLOUDFLARE_API_TOKEN")
            self.base = f"https://api.cloudflare.com/client/v4/accounts/{account}/d1/database/{database}"
            self.headers = {"Authorization": f"Bearer {token}"}
        else:
            raise D1Error(f"STUDIO_D1 must start with proxy: or rest:, not {target!r}")

    def execute(self, sql, params=()):
        params = list(params)
        if self.kind == "proxy":
            r = _post(f"{self.base}/query", {"sql": sql, "params": params})
            if "error" in r:
                raise D1Error(r["error"])
            return Cursor(r.get("results") or [], r.get("changes", 0), r.get("last_row_id"))
        r = _post(f"{self.base}/query", {"sql": sql, "params": params}, self.headers)
        if not r.get("success"):
            raise D1Error(str(r.get("errors")))
        res = r["result"][0]
        meta = res.get("meta") or {}
        return Cursor(res.get("results") or [], meta.get("changes", 0), meta.get("last_row_id"))

    def executescript(self, sql):
        if self.kind == "proxy":
            r = _post(f"{self.base}/exec", {"sql": sql})
            if "error" in r:
                raise D1Error(r["error"])
            return None
        for stmt in [s.strip() for s in sql.split(";") if s.strip()]:     # the REST API takes one statement per call here
            self.execute(stmt)
        return None

    def commit(self):
        pass

    def close(self):
        pass
