"""Sticker Studio web app.

    cd rig && .venv/bin/uvicorn app.main:app --reload            # http://localhost:8000

Everything the page does goes through /api/*.  The browser plays the Lottie preview itself (lottie-web), so the
server only composes; files are rasterised on download.
"""
from __future__ import annotations

import json
import logging
import os
import secrets
import threading

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from studio.packs import PackError, telegram_zip, whatsapp_zip
from studio.parse.fallback import default_parser, parse
from studio.spec import StickerSpec

from . import auth, billing, db, mailer, plans, render
from .config import settings
from .vocab import vocab

log = logging.getLogger("studio")
HERE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(HERE, "static")
PACK_MAX = 30

app = FastAPI(title="Pawse Studio", docs_url="/api/docs" if settings.dev else None, redoc_url=None, openapi_url="/api/openapi.json" if settings.dev else None)
db.init(settings.db_path)
default_parser()                                         # load the word lists once, at start-up
_vocab = vocab()


# ---------------------------------------------------------------- safety
@app.middleware("http")
async def guard(request: Request, call_next):
    # State-changing calls must be JSON: browsers can't send that cross-site without CORS, and the session cookie is
    # SameSite=Lax.  Stripe's webhook is the one exception (it is signed instead).
    if request.method in ("POST", "PUT", "PATCH", "DELETE") and request.url.path.startswith("/api/") \
            and request.url.path != "/api/billing/webhook":
        if not request.headers.get("content-type", "").startswith("application/json"):
            return JSONResponse({"detail": "Send JSON."}, status_code=415)
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "same-origin"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self' https://cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; img-src 'self' data: blob:; connect-src 'self'; frame-ancestors 'none'")
    return resp


def spec_from(d: dict) -> StickerSpec:
    try:
        spec = StickerSpec.from_dict(d)
    except (ValueError, TypeError, KeyError) as e:
        raise HTTPException(400, f"That sticker can't be made: {e}") from None
    if spec.caption and len(spec.caption.text) > 60:
        raise HTTPException(400, "Keep the caption to 60 characters or fewer.")
    if len(spec.palette) > 12 or any(not isinstance(v, str) or len(v) != 7 or v[0] != "#" for v in spec.palette.values()):
        raise HTTPException(400, "Colours must be #rrggbb values.")
    return spec


# ---------------------------------------------------------------- page and vocabulary
@app.get("/", include_in_schema=False)
def landing():
    return FileResponse(os.path.join(STATIC, "landing.html"))


@app.get("/studio", include_in_schema=False)
def studio():
    return FileResponse(os.path.join(STATIC, "index.html"))


@app.get("/privacy", include_in_schema=False)
def privacy():
    return FileResponse(os.path.join(STATIC, "privacy.html"))


EXAMPLES = ["kitten waving hi with a bow", "grumpy cat saying 'no.'", "sleepy bear with coffee saying 'monday...'",
            "cool fox in shades dancing", "thank you", "on my way"]


@app.get("/api/examples")
def examples():
    """Finished stickers for the landing page, made by the same engine (no watermark: they are ours)."""
    out = []
    for prompt in EXAMPLES:
        spec = parse(prompt).spec
        doc, info = render.preview(spec, False)
        out.append({"prompt": prompt, "base": spec.base, "lottie": doc, "still": info["still"]})
    return out


def _warm():
    try:
        examples()
    except Exception:  # noqa: BLE001 - warming is best effort; the first visitor pays the cost instead
        log.exception("could not pre-compose the landing examples")


threading.Thread(target=_warm, daemon=True).start()


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(os.path.join(STATIC, "favicon.svg"), media_type="image/svg+xml")


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/api/vocab")
def get_vocab():
    return _vocab


@app.get("/api/me")
def me(request: Request):
    user = auth.current_user(request)
    with db.connect() as c:
        return {"user": plans.summary(c, user), "billing": settings.billing_ready, "dev": settings.dev,
                "free_daily": settings.free_daily_exports, "pack_credits": settings.pack_credits,
                "price_pro": settings.price_pro_label, "price_pack": settings.price_pack_label,
                "invite_only": settings.invite_only, "contact": settings.contact_email}


# ---------------------------------------------------------------- accounts
class Credentials(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(max_length=256)


class Signup(Credentials):
    invite: str = Field(default="", max_length=64)


@app.post("/api/signup")
def signup(body: Signup, request: Request, response: Response):
    email = auth.validate_signup(body.email, body.password)
    code = body.invite.strip().upper()
    with db.connect() as c:
        if c.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
            raise HTTPException(409, "That email already has an account. Sign in instead.")
        if settings.invite_only:
            if not code:
                raise HTTPException(403, "The studio is invite-only for now. Enter your invite code, or join the waitlist.")
            got = c.execute("UPDATE invites SET uses = uses + 1 WHERE code=? AND uses < max_uses", (code,)).rowcount
            if not got:
                raise HTTPException(403, "That invite code isn't valid or has been used up.")
        cur = c.execute("INSERT INTO users (email, pw_hash, created, invite) VALUES (?, ?, ?, ?)",
                        (email, auth.hash_password(body.password), db.now(), code or None))
        uid = cur.lastrowid
    auth.start_session(response, uid)
    db.bump("signup")
    return {"ok": True}


@app.post("/api/login")
def login(body: Credentials, request: Request, response: Response):
    email = body.email.strip().lower()
    ip = request.client.host if request.client else "?"
    auth.throttle(f"e:{email}", f"i:{ip}")
    with db.connect() as c:
        u = c.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if u is None or not auth.check_password(body.password, u["pw_hash"]):
        auth.failed(f"e:{email}", f"i:{ip}")
        raise HTTPException(401, "That email and password don't match.")
    auth.start_session(response, u["id"])
    return {"ok": True}


@app.post("/api/logout")
def logout(request: Request, response: Response):
    auth.end_session(request, response)
    return {"ok": True}


class Forgot(BaseModel):
    email: str = Field(max_length=320)


RESET_HOURS = 1


@app.post("/api/password/forgot")
def forgot(body: Forgot, request: Request):
    """Always answers the same, so it can't be used to find out who has an account."""
    email = body.email.strip().lower()
    ip = request.client.host if request.client else "?"
    auth.throttle(f"r:{email}", f"i:{ip}")
    auth.failed(f"r:{email}")                                  # counts requests: at most 5 resets an email per window
    with db.connect() as c:
        u = c.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if u is not None:
            token = secrets.token_urlsafe(32)
            c.execute("INSERT INTO reset_tokens (token, user_id, expires) VALUES (?, ?, ?)",
                      (auth.digest(token), u["id"], db.now() + RESET_HOURS * 3600))
    if u is not None:
        mailer.reset_email(email, f"{settings.base_url}/studio?reset={token}")
    return {"ok": True}


class Reset(BaseModel):
    token: str = Field(min_length=10, max_length=128)
    password: str = Field(max_length=256)


@app.post("/api/password/reset")
def reset_password(body: Reset, response: Response):
    auth.validate_signup("someone@example.com", body.password)            # same password rules as signup
    with db.connect() as c:
        row = c.execute("SELECT user_id FROM reset_tokens WHERE token=? AND expires>?", (auth.digest(body.token), db.now())).fetchone()
        if row is None:
            raise HTTPException(400, "That reset link has expired or was already used. Ask for a new one.")
        uid = row["user_id"]
        c.execute("UPDATE users SET pw_hash=? WHERE id=?", (auth.hash_password(body.password), uid))
        c.execute("DELETE FROM reset_tokens WHERE user_id=?", (uid,))
        c.execute("DELETE FROM sessions WHERE user_id=?", (uid,))            # signed out everywhere else
    auth.start_session(response, uid)
    return {"ok": True}


class Waitlist(BaseModel):
    email: str = Field(max_length=320)
    source: str = Field(default="", max_length=40)


@app.post("/api/waitlist")
def join_waitlist(body: Waitlist, request: Request):
    email = auth.validate_signup(body.email, "placeholder-ok")
    ip = request.client.host if request.client else "?"
    auth.throttle(f"w:{ip}")
    auth.failed(f"w:{ip}")
    with db.connect() as c:
        added = c.execute("INSERT OR IGNORE INTO waitlist (email, source, created) VALUES (?, ?, ?)",
                          (email, body.source, db.now())).rowcount
    if added:
        db.bump("waitlist")
    return {"ok": True}


class Feedback(BaseModel):
    kind: str = Field(pattern="^(wrong|idea|bug)$")
    note: str = Field(default="", max_length=500)
    prompt: str = Field(default="", max_length=200)
    spec: dict = Field(default_factory=dict)


@app.post("/api/feedback")
def feedback(body: Feedback, request: Request):
    ip = request.client.host if request.client else "?"
    auth.throttle(f"b:{ip}")
    auth.failed(f"b:{ip}")
    user = auth.current_user(request)
    with db.connect() as c:
        c.execute("INSERT INTO feedback (user_id, kind, prompt, spec, note, created) VALUES (?, ?, ?, ?, ?, ?)",
                  (user["id"] if user else None, body.kind, body.prompt, json.dumps(body.spec)[:4000], body.note, db.now()))
    db.bump(f"feedback:{body.kind}")
    return {"ok": True}


# ---------------------------------------------------------------- making stickers
class Prompt(BaseModel):
    prompt: str = Field(min_length=1, max_length=200)


@app.post("/api/parse")
def parse_prompt(body: Prompt, request: Request):
    user = auth.current_user(request)
    use_llm = False
    if settings.llm and user is not None:
        with db.connect() as c:
            use_llm = db.usage_today(c, user["id"], "llm") < settings.llm_daily
    r = parse(body.prompt, llm=use_llm)
    db.bump("prompt" if r.confident else "prompt:unsure")
    if "llm" in r.source and user is not None:
        with db.connect() as c:
            db.add_usage(c, user["id"], "llm")
    return {"spec": r.spec.to_dict(), "confident": r.confident, "source": r.source, "template": r.template,
            "understood": [{"phrase": m.phrase, "as": m.section, "name": m.name, "negated": m.negated} for m in r.matches],
            "unknown": r.unknown}


class SpecBody(BaseModel):
    spec: dict


@app.post("/api/preview")
def preview(body: SpecBody, request: Request):
    spec = spec_from(body.spec)
    user = auth.current_user(request)
    doc, info = render.preview(spec, plans.preview_watermark(user))
    return {"lottie": doc, "notes": info["notes"], "still": info["still"], "key": info["key"], "motion": info["motion"],
            "stance": info["stance"]}


class ExportBody(BaseModel):
    spec: dict
    format: str


@app.post("/api/export")
def export(body: ExportBody, request: Request):
    spec = spec_from(body.spec)
    user = auth.current_user(request)
    with db.connect() as c:
        d = plans.decide(c, user, body.format)
        if not d.allowed:
            raise HTTPException(403 if user else 401, d.reason)
        data, name, mime, warn = render.export_bytes(spec, body.format, d.watermark)
        if d.use_credit:
            got = c.execute("UPDATE users SET credits = credits - 1 WHERE id=? AND credits > 0", (user["id"],)).rowcount
            if not got:
                raise HTTPException(403, "Your credits ran out. Buy a pack or get Pro.")
        elif user["plan"] != "pro":
            db.add_usage(c, user["id"], "export")
    db.bump(f"export:{body.format}")
    headers = {"Content-Disposition": f'attachment; filename="{name}"'}
    if warn:
        headers["X-Sticker-Warning"] = warn
    return Response(data, media_type=mime, headers=headers)


# ---------------------------------------------------------------- saved stickers
class SaveBody(BaseModel):
    spec: dict
    prompt: str = Field(default="", max_length=200)


@app.get("/api/stickers")
def list_stickers(user=Depends(auth.require_user)):
    with db.connect() as c:
        rows = c.execute("SELECT id, prompt, spec, created FROM stickers WHERE user_id=? ORDER BY created DESC, id DESC LIMIT 200",
                         (user["id"],)).fetchall()
    return [{"id": r["id"], "prompt": r["prompt"], "spec": json.loads(r["spec"]), "created": r["created"]} for r in rows]


@app.post("/api/stickers")
def save_sticker(body: SaveBody, user=Depends(auth.require_user)):
    spec = spec_from(body.spec)
    with db.connect() as c:
        n = c.execute("SELECT COUNT(*) AS n FROM stickers WHERE user_id=?", (user["id"],)).fetchone()["n"]
        if n >= 200:
            raise HTTPException(400, "You have 200 saved stickers. Delete some to save more.")
        cur = c.execute("INSERT INTO stickers (user_id, prompt, spec, created) VALUES (?, ?, ?, ?)",
                        (user["id"], body.prompt, spec.to_json(), db.now()))
    db.bump("save")
    return {"id": cur.lastrowid}


@app.delete("/api/stickers/{sid}")
def delete_sticker(sid: int, user=Depends(auth.require_user)):
    with db.connect() as c:
        if not c.execute("DELETE FROM stickers WHERE id=? AND user_id=?", (sid, user["id"])).rowcount:
            raise HTTPException(404, "That sticker isn't in your collection.")
    return {"ok": True}


class PackBody(BaseModel):
    platform: str = Field(pattern="^(telegram|whatsapp)$")
    ids: list[int] = Field(default_factory=list, max_length=PACK_MAX)
    name: str = Field(default="My stickers", min_length=1, max_length=60)
    animated: bool = True                         # WhatsApp only: a pack is all animated or all static


@app.post("/api/packs")
def pack(body: PackBody, user=Depends(auth.require_user)):
    """Saved stickers as a ready-to-add pack (Pro): Telegram .tgs files with a guide, or WhatsApp's pack format."""
    if user["plan"] != "pro":
        raise HTTPException(403, "Sticker packs come with Pro.")
    with db.connect() as c:
        rows = c.execute("SELECT id, spec FROM stickers WHERE user_id=? ORDER BY created ASC, id ASC", (user["id"],)).fetchall()
    if body.ids:
        wanted = set(body.ids)
        rows = [r for r in rows if r["id"] in wanted]
    rows = rows[:PACK_MAX]
    specs = [StickerSpec.from_dict(json.loads(r["spec"])) for r in rows]
    composed = [render.composed(s) for s in specs]
    try:
        if body.platform == "telegram":
            data = telegram_zip([(s, d) for s, (d, _) in zip(specs, composed)], body.name)
        else:
            data = whatsapp_zip([(s, d, i["still"]) for s, (d, i) in zip(specs, composed)], body.name,
                                animated=body.animated, identifier=f"pawse_{user['id']}_{len(specs)}", website=settings.base_url)
    except PackError as e:
        raise HTTPException(400, " ".join(e.problems)) from None
    db.bump(f"pack:{body.platform}")
    fname = f"{body.platform}-pack.zip"
    return Response(data, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{fname}"'})


# ---------------------------------------------------------------- billing
class CheckoutBody(BaseModel):
    kind: str


@app.post("/api/billing/checkout")
def checkout(body: CheckoutBody, user=Depends(auth.require_user)):
    url = billing.checkout_url(user, body.kind)
    db.bump(f"checkout:{body.kind}")
    return {"url": url}


@app.post("/api/billing/portal")
def portal(user=Depends(auth.require_user)):
    return {"url": billing.portal_url(user)}


@app.post("/api/billing/webhook", include_in_schema=False)
async def webhook(request: Request):
    payload = await request.body()
    result = billing.handle_webhook(payload, request.headers.get("stripe-signature"))
    log.info("stripe webhook: %s", result)
    return {"received": True}


# ---------------------------------------------------------------- development only
if settings.dev:
    class DevPlan(BaseModel):
        plan: str = "free"
        credits: int = 0

    @app.post("/api/dev/plan")
    def dev_plan(body: DevPlan, user=Depends(auth.require_user)):
        """Switch your own plan without paying.  Exists only when STUDIO_DEV=1."""
        if body.plan not in ("free", "pro"):
            raise HTTPException(400, "plan is free or pro")
        with db.connect() as c:
            c.execute("UPDATE users SET plan=?, credits=? WHERE id=?", (body.plan, max(0, body.credits), user["id"]))
        return {"ok": True}
