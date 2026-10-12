// Pawse Studio on Cloudflare: this Worker answers stickers.liveintently.app and hands every request to the Python
// app running in a Cloudflare Container.  The app keeps its data in D1: it sends SQL to http://d1.internal, which never
// leaves the machine. The container's outbound request is intercepted here and run on the D1 binding.
import { Container, ContainerProxy, getContainer } from "@cloudflare/containers";

export { ContainerProxy };            // required for outbound interception

// POST /query {sql, params} -> {results, changes, last_row_id}     POST /exec {sql} -> {ok}
async function d1Proxy(request, env) {
  if (request.method !== "POST") return Response.json({ error: "POST only" }, { status: 405 });
  try {
    const url = new URL(request.url);
    const body = await request.json();
    if (url.pathname === "/exec") {
      // several statements (the schema): run them as one batch, one prepared statement each
      const statements = body.sql.split(";").map((s) => s.trim()).filter(Boolean);
      await env.DB.batch(statements.map((s) => env.DB.prepare(s)));
      return Response.json({ ok: true });
    }
    const result = await env.DB.prepare(body.sql).bind(...(body.params || [])).all();
    return Response.json({
      results: result.results ?? [],
      changes: result.meta?.changes ?? 0,
      last_row_id: result.meta?.last_row_id ?? null,
    });
  } catch (err) {
    return Response.json({ error: String(err?.message || err) }, { status: 500 });
  }
}

export class StickerStudio extends Container {
  defaultPort = 8000;               // uvicorn in the Dockerfile
  sleepAfter = "20m";               // stop after 20 idle minutes; the next visitor wakes it (a few seconds)
  enableInternet = true;            // for SMTP, Stripe and Anthropic once they are configured

  static outboundByHost = { "d1.internal": d1Proxy };

  constructor(ctx, env) {
    super(ctx, env);
    this.envVars = {
      STUDIO_D1: "proxy:http://d1.internal",
      STUDIO_BASE_URL: env.BASE_URL,
      STUDIO_INVITE_ONLY: env.INVITE_ONLY,
      STUDIO_BEHIND_CLOUDFLARE: "1",
      FREE_DAILY_EXPORTS: env.FREE_DAILY_EXPORTS,
      PACK_CREDITS: env.PACK_CREDITS,
      CONTACT_EMAIL: env.CONTACT_EMAIL ?? "",
      ...(env.MAIL_FROM ? { MAIL_FROM: env.MAIL_FROM } : {}),
      // Secrets (set with `wrangler secret put`) reach the app only once they exist.
      ...(env.SMTP_HOST ? { SMTP_HOST: env.SMTP_HOST, SMTP_PORT: env.SMTP_PORT ?? "587", SMTP_USER: env.SMTP_USER ?? "",
                            SMTP_PASSWORD: env.SMTP_PASSWORD ?? "" } : {}),
      ...(env.STRIPE_API_KEY ? { STRIPE_API_KEY: env.STRIPE_API_KEY, STRIPE_WEBHOOK_SECRET: env.STRIPE_WEBHOOK_SECRET ?? "",
                                 STRIPE_PRICE_PRO: env.STRIPE_PRICE_PRO ?? "", STRIPE_PRICE_PACK: env.STRIPE_PRICE_PACK ?? "" } : {}),
    };
  }
}

export default {
  async fetch(request, env) {
    // One instance holds the in-memory preview cache; all lasting data is in D1, so a restart loses nothing.
    return getContainer(env.STUDIO, "main").fetch(request);
  },
};
