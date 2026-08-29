#!/usr/bin/env python3
"""PNG estático del mock HUD v1. El contrato sigue siendo GRID.md + index.html."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
FONT = "/usr/share/fonts/TTF/JetBrainsMonoNerdFont-Regular.ttf"
FONTB = "/usr/share/fonts/TTF/JetBrainsMonoNLNerdFont-SemiBold.ttf"

ICE, LIGHT, CYAN = (0xEA, 0xFD, 0xF5), (0xA7, 0xF3, 0xD0), (0x34, 0xD3, 0x99)
EMERALD, DEEP, SHADOW = (0x10, 0xB9, 0x81), (0x06, 0x4E, 0x3B), (0x04, 0x33, 0x28)
MUTED, BG, BORDER = (0x6E, 0x96, 0x8B), (0x07, 0x13, 0x10), (0x20, 0x41, 0x38)
HERDR, SIDE, BAR = (0x1E, 0x22, 0x30), (0x15, 0x18, 0x20), (0x12, 0x14, 0x1A)
PI, GOLD, PINK, DIM = (0xC8, 0xCD, 0xD8), (0xE6, 0xB4, 0x50), (0xD4, 0x8A, 0xD6), (0x7B, 0x82, 0x94)

MARK = [
    "   HHHHH     ",
    "    MMMMM    ",
    "     MMMM    ",
    "      MMMM   ",
    " LLL  XXXX   ",
    " LLL  XXXXM  ",
    "LLLLLL  MMM  ",
    " LLLLL  MM   ",
    "  LLL   MM   ",
    "   L    MM   ",
]


def font(size, bold=False):
    return ImageFont.truetype(FONTB if bold else FONT, size)


def draw_mark(img, x, y, awake, px=6):
    colors_awake = {"H": ICE, "M": CYAN, "X": LIGHT, "L": EMERALD, "S": SHADOW}
    colors_idle = {"H": MUTED, "M": EMERALD, "X": DEEP, "L": DEEP, "S": SHADOW}
    pal = colors_awake if awake else colors_idle
    for j, row in enumerate(MARK):
        for i, ch in enumerate(row):
            if ch == " ":
                continue
            x0, y0 = x + i * px, y + int(j * px * 0.85)
            for dy in range(int(px * 0.85)):
                for dx in range(px):
                    img.putpixel((x0 + dx, y0 + dy), pal[ch])


def rounded_rect(draw, box, fill, outline=None):
    draw.rectangle(box, fill=fill, outline=outline)


def render(awake: bool) -> Image.Image:
    W, H = 1280, 720
    img = Image.new("RGB", (W, H), (11, 13, 18))
    d = ImageDraw.Draw(img)
    # window
    x0, y0, x1, y1 = 24, 24, W - 24, H - 24
    rounded_rect(d, (x0, y0, x1, y1), HERDR)
    rounded_rect(d, (x0, y0, x1, y0 + 28), BAR)
    d.ellipse((x0 + 12, y0 + 9, x0 + 22, y0 + 19), fill=(58, 64, 80))
    d.ellipse((x0 + 28, y0 + 9, x0 + 38, y0 + 19), fill=(58, 64, 80))
    d.ellipse((x0 + 44, y0 + 9, x0 + 54, y0 + 19), fill=(58, 64, 80))
    d.text((x0 + 66, y0 + 7), "herdr — cortex-demo", font=font(13), fill=DIM)

    # sidebar
    sx1 = x0 + 188
    rounded_rect(d, (x0, y0 + 28, sx1, y1), SIDE)
    d.line((sx1, y0 + 28, sx1, y1), fill=(42, 49, 64))
    d.text((x0 + 14, y0 + 40), "spaces", font=font(12), fill=(107, 115, 134))
    rounded_rect(d, (x0, y0 + 62, sx1, y0 + 86), (42, 31, 20))
    d.ellipse((x0 + 16, y0 + 70, x0 + 24, y0 + 78), fill=(201, 162, 39))
    d.text((x0 + 32, y0 + 66), "cortex-demo", font=font(13), fill=(240, 213, 176))
    d.text((x0 + 14, y0 + 130), "agents", font=font(12), fill=(107, 115, 134))
    d.text((x0 + 14, y0 + 154), "cortex-demo · 1", font=font(13), fill=(208, 214, 226))
    d.text((x0 + 14, y0 + 174), "idle · pi", font=font(12), fill=DIM)
    d.text((x0 + 14, y0 + 210), "cortex-demo · HUD", font=font(13), fill=(208, 214, 226))
    hud_st = "working · cortex" if awake else "idle · cortex"
    d.text((x0 + 14, y0 + 230), hud_st, font=font(12), fill=CYAN)

    # tabs
    tx = sx1
    rounded_rect(d, (tx, y0 + 28, x1, y0 + 56), (22, 24, 31))
    rounded_rect(d, (tx, y0 + 28, tx + 70, y0 + 56), HERDR)
    d.text((tx + 16, y0 + 35), "1  pi", font=font(13), fill=(232, 237, 247))
    d.text((tx + 86, y0 + 35), "2", font=font(13), fill=DIM)

    # pi pane
    hud_top = y1 - 230
    rounded_rect(d, (tx + 1, y0 + 56, x1, hud_top), HERDR)
    d.text((tx + 22, y0 + 76), "Update Available", font=font(14, True), fill=GOLD)
    d.text((tx + 22, y0 + 100), "New version 0.84.4 is available. Run pi update", font=font(13), fill=PI)
    d.line((tx + 22, y0 + 128, x1 - 28, y0 + 128), fill=(58, 51, 68))
    d.text((tx + 22, y0 + 144), "spec/auth.md · plan listo · esperando tu próximo prompt", font=font(13), fill=DIM)
    d.text((tx + 22, y0 + 166), "no toqué src/ fuera de lo acordado.", font=font(13), fill=DIM)
    d.text((tx + 22, y0 + 210), "$", font=font(14), fill=PI)
    d.rectangle((tx + 40, y0 + 212, tx + 48, y0 + 226), fill=PI)

    # HUD
    rounded_rect(d, (tx + 1, hud_top, x1, y1), BG)
    d.line((tx + 1, hud_top, x1, hud_top), fill=DEEP)
    hx, hy = tx + 18, hud_top + 14
    draw_mark(img, hx, hy + 2, awake=awake, px=6)

    d.text((hx + 96, hy), "CORTEX", font=font(13, True), fill=CYAN)
    d.text((x1 - 90, hy), "pi idle", font=font(12), fill=CYAN if awake else MUTED)
    d.text((hx + 96, hy + 22), "cortex-demo", font=font(13, True), fill=ICE)
    d.text((hx + 214, hy + 22), "·  feature/obra17  ·  sesión 2026-08-29_auth", font=font(12), fill=MUTED)
    d.rectangle((hx + 560, hy + 20, hx + 610, hy + 38), outline=DEEP)
    d.text((hx + 568, hy + 22), "plan", font=font(12), fill=CYAN)

    d.line((hx, hy + 62, x1 - 24, hy + 62), fill=BORDER)

    if not awake:
        d.text((hx, hy + 74), "PROMPT PARA PI", font=font(11), fill=MUTED)
        d.text((hx, hy + 92), "descomponé el plan en tickets según la spec de auth;", font=font(14), fill=ICE)
        d.text((hx, hy + 110), "no toques fuera de src/auth.", font=font(14), fill=ICE)
        d.rectangle((x1 - 150, hy + 84, x1 - 24, hy + 118), outline=CYAN)
        d.text((x1 - 128, hy + 92), "[ Copiar ]", font=font(14), fill=CYAN)
        d.line((hx, hy + 132, x1 - 24, hy + 132), fill=BORDER)
        d.text((hx, hy + 146), "HIGIENE", font=font(11), fill=MUTED)
        d.text((hx + 80, hy + 144), "Validar documentos del vault", font=font(14), fill=LIGHT)
        d.text((hx + 430, hy + 146), "score 8.0", font=font(12), fill=MUTED)
        d.rectangle((x1 - 290, hy + 140, x1 - 160, hy + 168), outline=CYAN)
        d.text((x1 - 274, hy + 146), "[ Aprobar ]", font=font(13), fill=CYAN)
        d.rectangle((x1 - 148, hy + 140, x1 - 24, hy + 168), outline=BORDER)
        d.text((x1 - 128, hy + 146), "[ Saltar ]", font=font(13), fill=MUTED)
    else:
        d.text((hx, hy + 74), "CONSULTA", font=font(11), fill=MUTED)
        d.text((hx, hy + 92), "sí — vault/decisions/2026-04-jwt-hs256.md", font=font(14), fill=LIGHT)
        d.text((hx, hy + 110), "HS256 local, no RS256. el spec de auth lo cita.", font=font(14), fill=LIGHT)
        d.text((hx, hy + 136), "prompt reescrito, listo para copiar", font=font(11), fill=MUTED)
        d.text((hx, hy + 154), "implementá auth según …jwt-hs256.md (HS256). no toques fuera de src/auth.", font=font(13), fill=ICE)
        d.rectangle((x1 - 150, hy + 118, x1 - 24, hy + 152), outline=CYAN)
        d.text((x1 - 128, hy + 126), "[ Copiar ]", font=font(14), fill=CYAN)

    d.line((hx, hy + 178, x1 - 24, hy + 178), fill=BORDER)
    d.text((hx, hy + 188), "›", font=font(14), fill=CYAN)
    ask = "hay una decisión de jwt?" if awake else "preguntale a Cortex"
    d.text((hx + 18, hy + 188), ask, font=font(14), fill=ICE if awake else MUTED)
    ram = "LFM en RAM" if awake else "RAM libre"
    d.text((x1 - 120, hy + 190), ram, font=font(11), fill=CYAN if awake else MUTED)
    return img


def main():
    render(False).save(ROOT / "idle.png")
    render(True).save(ROOT / "awake.png")
    print("wrote idle.png awake.png")


if __name__ == "__main__":
    main()
