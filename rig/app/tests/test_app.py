"""Web app tests.  Run from rig/:   python3 -m unittest app.tests.test_app -v

Stripe is never called: the settings get dummy keys so the webhook path is live, signatures are computed here the way
Stripe computes them, and checkout is checked only for its refusals.
"""
from __future__ import annotations

import hashlib
import hmac
import io
import json
import os
import tempfile
import time
import unittest
import zipfile

from PIL import Image
from urllib.parse import parse_qs, urlparse

_tmp = tempfile.mkdtemp()
os.environ.update({
    "STUDIO_DB": os.path.join(_tmp, "test.db"), "STUDIO_DEV": "1", "STUDIO_CACHE": _tmp, "FREE_DAILY_EXPORTS": "2",
    "PACK_CREDITS": "20", "STRIPE_API_KEY": "rk_test_dummy", "STRIPE_WEBHOOK_SECRET": "whsec_test_dummy",
    "STRIPE_PRICE_PRO": "price_pro_dummy", "STRIPE_PRICE_PACK": "price_pack_dummy", "STUDIO_RATE_LIMITS": "0",
})

from fastapi.testclient import TestClient  # noqa: E402

from app import auth, billing, db, google  # noqa: E402
from app.main import app  # noqa: E402

SPEC = {"face": "joy", "motion": "bounce"}


def new_client(email=None, plan=None, credits=0):
    c = TestClient(app)
    if email:
        r = c.post("/api/signup", json={"email": email, "password": "correct horse"})
        assert r.status_code == 200, r.text
        if plan or credits:
            c.post("/api/dev/plan", json={"plan": plan or "free", "credits": credits})
    return c


def layer_names(doc):
    return [L["nm"] for L in doc["layers"]]


class Accounts(unittest.TestCase):
    def test_signup_login_logout(self):
        c = new_client("a@example.com")
        self.assertEqual(c.get("/api/me").json()["user"]["email"], "a@example.com")
        c.post("/api/logout", json={})
        self.assertIsNone(c.get("/api/me").json()["user"])
        self.assertEqual(c.post("/api/login", json={"email": "a@example.com", "password": "wrong pass"}).status_code, 401)
        self.assertEqual(c.post("/api/login", json={"email": "A@Example.com", "password": "correct horse"}).status_code, 200)
        self.assertEqual(c.get("/api/me").json()["user"]["plan"], "free")

    def test_bad_signups(self):
        c = TestClient(app)
        self.assertEqual(c.post("/api/signup", json={"email": "nope", "password": "correct horse"}).status_code, 400)
        self.assertEqual(c.post("/api/signup", json={"email": "b@example.com", "password": "short"}).status_code, 400)
        new_client("dup@example.com")
        self.assertEqual(c.post("/api/signup", json={"email": "dup@example.com", "password": "correct horse"}).status_code, 409)

    def test_session_token_is_not_stored(self):
        c = new_client("t@example.com")
        token = c.cookies.get("sid")
        with db.connect() as conn:
            stored = [r["token"] for r in conn.execute("SELECT token FROM sessions")]
        self.assertNotIn(token, stored)

    def test_password_guessing_is_slowed(self):
        new_client("g@example.com")
        c = TestClient(app)
        codes = [c.post("/api/login", json={"email": "g@example.com", "password": f"guess{i:04d}"}).status_code for i in range(12)]
        self.assertEqual(codes[-1], 429)

    def test_form_posts_are_refused(self):
        c = TestClient(app)
        r = c.post("/api/signup", data={"email": "f@example.com", "password": "correct horse"})
        self.assertEqual(r.status_code, 415)


class Making(unittest.TestCase):
    def test_parse(self):
        r = TestClient(app).post("/api/parse", json={"prompt": "grumpy cat saying 'no'"}).json()
        self.assertEqual(r["spec"]["base"], "mochi")
        self.assertEqual(r["spec"]["caption"]["text"], "no")
        self.assertTrue(r["confident"])

    def test_preview_is_marked_until_you_pay(self):
        anon = TestClient(app).post("/api/preview", json={"spec": SPEC})
        self.assertEqual(anon.headers["content-type"], "image/webp")
        self.assertIn("notes", json.loads(anon.headers["x-preview"]))
        pro_client = new_client("pro-preview@example.com", plan="pro")
        stills = [cl.post("/api/preview", json={"spec": SPEC, "kind": "still"}) for cl in (TestClient(app), pro_client)]
        self.assertEqual([r.headers["content-type"] for r in stills], ["image/png"] * 2)
        marked, clean = (Image.open(io.BytesIO(r.content)).convert("RGBA") for r in stills)
        self.assertEqual(marked.size, (400, 400))
        changed = sum(1 for a, b in zip(marked.getdata(), clean.getdata()) if a != b)
        self.assertGreater(changed, 2000)                     # the mark is in the pixels, not a layer to delete

    def test_bad_specs_are_refused(self):
        c = TestClient(app)
        for spec in ({"face": "smirk"}, {"props": ["sword"]}, {"caption": "x" * 61}, {"palette": {"orange": "red"}}, {"hack": 1}):
            with self.subTest(spec=spec):
                self.assertEqual(c.post("/api/preview", json={"spec": spec}).status_code, 400)


class Downloads(unittest.TestCase):
    def export(self, c, fmt, spec=SPEC):
        return c.post("/api/export", json={"spec": spec, "format": fmt})

    def test_signed_out(self):
        self.assertEqual(self.export(TestClient(app), "png").status_code, 401)

    def test_free_account(self):
        c = new_client("free@example.com")
        r = self.export(c, "png")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers["content-type"], "image/png")
        self.assertEqual(self.export(c, "tgs").status_code, 403)          # animated needs Pro or credits
        self.assertEqual(self.export(c, "webp").status_code, 200)
        r = self.export(c, "png")                                          # FREE_DAILY_EXPORTS = 2 in these tests
        self.assertEqual(r.status_code, 403)
        self.assertIn("free downloads", r.json()["detail"])
        self.assertEqual(c.get("/api/me").json()["user"]["free_left_today"], 0)

    def test_free_download_carries_the_mark(self):
        import gzip
        c = new_client("mark@example.com", credits=0)
        c.post("/api/dev/plan", json={"plan": "pro"})
        clean = self.export(c, "json").json()
        self.assertNotIn("watermark", layer_names(clean))
        c.post("/api/dev/plan", json={"plan": "free", "credits": 1})
        tgs = json.loads(gzip.decompress(self.export(c, "tgs").content))
        self.assertNotIn("watermark", layer_names(tgs))                    # a credit buys a clean file

    def test_credits(self):
        c = new_client("credits@example.com", credits=2)
        self.assertEqual(self.export(c, "tgs").status_code, 200)
        self.assertEqual(c.get("/api/me").json()["user"]["credits"], 1)
        self.assertEqual(self.export(c, "gif").status_code, 200)
        self.assertEqual(c.get("/api/me").json()["user"]["credits"], 0)
        self.assertEqual(self.export(c, "gif").status_code, 403)

    def test_pro(self):
        c = new_client("pro@example.com", plan="pro")
        for fmt in ("png", "tgs", "json"):
            with self.subTest(fmt=fmt):
                self.assertEqual(self.export(c, fmt).status_code, 200)
        self.assertEqual(self.export(c, "bmp").status_code, 403)


class Collection(unittest.TestCase):
    def test_save_list_delete_and_pack(self):
        c = new_client("collector@example.com")
        self.assertEqual(TestClient(app).get("/api/stickers").status_code, 401)
        sid = c.post("/api/stickers", json={"spec": SPEC, "prompt": "yay"}).json()["id"]
        c.post("/api/stickers", json={"spec": {"motion": "wave"}, "prompt": "hi"})
        self.assertEqual([s["prompt"] for s in c.get("/api/stickers").json()], ["hi", "yay"])
        self.assertEqual(c.post("/api/packs", json={"platform": "telegram"}).status_code, 403)
        c.post("/api/dev/plan", json={"plan": "pro"})
        r = c.post("/api/packs", json={"platform": "telegram", "name": "Mine"})
        self.assertEqual(r.status_code, 200)
        names = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
        self.assertEqual(sum(n.endswith(".tgs") for n in names), 2)
        self.assertIn("HOW-TO-ADD-TO-TELEGRAM.txt", names)
        r = c.post("/api/packs", json={"platform": "whatsapp"})                 # WhatsApp needs at least 3
        self.assertEqual(r.status_code, 400)
        self.assertIn("3 to 30", r.json()["detail"])
        self.assertEqual(c.request("DELETE", f"/api/stickers/{sid}", json={}).status_code, 200)
        other = new_client("other@example.com")
        self.assertEqual(other.request("DELETE", f"/api/stickers/{sid}", json={}).status_code, 404)
        self.assertEqual(len(c.get("/api/stickers").json()), 1)


class WhatsAppPack(unittest.TestCase):
    def test_pack_format(self):
        c = new_client("wa@example.com", plan="pro")
        for spec in ({"motion": "wave"}, {"face": "angry", "effects": ["anger"]}, {"props": ["mug"], "caption": {"text": "Hi"}}):
            c.post("/api/stickers", json={"spec": spec})
        r = c.post("/api/packs", json={"platform": "whatsapp", "name": "Test pack"})
        self.assertEqual(r.status_code, 200, r.text)
        z = zipfile.ZipFile(io.BytesIO(r.content))
        pack = json.loads(z.read("contents.json"))["sticker_packs"][0]
        self.assertTrue(pack["animated_sticker_pack"])
        self.assertEqual(pack["tray_image_file"], "tray.png")
        self.assertEqual(len(pack["stickers"]), 3)
        from PIL import Image
        from studio.export import webp_durations
        self.assertEqual(Image.open(io.BytesIO(z.read("tray.png"))).size, (96, 96))
        for st in pack["stickers"]:
            data = z.read(st["image_file"])
            self.assertLessEqual(len(data), 500 * 1024)
            self.assertEqual(Image.open(io.BytesIO(data)).size, (512, 512))
            durs = webp_durations(data)
            self.assertGreaterEqual(min(durs), 8)
            self.assertLessEqual(sum(durs), 10000)
            self.assertTrue(1 <= len(st["emojis"]) <= 3)
        static = zipfile.ZipFile(io.BytesIO(c.post("/api/packs", json={"platform": "whatsapp", "animated": False}).content))
        for st in json.loads(static.read("contents.json"))["sticker_packs"][0]["stickers"]:
            self.assertLessEqual(len(static.read(st["image_file"])), 100 * 1024)


class PasswordReset(unittest.TestCase):
    def test_reset_flow(self):
        import glob
        from app.config import settings
        new_client("forgetful@example.com")
        c = TestClient(app)
        self.assertEqual(c.post("/api/password/forgot", json={"email": "nobody@example.com"}).json(), {"ok": True})
        before = set(glob.glob(os.path.join(settings.outbox, "*forgetful*")))
        self.assertEqual(c.post("/api/password/forgot", json={"email": "Forgetful@example.com"}).json(), {"ok": True})
        mail = (set(glob.glob(os.path.join(settings.outbox, "*forgetful*"))) - before).pop()
        import email
        from email import policy
        with open(mail, "rb") as f:
            body = email.message_from_binary_file(f, policy=policy.default).get_content()   # decoded, as a mail app shows it
        self.assertIn("/studio?reset=", body)
        token = body.split("reset=")[1].split()[0]
        self.assertEqual(c.post("/api/password/reset", json={"token": token, "password": "short"}).status_code, 400)
        self.assertEqual(c.post("/api/password/reset", json={"token": token, "password": "a brand new one"}).status_code, 200)
        self.assertEqual(c.get("/api/me").json()["user"]["email"], "forgetful@example.com")
        self.assertEqual(c.post("/api/password/reset", json={"token": token, "password": "another new one"}).status_code, 400)
        fresh = TestClient(app)
        self.assertEqual(fresh.post("/api/login", json={"email": "forgetful@example.com", "password": "correct horse"}).status_code, 401)
        self.assertEqual(fresh.post("/api/login", json={"email": "forgetful@example.com", "password": "a brand new one"}).status_code, 200)

    def test_reset_requests_are_limited(self):
        c = TestClient(app)
        codes = [c.post("/api/password/forgot", json={"email": "spam@example.com"}).status_code for _ in range(7)]
        self.assertEqual(codes[:5], [200] * 5)
        self.assertEqual(codes[-1], 429)


class Beta(unittest.TestCase):
    def setUp(self):
        from app.config import settings
        object.__setattr__(settings, "invite_only", True)

    def tearDown(self):
        from app.config import settings
        object.__setattr__(settings, "invite_only", False)

    def test_invite_codes(self):
        from app import admin
        with db.connect() as conn:
            conn.execute("INSERT INTO invites (code, max_uses, created) VALUES ('PAWS-TEST01', 1, 0)")
        c = TestClient(app)
        self.assertTrue(c.get("/api/me").json()["invite_only"])
        body = {"email": "beta1@example.com", "password": "correct horse"}
        self.assertEqual(c.post("/api/signup", json=body).status_code, 403)
        self.assertEqual(c.post("/api/signup", json=dict(body, invite="WRONG")).status_code, 403)
        self.assertEqual(c.post("/api/signup", json=dict(body, invite="paws-test01")).status_code, 200)
        r = TestClient(app).post("/api/signup", json={"email": "beta2@example.com", "password": "correct horse", "invite": "PAWS-TEST01"})
        self.assertEqual(r.status_code, 403)                                      # single use
        self.assertEqual(len(admin.new_code()), 11)

    def test_waitlist_and_admin(self):
        import contextlib
        from app import admin
        c = TestClient(app)
        for e in ("w1@example.com", "W1@example.com", "w2@example.com"):
            self.assertEqual(c.post("/api/waitlist", json={"email": e, "source": "landing"}).status_code, 200)
        self.assertEqual(c.post("/api/waitlist", json={"email": "not an email"}).status_code, 400)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            admin.main(["invite-waitlist", "5"])
            admin.main(["report", "--days", "2"])
        text = out.getvalue()
        self.assertIn("invited 2", text)
        self.assertIn("waitlist joins", text)
        with db.connect() as conn:
            code = conn.execute("SELECT invite FROM waitlist WHERE email='w2@example.com'").fetchone()["invite"]
        r = TestClient(app).post("/api/signup", json={"email": "w2@example.com", "password": "correct horse", "invite": code})
        self.assertEqual(r.status_code, 200)


class Pages(unittest.TestCase):
    def test_pages_and_feedback(self):
        c = TestClient(app)
        for path in ("/", "/studio", "/privacy", "/favicon.ico"):
            with self.subTest(path=path):
                self.assertEqual(c.get(path).status_code, 200)
        from app.main import ASSET_V
        html = c.get("/studio").text                    # scripts and styles are stamped, so no cache serves old ones
        self.assertIn(f'src="/static/app.js?v={ASSET_V}"', html)
        self.assertNotRegex(html, r'(?:href|src)="/static/[^"?]+"')
        self.assertIn("immutable", c.get(f"/static/app.js?v={ASSET_V}").headers["cache-control"])
        self.assertEqual(c.get("/static/app.js").headers["cache-control"], "public, max-age=300")
        ex = c.get("/api/examples").json()
        self.assertGreaterEqual(len(ex), 4)
        self.assertEqual(set(ex[0]), {"prompt", "base", "image", "still"})
        img = c.get(ex[0]["image"])
        self.assertEqual((img.headers["content-type"], "immutable" in img.headers["cache-control"]), ("image/webp", True))
        self.assertEqual(c.get("/api/examples/../../main.py").status_code, 404)
        self.assertEqual(c.post("/api/feedback", json={"kind": "wrong", "prompt": "x", "note": "it waved", "spec": SPEC}).status_code, 200)
        self.assertEqual(c.post("/api/feedback", json={"kind": "rant"}).status_code, 422)

    def test_origin_key(self):
        from app.config import settings
        object.__setattr__(settings, "origin_key", "from-the-worker")
        try:
            c = TestClient(app)
            self.assertEqual(c.get("/").status_code, 404)
            self.assertEqual(c.get("/", headers={"X-Origin-Key": "guess"}).status_code, 404)
            self.assertEqual(c.get("/", headers={"X-Origin-Key": "from-the-worker"}).status_code, 200)
        finally:
            object.__setattr__(settings, "origin_key", "")


class Protection(unittest.TestCase):
    """The art never reaches the browser as Lottie; limits, headers, cookies, bot checks and account deletion."""

    def setUp(self):
        from app.config import settings
        self.settings = settings

    def test_no_lottie_reaches_the_browser(self):
        c = TestClient(app)
        bodies = [c.post("/api/preview", json={"spec": SPEC}).content, c.post("/api/preview", json={"spec": SPEC, "kind": "still"}).content,
                  c.get("/api/examples").content, c.get(c.get("/api/examples").json()[0]["image"]).content]
        for b in bodies:
            self.assertNotIn(b'"layers"', b)
        self.assertEqual(c.post("/api/export", json={"spec": SPEC, "format": "lottie"}).status_code, 401)
        for page_ in ("/", "/studio"):
            self.assertFalse("lottie-web" in c.get(page_).text, page_)                    # no player script on the pages

    def test_thumbs_are_private(self):
        owner, other = new_client("thumb-owner@example.com"), new_client("thumb-other@example.com")
        sid = owner.post("/api/stickers", json={"spec": SPEC, "prompt": "joy"}).json()["id"]
        r = owner.get(f"/api/stickers/{sid}/thumb.png")
        self.assertEqual((r.status_code, r.headers["content-type"], Image.open(io.BytesIO(r.content)).size), (200, "image/png", (200, 200)))
        self.assertEqual(other.get(f"/api/stickers/{sid}/thumb.png").status_code, 404)
        self.assertEqual(TestClient(app).get(f"/api/stickers/{sid}/thumb.png").status_code, 401)

    def test_rate_limits(self):
        object.__setattr__(self.settings, "rate_limits", True)
        auth._hits.clear()
        try:
            c = TestClient(app)
            codes = [c.post("/api/parse", json={"prompt": "happy fox"}).status_code for _ in range(61)]
            self.assertEqual((codes.count(200), codes[-1]), (60, 429))
            self.assertIn("retry-after", c.post("/api/parse", json={"prompt": "happy fox"}).headers)
        finally:
            object.__setattr__(self.settings, "rate_limits", False)
            auth._hits.clear()

    def test_body_limit(self):
        c = TestClient(app)
        self.assertEqual(c.post("/api/parse", json={"prompt": "x" * 70_000}).status_code, 413)

        def chunks():                                          # no Content-Length, like the Cloudflare Worker sends
            yield b'{"prompt": "'
            for _ in range(80):
                yield b"x" * 1024
            yield b'"}'
        r = c.post("/api/parse", content=chunks(), headers={"Content-Type": "application/json"})
        self.assertIn(r.status_code, (400, 413))

    def test_headers(self):
        c = TestClient(app)
        h = c.get("/").headers
        for name in ("strict-transport-security", "permissions-policy", "cross-origin-opener-policy", "cross-origin-resource-policy"):
            self.assertIn(name, h)
        self.assertIn("object-src 'none'", h["content-security-policy"])
        self.assertNotIn("cdnjs", h["content-security-policy"])
        self.assertEqual(c.get("/api/me").headers["cache-control"], "no-store")

    def test_host_only_cookie(self):
        object.__setattr__(self.settings, "base_url", "https://stickers.example")
        try:
            c = TestClient(app, base_url="https://testserver")
            r = c.post("/api/signup", json={"email": "host-cookie@example.com", "password": "correct horse"})
            self.assertIn("__Host-sid=", r.headers["set-cookie"])
            self.assertIn("Secure", r.headers["set-cookie"])
            self.assertEqual(c.get("/api/me").json()["user"]["email"], "host-cookie@example.com")
        finally:
            object.__setattr__(self.settings, "base_url", "http://localhost:8000")

    def test_turnstile(self):
        from app import turnstile
        object.__setattr__(self.settings, "turnstile_site_key", "site")
        object.__setattr__(self.settings, "turnstile_secret", "secret")
        real = turnstile.verify
        turnstile.verify = lambda token, ip: token == "good"
        try:
            c = TestClient(app)
            self.assertEqual(c.get("/api/me").json()["turnstile"], "site")
            body = {"email": "human@example.com", "source": "landing"}
            self.assertEqual(c.post("/api/waitlist", json=body).status_code, 400)
            self.assertEqual(c.post("/api/waitlist", json=dict(body, turnstile="bot")).status_code, 400)
            self.assertEqual(c.post("/api/waitlist", json=dict(body, turnstile="good")).status_code, 200)
            self.assertEqual(c.post("/api/signup", json={"email": "h2@example.com", "password": "correct horse"}).status_code, 400)
        finally:
            turnstile.verify = real
            object.__setattr__(self.settings, "turnstile_site_key", "")
            object.__setattr__(self.settings, "turnstile_secret", "")

    def test_delete_account(self):
        c = new_client("leaving@example.com")
        c.post("/api/stickers", json={"spec": SPEC, "prompt": "bye"})
        uid = db_user("leaving@example.com")["id"]
        self.assertEqual(c.post("/api/account/delete", json={"email": "someone@example.com"}).status_code, 400)
        self.assertEqual(c.post("/api/account/delete", json={"email": "Leaving@Example.com"}).status_code, 200)
        self.assertIsNone(c.get("/api/me").json()["user"])
        with db.connect() as conn:
            for table in ("users", "sessions", "stickers"):
                col = "id" if table == "users" else "user_id"
                self.assertIsNone(conn.execute(f"SELECT 1 FROM {table} WHERE {col}=?", (uid,)).fetchone(), table)
        new_client("leaving@example.com")                       # the address is free again
        pro = new_client("pro-leaving@example.com", plan="pro")
        with db.connect() as conn:
            conn.execute("UPDATE users SET stripe_subscription='sub_123' WHERE email='pro-leaving@example.com'")
        self.assertEqual(pro.post("/api/account/delete", json={"email": "pro-leaving@example.com"}).status_code, 409)


def db_user(email):
    with db.connect() as conn:
        return conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()


class GoogleSignIn(unittest.TestCase):
    """Google is never called: google.exchange is replaced by one that returns the claims a real ID token would carry."""
    CID = "test-client.apps.googleusercontent.com"

    def setUp(self):
        from app.config import settings
        self.settings = settings
        object.__setattr__(settings, "google_client_id", self.CID)
        object.__setattr__(settings, "google_client_secret", "test-secret")
        self.real_exchange = google.exchange

    def tearDown(self):
        google.exchange = self.real_exchange
        for k, v in (("google_client_id", ""), ("google_client_secret", ""), ("invite_only", False)):
            object.__setattr__(self.settings, k, v)

    def sign_in(self, c, sub, email, invite="", verified=True, nonce=None, state=None):
        r = c.get("/auth/google/start", params={"invite": invite} if invite else None, follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        at = urlparse(r.headers["location"])
        q = {k: v[0] for k, v in parse_qs(at.query).items()}
        self.assertEqual((at.netloc, q["scope"], q["code_challenge_method"]), ("accounts.google.com", "openid email", "S256"))
        self.assertEqual(q["redirect_uri"], "http://localhost:8000/auth/google/callback")
        claims = {"iss": "https://accounts.google.com", "aud": self.CID, "exp": time.time() + 300, "sub": sub,
                  "email": email, "email_verified": verified, "nonce": nonce or q["nonce"]}

        def exchange(code, verifier):
            self.assertEqual(google.challenge(verifier), q["code_challenge"])      # the verifier came back intact
            return claims
        google.exchange = exchange
        return c.get("/auth/google/callback", params={"code": "one-time", "state": state or q["state"]}, follow_redirects=False)

    def user(self, **where):
        (k, v), = where.items()
        with db.connect() as conn:
            return conn.execute(f"SELECT * FROM users WHERE {k}=?", (v,)).fetchone()

    def test_new_account_then_return(self):
        c = TestClient(app)
        r = self.sign_in(c, "g-100", "Gina@Example.com")
        self.assertEqual(r.headers["location"], "/studio?signed=new")
        me = c.get("/api/me").json()["user"]
        self.assertEqual((me["email"], me["google"]), ("gina@example.com", True))
        self.assertEqual(self.user(google_sub="g-100")["pw_hash"], "")
        c2 = TestClient(app)                                     # Google keeps the id when the address changes
        self.assertEqual(self.sign_in(c2, "g-100", "gina.new@example.com").headers["location"], "/studio?signed=in")
        self.assertEqual(c2.get("/api/me").json()["user"]["email"], "gina@example.com")
        self.assertEqual(c.post("/api/login", json={"email": "gina@example.com", "password": "any password"}).status_code, 401)   # no password matches a Google-only account

    def test_links_password_account(self):
        new_client("both@example.com")
        c = TestClient(app)
        self.assertEqual(self.sign_in(c, "g-200", "both@example.com").headers["location"], "/studio?signed=in")
        self.assertEqual(self.user(email="both@example.com")["google_sub"], "g-200")
        self.assertEqual(TestClient(app).post("/api/login", json={"email": "both@example.com", "password": "correct horse"}).status_code, 200)
        r = self.sign_in(TestClient(app), "g-other", "both@example.com")           # a second Google account, same email
        self.assertEqual(r.headers["location"], "/studio?auth=taken")

    def test_invite_link(self):
        object.__setattr__(self.settings, "invite_only", True)
        with db.connect() as conn:
            conn.execute("INSERT INTO invites (code, max_uses, created) VALUES ('PAWS-GOOG01', 1, 0)")
        c = TestClient(app)
        self.assertEqual(self.sign_in(c, "g-300", "inv@example.com", invite="paws-goog01").headers["location"], "/studio?signed=new")
        self.assertEqual(c.get("/api/me").json()["user"]["email"], "inv@example.com")
        with db.connect() as conn:
            self.assertEqual(conn.execute("SELECT uses FROM invites WHERE code='PAWS-GOOG01'").fetchone()["uses"], 1)

    def test_invite_step(self):
        object.__setattr__(self.settings, "invite_only", True)
        with db.connect() as conn:
            conn.execute("INSERT INTO invites (code, max_uses, created) VALUES ('PAWS-GOOG02', 1, 0)")
        c = TestClient(app)
        self.assertEqual(self.sign_in(c, "g-400", "step@example.com").headers["location"], "/studio?google=invite")
        me = c.get("/api/me").json()
        self.assertEqual((me["user"], me["pending_google"]), (None, "step@example.com"))
        self.assertEqual(c.post("/api/google/finish", json={"invite": "WRONG"}).status_code, 403)
        self.assertEqual(c.post("/api/google/finish", json={"invite": "paws-goog02"}).status_code, 200)
        me = c.get("/api/me").json()
        self.assertEqual((me["user"]["email"], me["pending_google"]), ("step@example.com", None))
        self.assertEqual(self.user(email="step@example.com")["google_sub"], "g-400")
        self.assertEqual(c.post("/api/google/finish", json={"invite": "paws-goog02"}).status_code, 400)
        self.assertEqual(TestClient(app).post("/api/google/finish", json={"invite": "x"}).status_code, 400)  # no cookie

    def test_waitlist_step(self):
        object.__setattr__(self.settings, "invite_only", True)
        c = TestClient(app)
        self.sign_in(c, "g-500", "later@example.com")
        r = c.post("/api/google/waitlist", json={})
        self.assertEqual(r.json(), {"ok": True, "email": "later@example.com"})
        with db.connect() as conn:
            self.assertEqual(conn.execute("SELECT source FROM waitlist WHERE email='later@example.com'").fetchone()["source"], "google")
        self.assertIsNone(c.get("/api/me").json()["pending_google"])
        self.assertIsNone(self.user(email="later@example.com"))

    def test_refusals(self):
        c = TestClient(app)
        self.assertEqual(self.sign_in(c, "g-600", "a@example.com", state="forged").headers["location"], "/studio?auth=state")
        self.assertEqual(self.sign_in(c, "g-600", "a@example.com", nonce="replayed").headers["location"], "/studio?auth=state")
        self.assertEqual(self.sign_in(c, "g-600", "a@example.com", verified=False).headers["location"], "/studio?auth=unverified")
        r = c.get("/auth/google/callback", params={"error": "access_denied"}, follow_redirects=False)
        self.assertEqual(r.headers["location"], "/studio?auth=cancelled")
        r = TestClient(app).get("/auth/google/callback", params={"code": "x", "state": "y"}, follow_redirects=False)
        self.assertEqual(r.headers["location"], "/studio?auth=state")              # never started here
        self.assertIsNone(self.user(google_sub="g-600"))
        self.assertIsNone(c.get("/api/me").json()["user"])

    def test_claims_are_checked(self):
        good = {"iss": "accounts.google.com", "aud": self.CID, "exp": time.time() + 60, "nonce": "n", "sub": "1",
                "email": "X@example.com", "email_verified": True}
        self.assertEqual(google.check(good, "n"), {"sub": "1", "email": "x@example.com"})
        for bad, key in ((dict(good, aud="someone-else"), "failed"), (dict(good, iss="https://evil.example"), "failed"),
                         (dict(good, exp=time.time() - 1), "failed"), (dict(good, email_verified="true"), "unverified")):
            with self.assertRaises(google.GoogleError) as e:
                google.check(bad, "n")
            self.assertEqual(str(e.exception), key)

    def test_off_when_not_set_up(self):
        object.__setattr__(self.settings, "google_client_secret", "")
        c = TestClient(app)
        self.assertEqual(c.get("/auth/google/start", follow_redirects=False).status_code, 404)
        self.assertFalse(c.get("/api/me").json()["google"])


def signed(payload: bytes, secret="whsec_test_dummy"):
    t = str(int(time.time()))
    sig = hmac.new(secret.encode(), f"{t}.".encode() + payload, hashlib.sha256).hexdigest()
    return f"t={t},v1={sig}"


class Billing(unittest.TestCase):
    def user_with_customer(self, email, customer):
        new_client(email)
        with db.connect() as c:
            c.execute("UPDATE users SET stripe_customer=? WHERE email=?", (customer, email))

    def me(self, email):
        with db.connect() as c:
            return c.execute("SELECT plan, credits FROM users WHERE email=?", (email,)).fetchone()

    def event(self, eid, kind, obj):
        return {"id": eid, "type": kind, "data": {"object": obj}}

    def test_subscription_lifecycle(self):
        self.user_with_customer("sub@example.com", "cus_sub")
        sub = {"id": "sub_1", "customer": "cus_sub", "status": "active"}
        self.assertEqual(billing.apply_event(self.event("evt_s1", "customer.subscription.created", sub)), "plan pro")
        self.assertEqual(self.me("sub@example.com")["plan"], "pro")
        billing.apply_event(self.event("evt_s2", "customer.subscription.updated", dict(sub, status="past_due")))
        self.assertEqual(self.me("sub@example.com")["plan"], "free")
        billing.apply_event(self.event("evt_s3", "customer.subscription.updated", dict(sub, status="trialing")))
        self.assertEqual(self.me("sub@example.com")["plan"], "pro")
        billing.apply_event(self.event("evt_s4", "customer.subscription.deleted", dict(sub, status="canceled")))
        self.assertEqual(self.me("sub@example.com")["plan"], "free")

    def test_credit_pack_is_granted_once(self):
        self.user_with_customer("pack@example.com", "cus_pack")
        sess = {"id": "cs_1", "customer": "cus_pack", "mode": "payment", "payment_status": "unpaid"}
        self.assertEqual(billing.apply_event(self.event("evt_p1", "checkout.session.completed", sess)), "waiting")
        self.assertEqual(self.me("pack@example.com")["credits"], 0)
        paid = dict(sess, payment_status="paid")
        self.assertEqual(billing.apply_event(self.event("evt_p2", "checkout.session.async_payment_succeeded", paid)), "credits +20")
        self.assertEqual(billing.apply_event(self.event("evt_p2", "checkout.session.async_payment_succeeded", paid)), "duplicate")
        self.assertEqual(billing.apply_event(self.event("evt_p3", "checkout.session.completed", paid)), "already fulfilled")
        self.assertEqual(self.me("pack@example.com")["credits"], 20)

    def test_subscription_checkout_does_not_grant_by_itself(self):
        self.user_with_customer("subco@example.com", "cus_subco")
        sess = {"id": "cs_2", "customer": "cus_subco", "mode": "subscription", "payment_status": "paid"}
        self.assertEqual(billing.apply_event(self.event("evt_c1", "checkout.session.completed", sess)), "waiting")
        self.assertEqual(self.me("subco@example.com")["plan"], "free")

    def test_webhook_signature(self):
        self.user_with_customer("hook@example.com", "cus_hook")
        body = json.dumps(self.event("evt_h1", "customer.subscription.created",
                                     {"id": "sub_h", "object": "subscription", "customer": "cus_hook", "status": "active"})).encode()
        c = TestClient(app)
        bad = c.post("/api/billing/webhook", content=body, headers={"stripe-signature": signed(body, "whsec_wrong"), "content-type": "application/json"})
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(self.me("hook@example.com")["plan"], "free")
        ok = c.post("/api/billing/webhook", content=body, headers={"stripe-signature": signed(body), "content-type": "application/json"})
        self.assertEqual(ok.status_code, 200, ok.text)
        self.assertEqual(self.me("hook@example.com")["plan"], "pro")

    def test_checkout_refusals(self):
        self.assertEqual(TestClient(app).post("/api/billing/checkout", json={"kind": "pro"}).status_code, 401)
        c = new_client("already@example.com", plan="pro")
        self.assertEqual(c.post("/api/billing/checkout", json={"kind": "pro"}).status_code, 409)
        self.assertEqual(c.post("/api/billing/checkout", json={"kind": "gold"}).status_code, 400)


if __name__ == "__main__":
    unittest.main()
