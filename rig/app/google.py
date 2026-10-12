"""Sign in with Google: OpenID Connect, authorization code flow with PKCE, done on the server.

The browser goes to Google at the top level and comes back to /auth/google/callback with a one-time code; the server
swaps the code for an ID token directly with Google.  Because that token arrives straight from Google over TLS, its
claims are read without checking the signature (OpenID Connect Core 3.1.3.7), but audience, issuer, expiry, nonce and
email verification are all checked.  No Google script runs on our pages, so the content security policy is unchanged.
"""
from __future__ import annotations

import base64
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request

from .config import settings

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
ISSUERS = ("https://accounts.google.com", "accounts.google.com")


class GoogleError(Exception):
    """`str(e)` is a short key the studio turns into a message: cancelled, state, unverified, failed."""


def redirect_uri():
    return f"{settings.base_url}/auth/google/callback"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def challenge(verifier: str) -> str:
    return _b64url(hashlib.sha256(verifier.encode()).digest())


def start_url(state: str, nonce: str, verifier: str) -> str:
    return AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id": settings.google_client_id, "redirect_uri": redirect_uri(), "response_type": "code",
        "scope": "openid email", "state": state, "nonce": nonce, "prompt": "select_account",
        "code_challenge": challenge(verifier), "code_challenge_method": "S256",
    })


def _claims(id_token: str) -> dict:
    try:
        payload = id_token.split(".")[1]
        return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except (IndexError, ValueError):
        raise GoogleError("failed") from None


def check(claims: dict, nonce: str) -> dict:
    """The claims we rely on, or GoogleError.  Returns {sub, email}."""
    if claims.get("iss") not in ISSUERS or claims.get("aud") != settings.google_client_id:
        raise GoogleError("failed")
    if not isinstance(claims.get("exp"), (int, float)) or claims["exp"] < time.time():
        raise GoogleError("failed")
    if not nonce or claims.get("nonce") != nonce:
        raise GoogleError("state")
    if claims.get("email_verified") is not True or not claims.get("email") or not claims.get("sub"):
        raise GoogleError("unverified")
    return {"sub": str(claims["sub"]), "email": str(claims["email"]).strip().lower()}


def exchange(code: str, verifier: str) -> dict:
    """Swap the one-time code for the ID token's claims (unchecked; see check)."""
    body = urllib.parse.urlencode({
        "code": code, "client_id": settings.google_client_id, "client_secret": settings.google_client_secret,
        "redirect_uri": redirect_uri(), "grant_type": "authorization_code", "code_verifier": verifier,
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=body, method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            tokens = json.loads(r.read())
    except (urllib.error.URLError, ValueError, TimeoutError):
        raise GoogleError("failed") from None
    if "id_token" not in tokens:
        raise GoogleError("failed")
    return _claims(tokens["id_token"])
