"""
Generate MyHealthCoach sidebar logo PNG.
Run once:  python assets/generate_logo.py
Output:    assets/logo.png  (320 x 88 px)
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent / "logo.png"

# ── canvas ─────────────────────────────────────────────────────────────────────
W, H = 320, 88
img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# ── background pill ────────────────────────────────────────────────────────────
BG    = (240, 250, 244, 255)   # very light green-white
BORD  = (30, 160, 90, 255)     # medium green border
R     = 18                     # corner radius

def draw_rounded_rect(draw, xy, radius, fill, outline, width=2):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill, outline=outline, width=width)

draw_rounded_rect(draw, [2, 2, W - 2, H - 2], R, fill=BG, outline=BORD, width=3)

# ── health cross icon (left side) ─────────────────────────────────────────────
GREEN = (30, 160, 90, 255)
CROSS_CX, CROSS_CY = 38, H // 2
ARM_W, ARM_H = 10, 28

# vertical bar
draw.rectangle(
    [CROSS_CX - ARM_W // 2, CROSS_CY - ARM_H // 2,
     CROSS_CX + ARM_W // 2, CROSS_CY + ARM_H // 2],
    fill=GREEN,
)
# horizontal bar
draw.rectangle(
    [CROSS_CX - ARM_H // 2, CROSS_CY - ARM_W // 2,
     CROSS_CX + ARM_H // 2, CROSS_CY + ARM_W // 2],
    fill=GREEN,
)
# white inner cross (gives hollow feel)
INNER = 4
draw.rectangle(
    [CROSS_CX - ARM_W // 2 + INNER, CROSS_CY - ARM_H // 2 + INNER,
     CROSS_CX + ARM_W // 2 - INNER, CROSS_CY + ARM_H // 2 - INNER],
    fill=(255, 255, 255, 255),
)
draw.rectangle(
    [CROSS_CX - ARM_H // 2 + INNER, CROSS_CY - ARM_W // 2 + INNER,
     CROSS_CX + ARM_H // 2 - INNER, CROSS_CY + ARM_W // 2 - INNER],
    fill=(255, 255, 255, 255),
)

# ── pulse / heartbeat line (right of icon) ────────────────────────────────────
PULSE_COLOR = (30, 160, 90, 255)
PX = [72, 84, 90, 96, 108, 116, 122, 134]
PY = [H // 2, H // 2, H // 2 - 18, H // 2 + 14, H // 2 - 10, H // 2 + 6, H // 2, H // 2]
draw.line(list(zip(PX, PY)), fill=PULSE_COLOR, width=3, joint="curve")

# ── tool name text ─────────────────────────────────────────────────────────────
TEXT_X = 146
try:
    font_main = ImageFont.truetype("arial.ttf", 17)
    font_sub  = ImageFont.truetype("arial.ttf", 11)
except OSError:
    font_main = ImageFont.load_default()
    font_sub  = font_main

# primary name
draw.text((TEXT_X, 18), "MyHealthCoach", font=font_main, fill=(20, 100, 55, 255))
# tagline
draw.text((TEXT_X, 42), "— AI Wellness Assistant", font=font_sub, fill=(70, 130, 90, 255))

# ── "AI" badge (top-right corner) ─────────────────────────────────────────────
BADGE_BG   = (30, 160, 90, 255)
BADGE_TEXT = (255, 255, 255, 255)
bx0, by0, bx1, by1 = W - 40, 6, W - 8, 24
draw.rounded_rectangle([bx0, by0, bx1, by1], radius=5, fill=BADGE_BG)
try:
    badge_font = ImageFont.truetype("arialbd.ttf", 10)
except OSError:
    badge_font = font_sub
draw.text((bx0 + 6, by0 + 2), "AI", font=badge_font, fill=BADGE_TEXT)

# ── save ───────────────────────────────────────────────────────────────────────
OUT.parent.mkdir(parents=True, exist_ok=True)
img.save(str(OUT), format="PNG")
print(f"Saved: {OUT}")
