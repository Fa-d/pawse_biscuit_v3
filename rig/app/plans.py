"""Who may download what.

  not signed in   preview only (watermarked)
  free            PNG and WebP stills, watermarked, FREE_DAILY_EXPORTS a day
  credits         each download uses one credit: any format, no watermark (packs of PACK_CREDITS)
  pro             everything, no watermark, no limits, sticker-pack zips
"""
from __future__ import annotations

from dataclasses import dataclass

from . import db
from .config import settings

FORMATS = {
    # key: (file extension, media type, label)
    "png": ("png", "image/png", "PNG"),
    "webp": ("webp", "image/webp", "WebP"),
    "tgs": ("tgs", "application/x-tgsticker", "Telegram"),
    "awebp": ("anim.webp", "image/webp", "WhatsApp"),
    "gif": ("gif", "image/gif", "GIF"),
    "json": ("json", "application/json", "Lottie"),
}
FREE_FORMATS = ("png", "webp")


@dataclass
class Decision:
    allowed: bool
    watermark: bool = True
    use_credit: bool = False
    reason: str = ""


def decide(c, user, fmt) -> Decision:
    if fmt not in FORMATS:
        return Decision(False, reason=f"Unknown format {fmt!r}.")
    if user is None:
        return Decision(False, reason="Create a free account to download stickers.")
    if user["plan"] == "pro":
        return Decision(True, watermark=False)
    if user["credits"] > 0:
        return Decision(True, watermark=False, use_credit=True)
    if fmt not in FREE_FORMATS:
        return Decision(False, reason=f"{FORMATS[fmt][2]} downloads come with Pro or a credit pack.")
    if db.usage_today(c, user["id"], "export") >= settings.free_daily_exports:
        return Decision(False, reason=f"You've used today's {settings.free_daily_exports} free downloads. "
                                      "They reset at midnight UTC, or get Pro for unlimited downloads.")
    return Decision(True, watermark=True)


def preview_watermark(user) -> bool:
    return user is None or (user["plan"] != "pro" and user["credits"] <= 0)


def summary(c, user):
    """What the editor needs to show: plan, credits, downloads left today."""
    if user is None:
        return None
    left = None
    if user["plan"] != "pro" and user["credits"] <= 0:
        left = max(0, settings.free_daily_exports - db.usage_today(c, user["id"], "export"))
    return dict(email=user["email"], plan=user["plan"], credits=user["credits"], free_left_today=left,
                google=bool(user["google_sub"]),
                formats=[f for f in FORMATS if decide(c, user, f).allowed or f in FREE_FORMATS])
