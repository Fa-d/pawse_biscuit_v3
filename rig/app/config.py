"""Settings, read once from the environment.  Secrets (Stripe keys, webhook secret) come only from the environment
or your platform's secrets vault, never from files in the repository."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

HERE = os.path.dirname(os.path.abspath(__file__))


def _flag(name, default="0"):
    return os.environ.get(name, default).lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    base_url: str = field(default_factory=lambda: os.environ.get("STUDIO_BASE_URL", "http://localhost:8000").rstrip("/"))
    db_path: str = field(default_factory=lambda: os.environ.get("STUDIO_DB", os.path.join(HERE, "data", "studio.db")))
    dev: bool = field(default_factory=lambda: _flag("STUDIO_DEV"))                 # enables /api/dev/* helpers; never in production
    llm: bool = field(default_factory=lambda: _flag("STUDIO_LLM"))                 # Haiku fallback for signed-in users
    llm_daily: int = field(default_factory=lambda: int(os.environ.get("STUDIO_LLM_DAILY", "20")))
    free_daily_exports: int = field(default_factory=lambda: int(os.environ.get("FREE_DAILY_EXPORTS", "5")))
    pack_credits: int = field(default_factory=lambda: int(os.environ.get("PACK_CREDITS", "20")))
    # Stripe: use a restricted key (rk_...) with write access to Checkout Sessions, Customers and Billing Portal sessions
    stripe_key: str = field(default_factory=lambda: os.environ.get("STRIPE_API_KEY", ""))
    stripe_webhook_secret: str = field(default_factory=lambda: os.environ.get("STRIPE_WEBHOOK_SECRET", ""))
    price_pro: str = field(default_factory=lambda: os.environ.get("STRIPE_PRICE_PRO", ""))       # recurring monthly price
    price_pack: str = field(default_factory=lambda: os.environ.get("STRIPE_PRICE_PACK", ""))     # one-time price
    # what the pricing panel says; keep in step with the Stripe prices
    price_pro_label: str = field(default_factory=lambda: os.environ.get("PRICE_PRO_LABEL", "$4.99 a month"))
    price_pack_label: str = field(default_factory=lambda: os.environ.get("PRICE_PACK_LABEL", "$2.99"))

    behind_cloudflare: bool = field(default_factory=lambda: _flag("STUDIO_BEHIND_CLOUDFLARE"))   # trust CF-Connecting-IP
    invite_only: bool = field(default_factory=lambda: _flag("STUDIO_INVITE_ONLY"))   # beta: signup needs an invite code
    # email: plain SMTP.  No SMTP_HOST = messages go to the outbox folder next to the database (for development)
    smtp_host: str = field(default_factory=lambda: os.environ.get("SMTP_HOST", ""))
    smtp_port: int = field(default_factory=lambda: int(os.environ.get("SMTP_PORT", "587")))
    smtp_user: str = field(default_factory=lambda: os.environ.get("SMTP_USER", ""))
    smtp_password: str = field(default_factory=lambda: os.environ.get("SMTP_PASSWORD", ""))
    smtp_security: str = field(default_factory=lambda: os.environ.get("SMTP_SECURITY", "starttls"))   # starttls | ssl | none
    mail_from: str = field(default_factory=lambda: os.environ.get("MAIL_FROM", "Pawse Studio <hello@localhost>"))
    contact_email: str = field(default_factory=lambda: os.environ.get("CONTACT_EMAIL", ""))   # shown on the site; empty hides it

    @property
    def outbox(self):
        return os.path.join(os.path.dirname(self.db_path) or ".", "outbox")

    @property
    def secure_cookies(self):
        return self.base_url.startswith("https://")

    @property
    def billing_ready(self):
        return bool(self.stripe_key and self.stripe_webhook_secret and self.price_pro and self.price_pack)


settings = Settings()
