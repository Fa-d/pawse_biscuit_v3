"""A stand-in for the Worker's D1 proxy (cloudflare/src/index.js), so the D1 code path runs locally.

Speaks the same protocol: POST /query {sql, params} -> {results, changes, last_row_id};  POST /exec {sql} -> {ok}.
Errors come back as HTTP 500 with {"error": message}, as the Worker sends them.

    python -m app.tests.fake_d1            # runs the whole app test suite through it
"""
from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def serve(path):
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            try:
                with lock:
                    if self.path == "/exec":
                        conn.executescript(body["sql"])
                        out = {"ok": True}
                    else:
                        cur = conn.execute(body["sql"], body.get("params") or [])
                        cols = [d[0] for d in cur.description] if cur.description else []
                        rows = [dict(zip(cols, r)) for r in cur.fetchall()] if cols else []
                        out = {"results": rows, "changes": max(cur.rowcount, 0), "last_row_id": cur.lastrowid}
                    conn.commit()
                code = 200
            except sqlite3.Error as e:
                out, code = {"error": str(e)}, 500
            data = json.dumps(out).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


if __name__ == "__main__":
    srv = serve(os.path.join(tempfile.mkdtemp(), "d1.db"))
    os.environ["STUDIO_D1"] = f"proxy:http://127.0.0.1:{srv.server_port}"
    unittest.main(module="app.tests.test_app", argv=["fake_d1", "-q"])
