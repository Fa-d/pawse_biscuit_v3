"""Accounts: email + password (scrypt), server-side sessions in an httpOnly cookie."""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, Response

from . import db
from .config import settings

COOKIE = "sid"


def cookie_name(base):
    """__Host- cookies can only be set over HTTPS, for this exact host and path /, so no other site or subdomain can
    plant or overwrite them.  Plain names over local http, where browsers refuse the prefix."""
    return f"__Host-{base}" if settings.secure_cookies else base


def set_cookie(resp, base, value, seconds):
    resp.set_cookie(cookie_name(base), value, max_age=seconds, path="/", httponly=True, samesite="lax", secure=settings.secure_cookies)


def clear_cookie(resp, base):
    resp.delete_cookie(cookie_name(base), path="/", httponly=True, samesite="lax", secure=settings.secure_cookies)


def get_cookie(request, base):
    return request.cookies.get(cookie_name(base))
SESSION_DAYS = 30
EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}\.[^@\s]{2,}$")
_N, _R, _P = 2 ** 14, 8, 1


def hash_password(pw: str) -> str:
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(pw.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${h.hex()}"


def check_password(pw: str, stored: str) -> bool:
    try:
        _, n, r, p, salt, h = stored.split("$")
        got = hashlib.scrypt(pw.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p), dklen=len(h) // 2)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(got.hex(), h)


DUMMY_HASH = hash_password(secrets.token_urlsafe(16))      # compared when no password exists, so timing reveals nothing


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()       # the database never holds a usable session token


def start_session(resp: Response, user_id: int):
    token = secrets.token_urlsafe(32)
    with db.connect() as c:
        c.execute("DELETE FROM sessions WHERE user_id=? AND expires<?", (user_id, db.now()))   # tidy this person's old ones
        c.execute("INSERT INTO sessions (token, user_id, expires) VALUES (?, ?, ?)",
                  (digest(token), user_id, db.now() + SESSION_DAYS * 86400))
    set_cookie(resp, COOKIE, token, SESSION_DAYS * 86400)


def end_session(request: Request, resp: Response):
    token = get_cookie(request, COOKIE)
    if token:
        with db.connect() as c:
            c.execute("DELETE FROM sessions WHERE token=?", (digest(token),))
    clear_cookie(resp, COOKIE)


def current_user(request: Request):
    """The signed-in user row, or None."""
    token = get_cookie(request, COOKIE)
    if not token:
        return None
    with db.connect() as c:
        return c.execute("SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token=? AND s.expires>?",
                         (digest(token), db.now())).fetchone()


def require_user(request: Request):
    u = current_user(request)
    if u is None:
        raise HTTPException(401, "Sign in to do that.")
    return u


# ---- slow down password guessing: in 15 minutes, at most 10 failures per email and 50 per network address
# (an office or a phone network shares one address, so its limit is looser)
_fails = defaultdict(deque)
WINDOW = 900
LIMITS = {"e": 10, "i": 50, "r": 5, "w": 20, "b": 30}   # e/i: login, r: reset emails, w: waitlist, b: feedback


def throttle(*keys):
    t = time.time()
    for k in keys:
        q = _fails[k]
        while q and q[0] < t - WINDOW:
            q.popleft()
        if len(q) >= LIMITS.get(k.split(":", 1)[0], 10):
            raise HTTPException(429, "Too many attempts. Wait 15 minutes and try again.")


def failed(*keys):
    for k in keys:
        _fails[k].append(time.time())


# ---- rate limits on the expensive calls (composing and rendering are CPU work): every call counts, unlike throttle.
# Kept in memory per instance; Cloudflare's edge rule is the shared backstop (see DEPLOY.md).
_hits = defaultdict(deque)


def limit(key, n, seconds):
    if not settings.rate_limits:
        return
    t = time.time()
    if len(_hits) > 50_000:                             # forget idle keys now and then, so memory stays bounded
        for k in [k for k, q in _hits.items() if not q or q[-1] < t - 3600]:
            del _hits[k]
    q = _hits[key]
    while q and q[0] < t - seconds:
        q.popleft()
    if len(q) >= n:
        raise HTTPException(429, "Slow down a moment, then try again.", headers={"Retry-After": str(int(q[0] + seconds - t) + 1)})
    q.append(t)


def validate_signup(email: str, password: str):
    email = email.strip().lower()
    if not EMAIL.match(email):
        raise HTTPException(400, "Enter a valid email address.")
    if len(password) < 8:
        raise HTTPException(400, "Use at least 8 characters for your password.")
    if len(password) > 256:
        raise HTTPException(400, "Use at most 256 characters for your password.")
    return email
