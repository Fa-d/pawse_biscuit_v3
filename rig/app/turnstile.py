"""Cloudflare Turnstile: a mostly invisible check that a form was sent by a person, not a script.

The page renders Cloudflare's widget (only when TURNSTILE_SITE_KEY is set) and sends its one-time token with the form;
the server asks Cloudflare whether the token is good.  Used on the forms a bot would fill: email signup, waitlist,
feedback and password reset.  Without both keys (development, tests) the check is skipped.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from fastapi import HTTPException

from .config import settings

VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def enabled():
    return bool(settings.turnstile_site_key and settings.turnstile_secret)


def verify(token: str, ip: str) -> bool:
    body = urllib.parse.urlencode({"secret": settings.turnstile_secret, "response": token, "remoteip": ip}).encode()
    req = urllib.request.Request(VERIFY_URL, data=body, method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read()).get("success") is True
    except (urllib.error.URLError, ValueError, TimeoutError):
        return False                                     # can't ask Cloudflare: treat as not passed


def check(token: str, ip: str):
    if not enabled():
        return
    if not token:
        raise HTTPException(400, "Wait for the human check to finish, then try again.")
    if not verify(token, ip):
        raise HTTPException(400, "The human check didn't pass. Try again.")
