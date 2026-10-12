# Deploying Pawse Studio

```
visitor ─► stickers.liveintently.app ─► Cloudflare Worker pawse-stickers-front ─► Cloud Run pawse-studio ─► D1 (REST)
            (Cloudflare custom domain)     cloudflare/src/proxy.js                 Google project think-fast-62678
```

| Piece | Where | Notes |
| --- | --- | --- |
| App | Cloud Run service `pawse-studio`, region `us-central1` | 2 vCPU / 2 GiB, scales to zero, at most 2 instances, 8 requests per instance |
| Image | `us-central1-docker.pkg.dev/think-fast-62678/pawse/studio:<tag>` | Built by Cloud Build from `rig/` (the `Dockerfile`; `.gcloudignore` decides what is uploaded) |
| Database | Cloudflare D1 `d6c84803-8d51-4c8d-b986-ac46e13b5455`, over the REST API | `STUDIO_D1=rest:<account>/<db>`; Cloud Run has no lasting disk, so SQLite files would vanish |
| Secrets | Secret Manager: `cloudflare-d1-token`, `studio-origin-key`, `google-client-secret` | Read only by the service account `pawse-studio@think-fast-62678.iam.gserviceaccount.com` |
| Front door | Worker `pawse-stickers-front` (`cloudflare/wrangler.jsonc`) | Adds the visitor's IP (`X-Client-IP`) and the shared `X-Origin-Key`; the app answers 404 without that key |
| Cost guard | Billing budget "Pawse Studio guard", $5 a month | Emails at 50%, 90% and 100% |

Google sign-in: OAuth client "Pawse Studio web" in the same Google project (Google Auth Platform → Clients), with the
redirect URI `https://stickers.liveintently.app/auth/google/callback`. Its id is the `GOOGLE_CLIENT_ID` env var; its
secret is `google-client-secret`.

Settings on the service: `STUDIO_INVITE_ONLY=1`, `STUDIO_BASE_URL=https://stickers.liveintently.app`,
`STUDIO_BEHIND_CLOUDFLARE=1`, and `STUDIO_D1` plus the two secrets. Stripe and SMTP are not set yet: payments stay off
and emails are written to the server's temporary outbox (lost on restart), so send invite codes by hand for now.

## Ship a new version

```
cd rig
gcloud builds submit --tag us-central1-docker.pkg.dev/think-fast-62678/pawse/studio:vN --machine-type=e2-highcpu-8 .
gcloud run deploy pawse-studio --image=us-central1-docker.pkg.dev/think-fast-62678/pawse/studio:vN --region=us-central1
```

Roll back: `gcloud run services update-traffic pawse-studio --region=us-central1 --to-revisions=<older revision>=100`
(`gcloud run revisions list --service=pawse-studio --region=us-central1` lists them).

The front door only changes when `cloudflare/` does: `cd cloudflare && npx wrangler deploy`.

## Change a setting or secret

```
gcloud run services update pawse-studio --region=us-central1 --update-env-vars=FREE_DAILY_EXPORTS=10
printf '%s' "$NEW_VALUE" | gcloud secrets versions add cloudflare-d1-token --data-file=-   # then redeploy to pick it up
```

Turning on payments: put the four Stripe values in Secret Manager the same way, add them with `--update-secrets`, and
point the Stripe webhook at `https://stickers.liveintently.app/api/billing/webhook` (see `app/README.md`).

**To do: a D1-only token.** The server currently uses the same Cloudflare token as the laptop, which can also deploy
Workers. Make a token with only *Account → D1 → Edit* in the Cloudflare dashboard (My Profile → API Tokens), add it
as a new version of `cloudflare-d1-token`, and redeploy.

**Changing the origin key:** add a new version of `studio-origin-key`, redeploy the service, then
`cd cloudflare && npx wrangler secret put ORIGIN_KEY` with the same value. The site returns 404 between those two steps.

## Running the beta against the live database

The admin tool talks to D1 directly from your laptop:

```
export STUDIO_D1=rest:fae059b7b66e7a56172c1542b32f43d5/d6c84803-8d51-4c8d-b986-ac46e13b5455   # plus CLOUDFLARE_API_TOKEN
.venv/bin/python -m app.admin invite --uses 20 --note "design friends"
.venv/bin/python -m app.admin report --days 7
```

Logs: `gcloud run services logs read pawse-studio --region=us-central1 --limit=100`.

## Limits to know

- D1's REST API allows about 1,200 requests per 5 minutes per account, and each page action makes a few of them. That
  is plenty for an invite-only beta. Before a public launch, move the database next to the app.
- A cold start (the first visit after about 15 quiet minutes) takes about 6 seconds. `--min-instances=1` removes it, but
  an always-on instance uses up the free tier.
- Login and email limits are counted per instance, so with 2 instances someone could get up to twice the limit.
