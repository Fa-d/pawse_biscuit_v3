"""Payments with Stripe Checkout: Pro (monthly subscription) and credit packs (one-time).

Entitlements change ONLY here, from signature-verified webhook events, never from the success page:
  customer.subscription.created / .updated   status active or trialing -> pro, anything else -> free
  customer.subscription.deleted              -> free
  checkout.session.completed / .async_payment_succeeded, mode payment, payment_status not 'unpaid'
                                             -> credits += PACK_CREDITS, once per Checkout Session
Events are applied once (stripe_events table).  A user is found through their Stripe Customer id, which is created
before their first checkout, not through metadata.
"""
from __future__ import annotations

import json
import logging

from fastapi import HTTPException

from . import db
from .config import settings

log = logging.getLogger("studio.billing")

# labels that tell the two checkout flows apart in the Stripe Dashboard
FLOW = {"pro": "pawse_studio_pro_qwhxrmtz", "pack": "pawse_studio_pack_bdkfnyle"}
ACTIVE = ("active", "trialing")


def client():
    if not settings.billing_ready:
        raise HTTPException(503, "Payments aren't set up yet. Try again later.")
    import stripe
    return stripe.StripeClient(settings.stripe_key)


def _customer(sc, user):
    """The user's Stripe Customer id, created on first use."""
    if user["stripe_customer"]:
        return user["stripe_customer"]
    cust = sc.v1.customers.create(params={"email": user["email"], "metadata": {"user_id": str(user["id"])}})
    with db.connect() as c:
        c.execute("UPDATE users SET stripe_customer=? WHERE id=?", (cust.id, user["id"]))
    return cust.id


def checkout_url(user, kind: str) -> str:
    if kind not in FLOW:
        raise HTTPException(400, "Choose Pro or a credit pack.")
    if kind == "pro" and user["plan"] == "pro":
        raise HTTPException(409, "You already have Pro. Manage it from your account.")
    sc = client()
    params = {
        "mode": "subscription" if kind == "pro" else "payment",
        "customer": _customer(sc, user),
        "client_reference_id": str(user["id"]),
        "line_items": [{"price": settings.price_pro if kind == "pro" else settings.price_pack, "quantity": 1}],
        "success_url": f"{settings.base_url}/?paid={kind}",
        "cancel_url": f"{settings.base_url}/?cancelled={kind}",
        "integration_identifier": FLOW[kind],
        "allow_promotion_codes": True,
    }
    return sc.v1.checkout.sessions.create(params=params).url


def portal_url(user) -> str:
    if not user["stripe_customer"]:
        raise HTTPException(400, "There's nothing to manage yet.")
    sc = client()
    return sc.v1.billing_portal.sessions.create(params={"customer": user["stripe_customer"], "return_url": settings.base_url}).url


def handle_webhook(payload: bytes, signature: str | None):
    """Verify, then apply the event once.  Returns a short word for the log."""
    sc = client()
    try:
        sc.construct_event(payload, signature, settings.stripe_webhook_secret)
    except Exception as e:  # noqa: BLE001 - the SDK raises ValueError or SignatureVerificationError
        log.warning("rejected webhook: %s", type(e).__name__)
        raise HTTPException(400, "Invalid signature.") from None
    event = json.loads(payload)
    return apply_event(event)


def apply_event(event: dict) -> str:
    """Apply one verified event.  Split out so tests can feed events without signatures."""
    kind, obj = event["type"], event["data"]["object"]
    with db.connect() as c:
        if c.execute("SELECT 1 FROM stripe_events WHERE id=?", (event["id"],)).fetchone():
            return "duplicate"
        c.execute("INSERT INTO stripe_events (id, type, received) VALUES (?, ?, ?)", (event["id"], kind, db.now()))
        user = c.execute("SELECT * FROM users WHERE stripe_customer=?", (obj.get("customer"),)).fetchone() if obj.get("customer") else None
        if user is None:
            log.warning("event %s %s: no user for customer %s", event["id"], kind, obj.get("customer"))
            return "no-user"

        if kind in ("customer.subscription.created", "customer.subscription.updated"):
            plan = "pro" if obj["status"] in ACTIVE else "free"
            c.execute("UPDATE users SET plan=?, stripe_subscription=? WHERE id=?", (plan, obj["id"], user["id"]))
            return f"plan {plan}"
        if kind == "customer.subscription.deleted":
            c.execute("UPDATE users SET plan='free' WHERE id=? AND (stripe_subscription IS NULL OR stripe_subscription=?)",
                      (user["id"], obj["id"]))
            return "plan free"
        if kind in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
            if obj.get("mode") != "payment" or obj.get("payment_status") == "unpaid":
                return "waiting"                     # subscriptions are handled by their own events; delayed payments later
            done = c.execute("SELECT 1 FROM fulfilled WHERE session_id=?", (obj["id"],)).fetchone()
            if done:
                return "already fulfilled"
            c.execute("INSERT INTO fulfilled (session_id, user_id, created) VALUES (?, ?, ?)", (obj["id"], user["id"], db.now()))
            c.execute("UPDATE users SET credits = credits + ? WHERE id=?", (settings.pack_credits, user["id"]))
            return f"credits +{settings.pack_credits}"
        if kind in ("invoice.paid", "invoice.payment_failed", "checkout.session.async_payment_failed"):
            # access follows the subscription's status, which Stripe updates (and sends) after these
            log.info("event %s %s for user %s", event["id"], kind, user["id"])
            return "noted"
    return "ignored"
