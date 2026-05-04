"""
Generates assets/banner.png — a wide header banner for the Streamlit main page.
Dimensions : 900 × 200 px
Style       : Deep navy-to-teal gradient, health cross, heartbeat line,
              large app title, tagline, and copyright footer baked in.
Run         : python assets/generate_banner.py
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import math

# ── canvas ────────────────────────────────────────────────────────────────────
W, H = 900, 200
img  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# ── gradient background (navy → teal) ─────────────────────────────────────────
C_LEFT  = (12,  45,  90)   # deep navy
C_RIGHT = (0,  120, 100)   # teal
for x in range(W):
    t  = x / (W - 1)
    r  = int(C_LEFT[0] + t * (C_RIGHT[0] - C_LEFT[0]))
    g  = int(C_LEFT[1] + t * (C_RIGHT[1] - C_LEFT[1]))
    b  = int(C_LEFT[2] + t * (C_RIGHT[2] - C_LEFT[2]))
    draw.line([(x, 0), (x, H)], fill=(r, g, b, 255))

# ── rounded-rect overlay (subtle dark card) ────────────────────────────────────
CARD_M = 10
draw.rounded_rectangle(
    [CARD_M, CARD_M, W - CARD_M, H - CARD_M],
    radius=18,
    outline=(255, 255, 255, 40),
    width=1,
)

# ── health cross (left side) ───────────────────────────────────────────────────
CX, CY   = 68, 90
ARM      = 28
THICK    = 10
CROSS_C  = (0, 220, 140)  # bright mint green

# vertical bar
draw.rounded_rectangle(
    [CX - THICK // 2, CY - ARM, CX + THICK // 2, CY + ARM],
    radius=4, fill=CROSS_C,
)
# horizontal bar
draw.rounded_rectangle(
    [CX - ARM, CY - THICK // 2, CX + ARM, CY + THICK // 2],
    radius=4, fill=CROSS_C,
)

# ── heartbeat / pulse line ─────────────────────────────────────────────────────
PULSE_C = (0, 220, 140)
PX = [110, 125, 132, 140, 150, 162, 172, 185, 192, 200, 210, 220]
PY_BASE = CY
PULSE_Y = [0, 0, -18, 34, -42, 50, -28, 20, -8, 0, 0, 0]
pts = [(px, PY_BASE + py) for px, py in zip(PX, PULSE_Y)]
draw.line(pts, fill=PULSE_C, width=2, joint="curve")

# ── fonts ─────────────────────────────────────────────────────────────────────
FONT_DIR = Path("C:/Windows/Fonts")

def load(name: str, size: int) -> ImageFont.FreeTypeFont:
    for fname in (name, name.lower()):
        p = FONT_DIR / fname
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()

font_title    = load("segoeui.ttf",   46)
font_subtitle = load("segoeuil.ttf",  20)
font_copy     = load("segoeuisl.ttf", 13)

# ── main title ─────────────────────────────────────────────────────────────────
TITLE_X = 235
draw.text((TITLE_X, 38), "MyHealthCoach", font=font_title, fill=(255, 255, 255, 255))

# ── subtitle ───────────────────────────────────────────────────────────────────
draw.text(
    (TITLE_X, 96),
    "— AI Wellness Assistant  ·  Powered by Azure OpenAI & LangGraph",
    font=font_subtitle,
    fill=(180, 240, 220, 230),
)

# ── thin separator line ────────────────────────────────────────────────────────
draw.line([(TITLE_X, 128), (W - 20, 128)], fill=(255, 255, 255, 60), width=1)

# ── copyright footer (baked into image) ───────────────────────────────────────
copy_text = "Copyright @CodeInsights  |  Design and Developed by pramodklal"
draw.text(
    (TITLE_X, 140),
    copy_text,
    font=font_copy,
    fill=(160, 220, 200, 210),
)

# ── "AI" badge (top-right) ─────────────────────────────────────────────────────
BADGE_X1, BADGE_Y1 = W - 58, 14
BADGE_X2, BADGE_Y2 = W - 14, 36
draw.rounded_rectangle(
    [BADGE_X1, BADGE_Y1, BADGE_X2, BADGE_Y2],
    radius=6,
    fill=(0, 220, 140, 230),
)
font_badge = load("segoeuib.ttf", 14)
draw.text(
    ((BADGE_X1 + BADGE_X2) // 2, (BADGE_Y1 + BADGE_Y2) // 2),
    "AI",
    font=font_badge,
    fill=(10, 40, 70, 255),
    anchor="mm",
)

# ── save ──────────────────────────────────────────────────────────────────────
out = Path(__file__).resolve().parent / "banner.png"
img.save(str(out), "PNG")
print(f"Saved: {out}")
