"""Email over plain SMTP (any provider: Postmark, Resend, SES, Google Workspace...).

Without SMTP_HOST nothing is sent: each message is written to the outbox folder as an .eml file and logged, so
password resets and invites can be tested locally.
"""
from __future__ import annotations

import logging
import os
import re
import smtplib
import ssl
import time
from email.message import EmailMessage

from .config import settings

log = logging.getLogger("studio.mail")


def send(to: str, subject: str, text: str) -> str:
    """Send one plain-text email.  Returns 'sent' or the outbox path."""
    msg = EmailMessage()
    msg["From"] = settings.mail_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    if not settings.smtp_host:
        os.makedirs(settings.outbox, exist_ok=True)
        path = os.path.join(settings.outbox, f"{int(time.time() * 1000)}-{re.sub(r'[^a-z0-9]+', '_', to.lower())}.eml")
        with open(path, "wb") as f:
            f.write(bytes(msg))
        log.info("outbox: %s -> %s", subject, path)
        return path
    sec = settings.smtp_security
    if sec == "ssl":
        server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=ssl.create_default_context(), timeout=20)
    else:
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20)
    with server:
        if sec == "starttls":
            server.starttls(context=ssl.create_default_context())
        if settings.smtp_user:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)
    log.info("sent: %s", subject)
    return "sent"


def reset_email(to, link):
    return send(to, "Reset your Pawse Studio password", f"""Hi,

Someone asked to reset the password for your Pawse Studio account. To choose a new one, open this link within an hour:

{link}

If it wasn't you, ignore this email. Your password stays the same.

Pawse Studio
""")


def invite_email(to, link, code):
    return send(to, "Your Pawse Studio invite", f"""Hi,

You're in. Your invite code is {code}. Open this link to create your account and make your first sticker:

{link}

Pawse Studio
""")
