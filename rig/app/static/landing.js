// Landing page: shows real stickers from the engine, typing the prompt that made each one.
"use strict";

const $ = (sel, root = document) => root.querySelector(sel);
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function play(box, data, still, autoplay) {
  box.replaceChildren();
  const a = lottie.loadAnimation({ container: box, renderer: "svg", loop: true, autoplay: autoplay && !reduceMotion, animationData: data });
  if (!autoplay || reduceMotion) a.addEventListener("DOMLoaded", () => a.goToAndStop(still, true));
  return a;
}

async function demo(examples) {
  const prompt = $("#demo-prompt");
  const box = $("#demo-sticker");
  let anim = null;
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
    if (anim) anim.destroy();
    anim = play(box, ex.lottie, ex.still, true);
    await sleep(reduceMotion ? 6000 : 4200);
    if (reduceMotion && i === examples.length - 1) return;   // with reduced motion, show each once and stop
  }
}

async function start() {
  const me = await fetch("/api/me").then((r) => r.json());
  for (const n of document.querySelectorAll(".free-daily")) n.textContent = me.free_daily;
  for (const n of document.querySelectorAll(".pack-credits")) n.textContent = me.pack_credits;
  for (const n of document.querySelectorAll(".price-pro")) n.textContent = me.price_pro;
  for (const n of document.querySelectorAll(".price-pack")) n.textContent = me.price_pack;
  if (me.contact) $("#contact-link").href = `mailto:${me.contact}`;
  else $("#faq-brand").hidden = true;

  if (me.invite_only && !me.user) {
    $("#cta-open").hidden = true;
    $("#waitlist").hidden = false;
    $("#waitlist").addEventListener("submit", async (e) => {
      e.preventDefault();
      const note = $("#wl-note");
      const res = await fetch("/api/waitlist", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: $("#wl-email").value, source: "landing" }) });
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
    if (ex) play(li.querySelector(".cast-sticker"), ex.lottie, ex.still, false);
  }
  demo(examples);
}

document.addEventListener("DOMContentLoaded", () => { start().catch((e) => console.error(e)); });
