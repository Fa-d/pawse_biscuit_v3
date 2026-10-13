# Pawse Studio web app

The paid sticker studio: describe a moment, edit it with chips, download it. FastAPI and SQLite on the server; plain
HTML, CSS and JavaScript in the browser (no build step), with lottie-web playing the live preview. How each sticker
decision is made is in `../studio/PIPELINE.md`.

## Run it locally

```
cd rig
python3 -m venv .venv && .venv/bin/pip install -r studio/requirements.txt -r app/requirements.txt
STUDIO_DEV=1 .venv/bin/uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000 for the landing page and http://localhost:8000/studio for the studio. With `STUDIO_DEV=1`, the account dialog has buttons to switch your own plan (Pro, 3 credits,
free) without paying, and the API docs are at `/api/docs`. Never set it in production.

## Settings

Everything comes from environment variables. Keep the Stripe values in your host's secrets vault, never in the
repository.

| Variable | Default | What it does |
| --- | --- | --- |
| `STUDIO_BASE_URL` | `http://localhost:8000` | Public address; used for Stripe return links. `https://` also turns on secure cookies |
| `STUDIO_DB` | `app/data/studio.db` | SQLite file |
| `STUDIO_DEV` | off | Development helpers (plan switcher, API docs) |
| `STUDIO_LLM` | off | Lets signed-in users' unclear prompts reach Claude Haiku (needs Anthropic credentials) |
| `STUDIO_LLM_DAILY` | 20 | Model calls per user per day |
| `FREE_DAILY_EXPORTS` | 5 | Free PNG or WebP downloads a day |
| `PACK_CREDITS` | 20 | Credits in one pack |
| `STRIPE_API_KEY` | none | A restricted key (`rk_…`), see below |
| `STRIPE_WEBHOOK_SECRET` | none | Signing secret of the webhook endpoint (`whsec_…`) |
| `STRIPE_PRICE_PRO` | none | Recurring monthly Price id for Pro |
| `STRIPE_PRICE_PACK` | none | One-time Price id for a credit pack |
| `PRICE_PRO_LABEL`, `PRICE_PACK_LABEL` | `$4.99 a month`, `$2.99` | What the pricing panel says; keep in step with the Stripe prices |
| `STUDIO_ORIGIN_KEY` | none | When set, requests without a matching `X-Origin-Key` header get 404, so only the Cloudflare Worker can reach the app |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | none | Sign in with Google (an OAuth "Web application" client). Without both, the studio shows only the email form |
| `TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET` | none | Cloudflare Turnstile on signup, waitlist, feedback and password reset. Without both, no check |
| `STUDIO_RATE_LIMITS` | on | Per-address and per-account limits on making stickers; tests turn it off |
| `STUDIO_INVITE_ONLY` | off | Beta: signing up needs an invite code, and the landing page shows a waitlist |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` | none, 587 | Your email provider's SMTP server. Without `SMTP_HOST`, emails are written to `outbox/` next to the database instead of being sent |
| `SMTP_SECURITY` | `starttls` | `starttls`, `ssl` (port 465) or `none` |
| `MAIL_FROM` | `Pawse Studio <hello@localhost>` | Sender of password resets and invites; use an address on a domain your provider has verified |
| `CONTACT_EMAIL` | none | Shown on the landing page (brand mascots) and the privacy page; empty hides those lines |

Payments stay switched off, and the buy buttons explain that, until all four Stripe values are set.

## Setting up Stripe

1. Work in a Stripe sandbox first (`stripe sandbox create` with the Stripe CLI gives you test keys without signing up).
2. Create two Products: **Pro** with a monthly recurring Price, and **Credit pack** with a one-time Price. Separate
   Products keep their names apart on receipts.
3. Create a **restricted key** with write access to Customers, Checkout Sessions and Customer Portal sessions only.
   Use it as `STRIPE_API_KEY`.
4. Turn on the Customer Portal in the Dashboard (Settings → Billing → Customer portal), so Pro members can cancel or
   change their card themselves.
5. Add a webhook endpoint at `https://<your domain>/api/billing/webhook` for these events:
   `checkout.session.completed`, `checkout.session.async_payment_succeeded`, `checkout.session.async_payment_failed`,
   `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.paid`,
   `invoice.payment_failed`. Its signing secret is `STRIPE_WEBHOOK_SECRET`.
   Locally: `stripe listen --forward-to localhost:8000/api/billing/webhook` prints a secret to use.
6. Tax: if you sell to customers in the US, EU or UK you may need to collect sales tax or VAT. Look at Stripe Tax
   before launch. It only collects once you have an active registration, so turning it on alone isn't enough.

Plans and credits change only from these signed webhook events, never from the page Stripe sends people back to.

## Security

Previews are pictures drawn on the server; the browser never receives Lottie. The full list of protections, and
where each lives, is in `../DEPLOY.md` → Security.

## Sign in with Google

Google is the main way in; email and password stay behind "Use email instead". The flow is OpenID Connect with PKCE,
run on the server (`app/google.py`), so no Google script loads on our pages.

1. Google Cloud console → Google Auth Platform → Branding: app name, support email, home page, privacy page
   (`/privacy`), and your domain under authorized domains. Leave the logo empty to skip brand verification.
2. Audience: External, then **Publish app** (in Testing, only listed test users can sign in). The `openid` and
   `email` scopes need no review.
3. Clients → Create client → Web application. Redirect URI: `<STUDIO_BASE_URL>/auth/google/callback` (add
   `http://localhost:8000/auth/google/callback` for local runs).
4. Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.

A Google sign-in whose email already has an account links to it. In an invite-only beta, someone new without an
invite link is asked for a code, or can join the waitlist with one click.

## Running the beta

Set `STUDIO_INVITE_ONLY=1`. The landing page then collects emails for a waitlist, and signing up needs a code.

```
.venv/bin/python -m app.admin invite --uses 20 --note "design friends"   # one code for a group
.venv/bin/python -m app.admin waitlist                                   # who is waiting
.venv/bin/python -m app.admin invite-waitlist 25                         # email single-use codes to the next 25
.venv/bin/python -m app.admin report --days 7                            # funnel, words the rules missed, feedback
.venv/bin/python -m app.admin reset-link someone@example.com             # support: a reset link to send by hand
.venv/bin/python -m app.admin plan someone@example.com pro               # support: change a plan
.venv/bin/python -m app.admin credits someone@example.com 20             # support: add credits
```

The report lists the words people typed that the rules didn't understand. Adding them to
`studio/parse/lexicon.yaml` is the main way the studio gets better during the beta. "Not what you meant?" reports
from the studio show up there too.

Only daily totals are counted (`events` table: signups, prompts, downloads by format, packs, checkouts). They hold no
user ids and no prompt text.

## Pages

| Path | What it is |
| --- | --- |
| `/` | Landing page: live examples made by the engine, how it works, mascots, pricing, questions, waitlist in beta |
| `/studio` | The studio. `?invite=CODE` opens signup with the code filled in; `?reset=TOKEN` opens the new-password form |
| `/privacy` | Privacy page, written from what the code stores. **Have it reviewed before launch.** There is no terms page yet |

## Checks

```
.venv/bin/python -m unittest app.tests.test_app -v          # accounts, gates, credits, watermark, packs, webhooks
STUDIO_DEV=1 .venv/bin/uvicorn app.main:app --port 8765 &
.venv/bin/python -m app.tests.e2e http://localhost:8765 out/e2e   # a real Chrome walks landing → studio → packs, screenshots per step
```

## Running it for real

The live beta runs on Google Cloud Run behind a Cloudflare Worker; how to ship and change it is in `../DEPLOY.md`.

- One machine is fine to start: `uvicorn app.main:app --workers 2 --host 0.0.0.0 --port 8000` behind HTTPS (Fly.io,
  Render or a small VPS with Caddy). Each worker keeps its own preview cache; composing is CPU work, so give it cores.
- Back up `STUDIO_DB` daily. Move to Postgres when one machine is no longer enough.
- The login, reset-email, waitlist and feedback limits are kept in memory per worker. Use a shared store such as
  Redis if you run many workers.
- Email deliverability: set up SPF and DKIM for the `MAIL_FROM` domain with your provider, or resets and invites
  land in spam.
