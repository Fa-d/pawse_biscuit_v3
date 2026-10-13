// Pawse Studio editor. The spec object is the single source of truth: the prompt fills it, chips change it,
// and every change asks the server for a new preview: a picture (animated WebP, or a PNG still with reduced motion)
// drawn on the server, so the sticker's vector source never reaches the browser.
"use strict";

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
const el = (tag, props = {}, ...kids) => {
  const n = Object.assign(document.createElement(tag), props);
  for (const k of kids) n.append(k);
  return n;
};
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const FORMATS = [
  { id: "png", label: "PNG", sub: "Still" },
  { id: "webp", label: "WebP", sub: "Still" },
  { id: "tgs", label: "Telegram", sub: "Animated" },
  { id: "awebp", label: "WhatsApp", sub: "Animated" },
  { id: "gif", label: "GIF", sub: "Animated" },
  { id: "json", label: "Lottie", sub: "For apps" },
];

const state = { vocab: null, me: null, spec: null, prompt: "", anim: null, seq: 0, captionOpts: { style: "outline", pos: "bottom" },
  invite: "", resetToken: "", emailOpen: false };

// ---------------------------------------------------------------- server
async function api(method, path, body) {
  const res = await fetch(path, {
    method,
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    credentials: "same-origin",
  });
  if (!res.ok) {
    let msg = `Something went wrong (${res.status}). Try again.`;
    try { const j = await res.json(); if (j.detail) msg = typeof j.detail === "string" ? j.detail : "Check what you entered and try again."; } catch (_) { /* not JSON */ }
    const err = new Error(msg);
    err.status = res.status;
    throw err;
  }
  return res;
}
const getJSON = async (path) => (await api("GET", path)).json();
const postJSON = async (path, body) => (await api("POST", path, body)).json();

let toastTimer;
function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("show"), 4200);
}

// ---------------------------------------------------------------- start
async function start() {
  const [vocab, me] = await Promise.all([getJSON("/api/vocab"), getJSON("/api/me")]);
  state.vocab = vocab;
  state.me = me;
  Human.setKey(me.turnstile);
  buildIdeas();
  buildEditor();
  renderAccount();
  renderDownloads();
  bindUI();

  const q = new URLSearchParams(location.search);
  if (q.get("invite")) state.invite = q.get("invite");
  if (q.get("reset")) state.resetToken = q.get("reset");
  const authErr = q.get("auth"), signed = q.get("signed");
  if (q.get("invite") || q.get("reset") || authErr || signed || q.get("google")) history.replaceState(null, "", "/studio");
  if (state.resetToken) {
    showAccountView("reset");
    $("#account-dialog").showModal();
  } else if (!me.user && me.pending_google) {
    openAccount();                                         // signed in with Google, still needs an invite code
  } else if (authErr && !me.user) {
    openAccount("signin");
    $("#google-error").textContent = GOOGLE_ERRORS[authErr] || GOOGLE_ERRORS.failed;
  } else if (state.invite && !me.user) {
    openAccount("signup", "Welcome to the beta. Create your account to start.");
  }
  if (signed && me.user) toast(signed === "new" ? "Account created. You're signed in." : "Signed in.");
  if (q.get("paid")) {
    toast(q.get("paid") === "pro" ? "Payment received. Pro switches on in a few seconds." : "Payment received. Your credits arrive in a few seconds.");
    history.replaceState(null, "", "/studio");
    setTimeout(refreshMe, 2500);
    setTimeout(refreshMe, 7000);
  } else if (q.get("cancelled")) {
    history.replaceState(null, "", "/studio");
  }
  const first = vocab.ideas[Math.floor(Math.random() * vocab.ideas.length)];
  $("#prompt").value = first.prompt;
  makeFromPrompt();
}

async function refreshMe() {
  const before = JSON.stringify(state.me && state.me.user);
  state.me = await getJSON("/api/me");
  renderAccount();
  renderDownloads();
  if (JSON.stringify(state.me.user) !== before) schedulePreview(0);
}

// ---------------------------------------------------------------- prompt
function buildIdeas() {
  const box = $("#ideas");
  const picks = ["good morning", "happy birthday", "thank you", "on my way", "busy", "weekend", "love you", "bad day"];
  const ideas = state.vocab.ideas.filter((i) => picks.includes(i.prompt));
  for (const idea of (ideas.length ? ideas : state.vocab.ideas.slice(0, 8))) {
    box.append(el("button", { type: "button", textContent: idea.prompt, onclick: () => { $("#prompt").value = idea.prompt; makeFromPrompt(); } }));
  }
}

async function makeFromPrompt() {
  const prompt = $("#prompt").value.trim();
  if (!prompt) { $("#prompt").focus(); return; }
  state.prompt = prompt;
  $("#make").disabled = true;
  try {
    const r = await postJSON("/api/parse", { prompt });
    renderUnderstood(r);
    setSpec(r.spec);
  } catch (e) {
    toast(e.message);
  } finally {
    $("#make").disabled = false;
  }
}

const SECTION_WORD = { template: "scenario", moods: "mood", actions: "movement", props: "holding", effects: "around it",
  accessories: "wearing", poses: "pose", colours: "colour", bases: "mascot", strong: "stronger", weak: "softer" };

function renderUnderstood(r) {
  const box = $("#understood");
  box.replaceChildren();
  const line = el("p");
  if (r.understood.length) {
    line.append("Understood ");
    r.understood.forEach((m, i) => {
      if (i) line.append(", ");
      const word = m.negated || m.dropped ? el("s", { textContent: m.phrase }) : el("mark", { textContent: m.phrase });
      line.append(word, ` as ${SECTION_WORD[m.as] || m.as}`);
    });
    line.append(".");
    box.append(line);
  }
  if (r.unknown.length) {
    box.append(el("p", { className: "unsure", textContent: `Didn't use: ${r.unknown.join(", ")}.` }));
  }
  for (const note of r.notes || []) {
    box.append(el("p", { className: "unsure", textContent: `${note.charAt(0).toUpperCase()}${note.slice(1)}.` }));
  }
  if (!r.confident) {
    box.append(el("p", { className: "unsure", textContent: "Not sure what you meant, so here's a friendly default. Try other words, or pick from the options below." }));
  }
  box.hidden = !box.childElementCount;
}

// ---------------------------------------------------------------- editor
function chip(item, pressed, onclick) {
  return el("button", { type: "button", textContent: item.label, onclick, ariaPressed: String(pressed) });
}

function buildEditor() {
  for (const group of $$("#editor .group[data-slot]")) {
    const slot = group.dataset.slot;
    if (slot === "colour") continue;
    const box = $(".chips", group);
    for (const item of state.vocab[slot]) {
      const b = chip(item, false, () => onChip(slot, item.id, box.dataset.kind, Number(group.dataset.max || 0)));
      b.dataset.id = item.id;
      box.append(b);
    }
  }
  const sw = $("#editor .swatches");
  for (const c of state.vocab.colours) {
    const b = el("button", { type: "button", ariaLabel: c.label, title: c.label, ariaPressed: "false" });
    b.dataset.id = c.id;
    if (c.hex) b.style.setProperty("--sw", c.hex);
    b.onclick = () => { state.spec.palette = c.palette ? { ...c.palette } : {}; changed(); };
    sw.append(b);
  }
  for (const slot of ["caption_style", "caption_pos"]) {
    const box = $(`.chips[data-slot="${slot}"]`);
    for (const item of state.vocab[slot]) {
      const b = chip(item, false, () => {
        state.captionOpts[slot === "caption_style" ? "style" : "pos"] = item.id;
        if (state.spec.caption) state.spec.caption = captionFromInput();
        changed();
      });
      b.dataset.id = item.id;
      box.append(b);
    }
  }
}

function onChip(slot, id, kind, max) {
  const s = state.spec;
  if (kind === "single") {
    s[slot] = id;
  } else {
    const list = s[slot];
    const at = list.indexOf(id);
    if (at >= 0) list.splice(at, 1);
    else if (list.length >= max) { toast(`Pick up to ${max}. Tap one to remove it first.`); return; }
    else list.push(id);
  }
  changed();
}

function captionFromInput() {
  const text = $("#caption").value.trim();
  return text ? { text, style: state.captionOpts.style, pos: state.captionOpts.pos } : null;
}

function setSpec(spec) {
  state.spec = spec;
  if (spec.caption) state.captionOpts = { style: spec.caption.style, pos: spec.caption.pos };
  $("#caption").value = spec.caption ? spec.caption.text : "";
  $("#editor").hidden = false;
  syncEditor();
  schedulePreview(0);
}

function changed() {
  syncEditor();
  schedulePreview(180);
}

function syncEditor() {
  const s = state.spec;
  for (const group of $$("#editor .group[data-slot]")) {
    const slot = group.dataset.slot;
    if (slot === "colour") continue;
    const val = s[slot] ?? group.dataset.default;    // (a spec leaves out a yaw of 0: the group says what that means)
    for (const b of $$(".chips button", group)) {     // (ids are text in the page; a number in the spec, such as a yaw, is compared as text)
      b.ariaPressed = String(Array.isArray(val) ? val.includes(b.dataset.id) : String(val ?? "") === b.dataset.id);
    }
  }
  const pal = JSON.stringify(s.palette || {});
  for (const b of $$("#editor .swatches button")) {
    const c = state.vocab.colours.find((x) => x.id === b.dataset.id);
    b.ariaPressed = String(JSON.stringify(c.palette || {}) === pal);
  }
  for (const b of $$('.chips[data-slot="caption_style"] button')) b.ariaPressed = String(b.dataset.id === state.captionOpts.style);
  for (const b of $$('.chips[data-slot="caption_pos"] button')) b.ariaPressed = String(b.dataset.id === state.captionOpts.pos);
  $("#intensity").value = s.intensity;
  $("#seconds").value = s.seconds;
  $("#seconds-out").textContent = `${s.seconds} s`;
}

// ---------------------------------------------------------------- preview
let previewTimer;
function schedulePreview(wait) {
  clearTimeout(previewTimer);
  previewTimer = setTimeout(runPreview, wait);
}

async function runPreview() {
  if (!state.spec) return;
  const seq = ++state.seq;
  const stage = $("#stage");
  stage.classList.add("busy");
  $("#stage-state").textContent = "Making your sticker…";
  try {
    const res = await api("POST", "/api/preview", { spec: state.spec, kind: reduceMotion ? "still" : "anim" });
    const meta = JSON.parse(res.headers.get("X-Preview") || "{}");
    const blob = await res.blob();
    if (seq !== state.seq) return;                     // a newer change is already on its way
    show(blob, $("#sticker"), "Sticker preview");
    stage.classList.add("has-sticker");
    renderNotes(meta.notes || []);
    $("#open-report").hidden = false;
  } catch (e) {
    if (seq === state.seq) toast(e.message);
  } finally {
    if (seq === state.seq) stage.classList.remove("busy");
  }
}

// A picture in a box: a Blob from the server (its object URL is freed when replaced) or a URL.
function show(src, box, alt) {
  const old = box.querySelector("img");
  if (old && old.dataset.blob) URL.revokeObjectURL(old.src);
  const img = el("img", { alt, draggable: false, decoding: "async" });
  if (src instanceof Blob) { img.src = URL.createObjectURL(src); img.dataset.blob = "1"; } else img.src = src;
  box.replaceChildren(img);
}

function renderNotes(notes) {
  $("#notes").replaceChildren(...notes.map((n) => el("li", { textContent: n.charAt(0).toUpperCase() + n.slice(1) + "." })));
}

// ---------------------------------------------------------------- downloads
function renderDownloads() {
  const row = $("#download-row");
  row.replaceChildren();
  const user = state.me.user;
  for (const f of FORMATS) {
    const open = user && user.formats.includes(f.id);
    const locked = user && !open;
    const b = el("button", { type: "button", className: locked ? "locked" : "" },
      el("span", { className: "fmt", textContent: f.label }),
      el("span", { className: "sub", textContent: locked ? "Pro or credits" : f.sub }));
    b.onclick = () => download(f.id);
    row.append(b);
  }
  let hint = "Create a free account to download.";
  if (user) {
    if (user.plan === "pro") hint = "Pro: every format, no mark.";
    else if (user.credits > 0) hint = `${user.credits} credit${user.credits === 1 ? "" : "s"} left. Each download uses one, with no mark.`;
    else hint = `${user.free_left_today} free download${user.free_left_today === 1 ? "" : "s"} left today (PNG or WebP, with a small mark).`;
  }
  $("#downloads-hint").textContent = hint;
}

async function download(fmt) {
  const user = state.me.user;
  if (!user) { openAccount("signup", "Create a free account to download your sticker."); return; }
  if (!user.formats.includes(fmt)) { openPricing(); return; }
  try {
    const res = await api("POST", "/api/export", { spec: state.spec, format: fmt });
    saveBlob(await res.blob(), filenameFrom(res, `sticker.${fmt}`));
    const warn = res.headers.get("X-Sticker-Warning");
    if (warn) toast(`Downloaded, but it's ${warn}.`);
    refreshMe();
  } catch (e) {
    if (e.status === 403) openPricing(e.message); else toast(e.message);
  }
}

function filenameFrom(res, fallback) {
  const m = /filename="([^"]+)"/.exec(res.headers.get("Content-Disposition") || "");
  return m ? m[1] : fallback;
}

function saveBlob(blob, name) {
  const url = URL.createObjectURL(blob);
  const a = el("a", { href: url, download: name });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 4000);
}

// ---------------------------------------------------------------- account
let authMode = "signin";
const GOOGLE_ERRORS = {
  cancelled: "Google sign-in was cancelled.",
  state: "That sign-in took too long or started in another tab. Try again.",
  unverified: "Your Google account's email isn't verified, so it can't be used here.",
  taken: "That email is linked to a different Google account. Use that account, or sign in with your password.",
  failed: "Something went wrong signing in with Google. Try again.",
};

function showAccountView(view) {
  for (const v of ["out", "in", "forgot", "reset", "google", "delete"]) $(`#account-${v}`).hidden = v !== view;
  const box = $(`#account-${view} .human`);
  if (box && (view !== "out" || authMode === "signup")) Human.prepare(box);   // signing in needs no check
}

function openAccount(mode, lead) {
  const user = state.me.user;
  if (!user && state.me.pending_google) {
    $("#google-pending-email").textContent = state.me.pending_google;
    $('#google-invite-form [name="invite"]').value = state.invite;
    $("#google-invite-error").textContent = "";
    showAccountView("google");
  } else {
    showAccountView(user ? "in" : "out");
    if (!user) {
      setAuthMode(mode || "signin");
      if (lead) $("#account-lead").textContent = lead;
      $("#auth-error").textContent = "";
      $("#google-error").textContent = "";
      renderAuthChoices();
    }
  }
  if (!$("#account-dialog").open) $("#account-dialog").showModal();
}

// Google first when it is set up; the email form waits behind "Use email instead"
function renderAuthChoices() {
  const google = Boolean(state.me.google);
  $("#google-start").hidden = !google;
  $("#google-start").href = "/auth/google/start" + (state.invite ? `?invite=${encodeURIComponent(state.invite)}` : "");
  $("#email-toggle-line").hidden = !google || state.emailOpen;
  $("#email-auth").hidden = google && !state.emailOpen;
}

function setAuthMode(mode) {
  authMode = mode;
  const up = mode === "signup";
  if (up) Human.prepare($("#auth-form .human"));
  $("#account-title").textContent = up ? "Create a free account" : "Sign in";
  $("#account-lead").textContent = up ? `Free accounts download ${state.me.free_daily} stickers a day.` : "Download stickers and keep the ones you make.";
  $("#auth-submit").textContent = up ? "Create account" : "Sign in";
  $("#auth-switch-text").textContent = up ? "Have an account?" : "New here?";
  $("#auth-switch").textContent = up ? "Sign in" : "Create a free account";
  $('#auth-form [name="password"]').autocomplete = up ? "new-password" : "current-password";
  $("#invite-label").hidden = !(up && state.me.invite_only);
  $('#auth-form [name="invite"]').value = state.invite;
  $("#forgot-line").hidden = up;
  if (up && state.me.invite_only) $("#account-lead").textContent = "The studio is in beta. Enter the invite code from your email.";
}

function renderAccount() {
  const user = state.me.user;
  $("#open-account").textContent = user ? (user.plan === "pro" ? "Pro" : "Account") : "Sign in";
  $("#open-collection").hidden = !user;
  if (user) {
    const plan = user.plan === "pro" ? "Pro" : user.credits > 0 ? `Free, with ${user.credits} credits` : "Free";
    $("#account-summary").textContent = `${user.google ? "Signed in with Google as " : ""}${user.email}. Plan: ${plan}.`;
    $("#manage-billing").hidden = user.plan !== "pro";
  }
  $("#free-daily").textContent = state.me.free_daily;
  $("#pack-credits").textContent = state.me.pack_credits;
  $("#price-pro").textContent = state.me.price_pro;
  $("#price-pack").textContent = state.me.price_pack;
  renderDevTools();
}

function renderDevTools() {
  const old = $("#dev-tools");
  if (old) old.remove();
  if (!state.me.dev || !state.me.user) return;
  const box = el("div", { id: "dev-tools", className: "stack" }, el("p", { className: "dialog-lead", textContent: "Development only: switch plans without paying." }));
  for (const [label, body] of [["Make me Pro", { plan: "pro", credits: 0 }], ["Give me 3 credits", { plan: "free", credits: 3 }], ["Back to free", { plan: "free", credits: 0 }]]) {
    box.append(el("button", { type: "button", className: "secondary", textContent: label, onclick: async () => { await postJSON("/api/dev/plan", body); await refreshMe(); } }));
  }
  $("#account-in").append(box);
}

// ---------------------------------------------------------------- pricing
function openPricing(reason) {
  $("#pricing-error").textContent = reason || "";
  $("#pricing-dialog").showModal();
}

async function buy(kind) {
  if (!state.me.user) { $("#pricing-dialog").close(); openAccount("signup", "Create a free account first, then pick a plan."); return; }
  try {
    const r = await postJSON("/api/billing/checkout", { kind });
    location.assign(r.url);
  } catch (e) {
    $("#pricing-error").textContent = e.message;
  }
}

// ---------------------------------------------------------------- collection
async function openCollection() {
  const dlg = $("#collection-dialog");
  dlg.showModal();
  const user = state.me.user;
  const actions = $("#pack-actions");
  actions.replaceChildren();
  if (user.plan === "pro") {
    const name = el("input", { type: "text", value: "My stickers", maxLength: 60, id: "pack-name" });
    actions.append(
      el("label", {}, "Pack name", name),
      el("button", { type: "button", className: "secondary", textContent: "Telegram pack", onclick: () => downloadPack("telegram", true) }),
      el("button", { type: "button", className: "secondary", textContent: "WhatsApp pack, animated", onclick: () => downloadPack("whatsapp", true) }),
      el("button", { type: "button", className: "secondary", textContent: "WhatsApp pack, still", onclick: () => downloadPack("whatsapp", false) }));
  } else {
    actions.append(el("p", { textContent: "With Pro you can download your saved stickers (up to 30) as one pack for Telegram or WhatsApp." }));
  }
  const sheet = $("#sheet");
  sheet.replaceChildren();
  let items = [];
  try { items = await getJSON("/api/stickers"); } catch (e) { toast(e.message); }
  $("#sheet-empty").hidden = items.length > 0;
  for (const it of items) {
    const thumb = el("div", { className: "thumb", role: "img", ariaLabel: it.prompt || "Saved sticker" });
    const li = el("li", {}, thumb, el("div", { className: "row" },
      el("button", { type: "button", textContent: "Edit", onclick: () => { dlg.close(); $("#prompt").value = it.prompt; $("#understood").hidden = true; setSpec(it.spec); } }),
      el("button", { type: "button", textContent: "Delete", onclick: async () => {
        try { await api("DELETE", `/api/stickers/${it.id}`, {}); li.remove(); $("#sheet-empty").hidden = $$("#sheet li").length > 0; } catch (e) { toast(e.message); }
      } })));
    sheet.append(li);
  }
  for (const [i, it] of items.entries()) show(`/api/stickers/${it.id}/thumb.png`, $$("#sheet .thumb")[i], it.prompt || "Saved sticker");
}

async function downloadPack(platform, animated) {
  toast("Packing your stickers. This can take a minute.");
  try {
    const name = ($("#pack-name") && $("#pack-name").value.trim()) || "My stickers";
    const res = await api("POST", "/api/packs", { platform, animated, name });
    saveBlob(await res.blob(), filenameFrom(res, `${platform}-pack.zip`));
    toast("Pack downloaded. The steps to add it are inside the zip.");
  } catch (e) {
    toast(e.message);
  }
}

// ---------------------------------------------------------------- wiring
function bindUI() {
  $("#ask").addEventListener("submit", (e) => { e.preventDefault(); makeFromPrompt(); });
  let capTimer;
  $("#caption").addEventListener("input", () => {
    clearTimeout(capTimer);
    capTimer = setTimeout(() => { state.spec.caption = captionFromInput(); changed(); }, 350);
  });
  $("#intensity").addEventListener("change", (e) => { state.spec.intensity = Number(e.target.value); changed(); });
  $("#seconds").addEventListener("input", (e) => { $("#seconds-out").textContent = `${e.target.value} s`; });
  $("#seconds").addEventListener("change", (e) => { state.spec.seconds = Number(e.target.value); changed(); });
  $("#save").addEventListener("click", async () => {
    if (!state.me.user) { openAccount("signup", "Create a free account to keep your stickers."); return; }
    try { await postJSON("/api/stickers", { spec: state.spec, prompt: state.prompt }); toast("Saved to My stickers."); } catch (e) { toast(e.message); }
  });

  $("#open-account").addEventListener("click", () => openAccount());
  $("#open-pricing").addEventListener("click", () => openPricing());
  $("#open-collection").addEventListener("click", openCollection);
  $("#auth-switch").addEventListener("click", () => setAuthMode(authMode === "signin" ? "signup" : "signin"));
  $("#auth-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    $("#auth-error").textContent = "";
    try {
      const body = { email: f.get("email"), password: f.get("password") };
      if (authMode === "signup") {
        const box = $(".human", e.target);
        body.invite = f.get("invite") || "";
        body.turnstile = await Human.token(box);
        Human.reset(box);
      }
      await postJSON(authMode === "signup" ? "/api/signup" : "/api/login", body);
      $("#account-dialog").close();
      e.target.reset();
      await refreshMe();
      toast(authMode === "signup" ? "Account created. You're signed in." : "Signed in.");
    } catch (err) {
      $("#auth-error").textContent = err.message;
    }
  });
  $("#email-toggle").addEventListener("click", () => {
    state.emailOpen = true;
    renderAuthChoices();
    $('#auth-form [name="email"]').focus();
  });
  $("#google-invite-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    $("#google-invite-error").textContent = "";
    try {
      await postJSON("/api/google/finish", { invite: new FormData(e.target).get("invite") });
      $("#account-dialog").close();
      e.target.reset();
      await refreshMe();
      toast("Account created. You're signed in.");
    } catch (err) {
      $("#google-invite-error").textContent = err.message;
    }
  });
  $("#google-waitlist").addEventListener("click", async () => {
    try {
      const box = $("#account-google .human");
      const turnstile = await Human.token(box);
      Human.reset(box);
      const r = await postJSON("/api/google/waitlist", { turnstile });
      $("#account-dialog").close();
      await refreshMe();
      toast(`You're on the waitlist as ${r.email}. Your invite will come by email.`);
    } catch (err) {
      $("#google-invite-error").textContent = err.message;
    }
  });
  $("#delete-open").addEventListener("click", () => { $("#delete-error").textContent = ""; showAccountView("delete"); });
  $("#delete-back").addEventListener("click", () => showAccountView("in"));
  $("#delete-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      await postJSON("/api/account/delete", { email: new FormData(e.target).get("email") });
      e.target.reset();
      $("#account-dialog").close();
      await refreshMe();
      toast("Your account and everything in it is deleted.");
    } catch (err) {
      $("#delete-error").textContent = err.message;
    }
  });
  $("#forgot-open").addEventListener("click", () => { $("#forgot-error").textContent = ""; showAccountView("forgot"); });
  $("#forgot-back").addEventListener("click", () => showAccountView("out"));
  $("#forgot-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      const box = $(".human", e.target);
      const turnstile = await Human.token(box);
      Human.reset(box);
      await postJSON("/api/password/forgot", { email: new FormData(e.target).get("email"), turnstile });
      $("#forgot-error").textContent = "";
      e.target.replaceChildren(el("p", { textContent: "If that email has an account, the link is on its way. Check your inbox and spam folder." }));
    } catch (err) {
      $("#forgot-error").textContent = err.message;
    }
  });
  $("#reset-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      await postJSON("/api/password/reset", { token: state.resetToken, password: new FormData(e.target).get("password") });
      state.resetToken = "";
      $("#account-dialog").close();
      await refreshMe();
      toast("Password changed. You're signed in.");
    } catch (err) {
      $("#reset-error").textContent = err.message;
    }
  });
  $("#open-report").addEventListener("click", () => { $("#report-dialog").showModal(); Human.prepare($("#report-form .human")); });
  $("#report-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    try {
      const box = $(".human", e.target);
      const turnstile = await Human.token(box);
      Human.reset(box);
      await postJSON("/api/feedback", { kind: f.get("kind"), note: f.get("note") || "", prompt: state.prompt, spec: state.spec || {}, turnstile });
      $("#report-dialog").close();
      e.target.reset();
      toast("Thanks. We read every report.");
    } catch (err) {
      toast(err.message);
    }
  });
  $("#sign-out").addEventListener("click", async () => {
    await postJSON("/api/logout", {});
    $("#account-dialog").close();
    await refreshMe();
    toast("Signed out.");
  });
  $("#manage-billing").addEventListener("click", async () => {
    try { location.assign((await postJSON("/api/billing/portal", {})).url); } catch (e) { toast(e.message); }
  });
  for (const b of $$(".buy")) b.addEventListener("click", () => buy(b.dataset.kind));
}

document.addEventListener("DOMContentLoaded", () => {
  start().catch((e) => {
    $("#stage-state").textContent = "The studio couldn't load. Refresh the page to try again.";
    console.error(e);
  });
});
