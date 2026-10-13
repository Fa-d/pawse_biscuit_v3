// Landing page: shows real stickers from the engine, typing the prompt that made each one.
"use strict";

const $ = (sel, root = document) => root.querySelector(sel);
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// The examples are pictures made on the server (an animated WebP and a PNG still), never the sticker's vector source.
function show(box, ex, animate) {
  const img = Object.assign(document.createElement("img"), { src: animate && !reduceMotion ? ex.image : ex.still,
    alt: `Sticker made from "${ex.prompt}"`, draggable: false, decoding: "async" });
  box.replaceChildren(img);
}

async function demo(examples) {
  const prompt = $("#demo-prompt");
  const box = $("#demo-sticker");
  for (let i = 0; ; i = (i + 1) % examples.length) {
    const ex = examples[i];
    if (reduceMotion) {
      prompt.textContent = ex.prompt;
    } else {
      prompt.textContent = "";
      const caret = document.createElement("span");
      caret.className = "caret";
      for (const ch of ex.prompt) {
        prompt.textContent += ch;
        prompt.append(caret);
        await sleep(38);
      }
      await sleep(250);
      caret.remove();
    }
    show(box, ex, true);
    await sleep(reduceMotion ? 6000 : 4200);
    if (reduceMotion && i === examples.length - 1) return;   // with reduced motion, show each once and stop
  }
}

async function start() {
  const me = await fetch("/api/me").then((r) => r.json());
  Human.setKey(me.turnstile);
  for (const n of document.querySelectorAll(".free-daily")) n.textContent = me.free_daily;
  for (const n of document.querySelectorAll(".pack-credits")) n.textContent = me.pack_credits;
  for (const n of document.querySelectorAll(".price-pro")) n.textContent = me.price_pro;
  for (const n of document.querySelectorAll(".price-pack")) n.textContent = me.price_pack;
  if (me.contact) $("#contact-link").href = `mailto:${me.contact}`;
  else $("#faq-brand").hidden = true;

  if (me.invite_only && !me.user) {
    $("#cta-open").hidden = true;
    $("#waitlist").hidden = false;
    Human.prepare($("#wl-human"));
    $("#waitlist").addEventListener("submit", async (e) => {
      e.preventDefault();
      const note = $("#wl-note");
      let turnstile = "";
      try { turnstile = await Human.token($("#wl-human")); } catch (err) { note.textContent = err.message; return; }
      Human.reset($("#wl-human"));
      const res = await fetch("/api/waitlist", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: $("#wl-email").value, source: "landing", turnstile }) });
      if (res.ok) {
        e.target.replaceChildren(Object.assign(document.createElement("p"), { className: "cta-note",
          textContent: "You're on the list. We'll email your invite as soon as there's room." }));
      } else {
        const j = await res.json().catch(() => ({}));
        note.textContent = typeof j.detail === "string" ? j.detail : "That didn't work. Check the email address and try again.";
      }
    });
  }

  const examples = await fetch("/api/examples").then((r) => r.json());
  for (const li of document.querySelectorAll("#cast li")) {
    const ex = examples.find((x) => x.base === li.dataset.base);
    if (ex) show(li.querySelector(".cast-sticker"), ex, false);
  }
  demo(examples);
}

document.addEventListener("DOMContentLoaded", () => { start().catch((e) => console.error(e)); });
