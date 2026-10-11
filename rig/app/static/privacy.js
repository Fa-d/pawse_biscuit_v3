"use strict";
fetch("/api/me").then((r) => r.json()).then((me) => {
  if (!me.contact) return;
  const line = document.getElementById("contact-line");
  line.textContent = "";
  line.append("write to ", Object.assign(document.createElement("a"), { href: `mailto:${me.contact}`, textContent: me.contact }));
});
