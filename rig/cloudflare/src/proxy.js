// Pawse Studio: this Worker answers stickers.liveintently.app and forwards every request to the app on Google Cloud
// Run (UPSTREAM).  The visitor's address travels in X-Client-IP, because Cloud Run would otherwise only see Cloudflare's.
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const upstream = new URL(url.pathname + url.search, env.UPSTREAM);
    const headers = new Headers(request.headers);
    headers.set("X-Client-IP", request.headers.get("CF-Connecting-IP") || "");
    headers.set("X-Forwarded-Host", url.host);
    headers.set("X-Forwarded-Proto", "https");
    headers.set("X-Origin-Key", env.ORIGIN_KEY || "");      // the app refuses requests without it (STUDIO_ORIGIN_KEY)
    headers.delete("Host");
    const init = { method: request.method, headers, redirect: "manual" };
    if (request.method !== "GET" && request.method !== "HEAD") init.body = request.body;
    return fetch(upstream, init);
  },
};
