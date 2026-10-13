// The human check on forms (Cloudflare Turnstile), shared by the studio and the landing page.
// Off until setKey() gets a site key from /api/me; then each form's .human box gets a widget that usually needs no
// clicks ("interaction-only") and works while the person types, so the token is ready by the time they submit.
"use strict";

const Human = (() => {
  let key = "";
  let loading = null;
  const widgets = new Map();

  function load() {
    loading ||= new Promise((resolve, reject) => {
      const s = Object.assign(document.createElement("script"),
        { src: "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit", async: true });
      s.onload = () => resolve(window.turnstile);
      s.onerror = () => { loading = null; reject(new Error("The human check couldn't load. Check your connection and try again.")); };
      document.head.append(s);
    });
    return loading;
  }

  async function prepare(box) {
    if (!key || !box || widgets.has(box)) return;
    const ts = await load();
    if (!widgets.has(box)) widgets.set(box, ts.render(box, { sitekey: key, appearance: "interaction-only", size: "flexible" }));
  }

  // The one-time token to send with a form ("" when the check is off). Waits up to 15 s for a check still running.
  async function token(box) {
    if (!key) return "";
    await prepare(box);
    const id = widgets.get(box);
    for (let i = 0; i < 60; i++) {
      const t = window.turnstile.getResponse(id);
      if (t) return t;
      await new Promise((r) => setTimeout(r, 250));
    }
    return "";
  }

  // Tokens work once: after each submit, get a fresh one ready.
  function reset(box) {
    const id = widgets.get(box);
    if (id !== undefined && window.turnstile) window.turnstile.reset(id);
  }

  return { setKey: (k) => { key = k || ""; }, prepare: (box) => prepare(box).catch(() => {}), token, reset };
})();
