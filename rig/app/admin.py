#!/usr/bin/env python3
"""Running the beta from the command line.

    .venv/bin/python -m app.admin invite --uses 20 --note "design friends"     # one code, 20 signups
    .venv/bin/python -m app.admin invites                                      # codes and how many are used
    .venv/bin/python -m app.admin waitlist                                     # who is waiting
    .venv/bin/python -m app.admin invite-waitlist 25                           # email single-use codes to the next 25
    .venv/bin/python -m app.admin plan someone@example.com pro                 # support: change a plan by hand
    .venv/bin/python -m app.admin credits someone@example.com 20               # support: add credits
    .venv/bin/python -m app.admin reset-link someone@example.com               # support: a password reset link
    .venv/bin/python -m app.admin report --days 14                             # the funnel, misses, feedback

Uses the same settings (STUDIO_DB, SMTP_*, STUDIO_BASE_URL, STUDIO_CACHE) as the web app.  For the live site on
Cloudflare, point it at D1:  STUDIO_D1=rest:<account id>/<database id> with CLOUDFLARE_API_TOKEN set.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import secrets
import sys
import time

from . import auth, db, mailer
from .config import settings

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"      # no 0/O, 1/I: codes are read aloud and typed by hand


def new_code():
    return "PAWS-" + "".join(secrets.choice(ALPHABET) for _ in range(6))


def cmd_invite(a):
    with db.connect() as c:
        for _ in range(a.count):
            code = new_code()
            c.execute("INSERT INTO invites (code, max_uses, note, created) VALUES (?, ?, ?, ?)", (code, a.uses, a.note, db.now()))
            print(code)


def cmd_invites(a):
    with db.connect() as c:
        rows = c.execute("SELECT * FROM invites ORDER BY created DESC").fetchall()
    for r in rows:
        print(f"{r['code']}  {r['uses']}/{r['max_uses']} used  {time.strftime('%Y-%m-%d', time.gmtime(r['created']))}  {r['note']}")
    if not rows:
        print("No invite codes yet. Make one with: invite --uses 10")


def cmd_waitlist(a):
    with db.connect() as c:
        rows = c.execute("SELECT * FROM waitlist ORDER BY created").fetchall()
    for r in rows:
        print(f"{r['email']:<40} {time.strftime('%Y-%m-%d', time.gmtime(r['created']))}  {r['source'] or '-':<12} {r['invite'] or ''}")
    waiting = sum(1 for r in rows if not r["invite"])
    print(f"{len(rows)} on the waitlist, {waiting} not invited yet")


def cmd_invite_waitlist(a):
    with db.connect() as c:
        rows = c.execute("SELECT email FROM waitlist WHERE invite IS NULL ORDER BY created LIMIT ?", (a.n,)).fetchall()
        for r in rows:
            code = new_code()
            c.execute("INSERT INTO invites (code, max_uses, note, created) VALUES (?, 1, ?, ?)", (code, f"waitlist {r['email']}", db.now()))
            c.execute("UPDATE waitlist SET invite=? WHERE email=?", (code, r["email"]))
            c.commit()
            where = mailer.invite_email(r["email"], f"{settings.base_url}/studio?invite={code}", code)
            print(f"{r['email']}  {code}  {where}")
    print(f"invited {len(rows)}")


def _user(c, email):
    u = c.execute("SELECT * FROM users WHERE email=?", (email.strip().lower(),)).fetchone()
    if u is None:
        sys.exit(f"No account for {email}")
    return u


def cmd_plan(a):
    with db.connect() as c:
        u = _user(c, a.email)
        c.execute("UPDATE users SET plan=? WHERE id=?", (a.plan, u["id"]))
    print(f"{a.email}: plan {a.plan}")


def cmd_credits(a):
    with db.connect() as c:
        u = _user(c, a.email)
        c.execute("UPDATE users SET credits = MAX(0, credits + ?) WHERE id=?", (a.n, u["id"]))
        print(f"{a.email}: {c.execute('SELECT credits FROM users WHERE id=?', (u['id'],)).fetchone()['credits']} credits")


def cmd_reset_link(a):
    with db.connect() as c:
        u = _user(c, a.email)
        token = secrets.token_urlsafe(32)
        c.execute("INSERT INTO reset_tokens (token, user_id, expires) VALUES (?, ?, ?)", (auth.digest(token), u["id"], db.now() + 3600))
    print(f"{settings.base_url}/studio?reset={token}   (valid for one hour)")


def cmd_report(a):
    since = time.strftime("%Y-%m-%d", time.gmtime(time.time() - a.days * 86400))
    with db.connect() as c:
        ev = collections.Counter({r["kind"]: r["n"] for r in c.execute(
            "SELECT kind, SUM(n) AS n FROM events WHERE day >= ? GROUP BY kind", (since,))})
        users = c.execute("SELECT COUNT(*) n, SUM(plan='pro') pro, SUM(credits > 0) with_credits FROM users").fetchone()
        packs_sold = c.execute("SELECT COUNT(*) n FROM fulfilled").fetchone()["n"]
        wl = c.execute("SELECT COUNT(*) n, SUM(invite IS NOT NULL) invited FROM waitlist").fetchone()
        fb = c.execute("SELECT kind, prompt, note, created FROM feedback ORDER BY created DESC LIMIT 15").fetchall()
    exports = {k.split(":", 1)[1]: v for k, v in ev.items() if k.startswith("export:")}
    print(f"Last {a.days} days (since {since})")
    print(f"  waitlist joins   {ev['waitlist']:>6}    (all time: {wl['n'] or 0}, invited {wl['invited'] or 0})")
    print(f"  signups          {ev['signup']:>6}")
    print(f"  prompts          {ev['prompt'] + ev['prompt:unsure']:>6}    ({ev['prompt:unsure']} not understood)")
    print(f"  saved stickers   {ev['save']:>6}")
    print(f"  downloads        {sum(exports.values()):>6}    " + ", ".join(f"{k} {v}" for k, v in sorted(exports.items(), key=lambda x: -x[1])))
    print(f"  packs            {ev['pack:telegram'] + ev['pack:whatsapp']:>6}    (telegram {ev['pack:telegram']}, whatsapp {ev['pack:whatsapp']})")
    print(f"  checkouts begun  {ev['checkout:pro'] + ev['checkout:pack']:>6}    (pro {ev['checkout:pro']}, credit pack {ev['checkout:pack']})")
    print(f"Now: {users['n']} accounts, {users['pro'] or 0} on Pro, {users['with_credits'] or 0} holding credits, {packs_sold} credit packs sold")

    words = collections.Counter()
    with db.connect() as c:                                         # the web app records misses in the database
        for r in c.execute("SELECT unknown FROM misses WHERE created >= ?", (int(time.time()) - a.days * 86400,)):
            try:
                words.update(json.loads(r["unknown"]))
            except ValueError:
                pass
    misses = os.path.join(os.environ.get("STUDIO_CACHE", os.path.join(os.path.dirname(__file__), "..", "studio", "cache")), "misses.jsonl")
    if not os.environ.get("STUDIO_D1") and os.path.exists(misses):   # the command line's own log, when run locally
        cutoff = time.time() - a.days * 86400
        with open(misses) as f:
            for line in f:
                try:
                    m = json.loads(line)
                except ValueError:
                    continue
                if m.get("t", 0) >= cutoff:
                    words.update(m.get("unknown", []))
    print("Words the rules didn't know (add them to studio/parse/lexicon.yaml):")
    print("  " + (", ".join(f"{w} ({n})" for w, n in words.most_common(25)) or "none"))
    print("Latest feedback:")
    for r in fb:
        print(f"  [{r['kind']}] {time.strftime('%m-%d', time.gmtime(r['created']))}  {r['prompt']!r}  {r['note']}")
    if not fb:
        print("  none")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m app.admin", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("invite", help="make invite codes")
    p.add_argument("--uses", type=int, default=1)
    p.add_argument("--count", type=int, default=1)
    p.add_argument("--note", default="")
    p.set_defaults(fn=cmd_invite)
    sub.add_parser("invites", help="list invite codes").set_defaults(fn=cmd_invites)
    sub.add_parser("waitlist", help="list the waitlist").set_defaults(fn=cmd_waitlist)
    p = sub.add_parser("invite-waitlist", help="email single-use codes to the next N people waiting")
    p.add_argument("n", type=int)
    p.set_defaults(fn=cmd_invite_waitlist)
    p = sub.add_parser("plan", help="set a plan by hand")
    p.add_argument("email")
    p.add_argument("plan", choices=("free", "pro"))
    p.set_defaults(fn=cmd_plan)
    p = sub.add_parser("credits", help="add (or with a minus sign, remove) credits")
    p.add_argument("email")
    p.add_argument("n", type=int)
    p.set_defaults(fn=cmd_credits)
    p = sub.add_parser("reset-link", help="print a password reset link for someone")
    p.add_argument("email")
    p.set_defaults(fn=cmd_reset_link)
    p = sub.add_parser("report", help="funnel, misses and feedback")
    p.add_argument("--days", type=int, default=14)
    p.set_defaults(fn=cmd_report)
    a = ap.parse_args(argv)
    db.init(settings.db_path)
    a.fn(a)


if __name__ == "__main__":
    main()
