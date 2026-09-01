#!/usr/bin/env python3
"""Stills del mock. Contrato: GRID.md + index.html. Logo = PNG original recortado."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
FONT = "/usr/share/fonts/TTF/JetBrainsMonoNerdFont-Regular.ttf"
FONTB = "/usr/share/fonts/TTF/JetBrainsMonoNLNerdFont-SemiBold.ttf"

PAPER = (246, 247, 245)
PAPER_DUSK = (240, 242, 239)
FOREST = (3, 82, 46)
MINT = (143, 220, 176)
MINT_SOFT = (174, 232, 198)
MINT_PALE = (200, 240, 220)
TEXT = (228, 237, 231)
MUTED = (138, 158, 147)
BG = (12, 20, 16)
BORDER = (42, 74, 58)
ACCENT = (61, 107, 84)
HERDR, SIDE, BAR = (30, 34, 48), (21, 24, 32), (18, 20, 26)
PI, GOLD, DIM = (200, 205, 216), (196, 163, 106), (123, 130, 148)


def font(size, bold=False):
    return ImageFont.truetype(FONTB if bold else FONT, size)


def render(awake: bool) -> Image.Image:
    W, H = 1280, 740
    img = Image.new("RGB", (W, H), (11, 13, 18))
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = 24, 24, W - 24, H - 24
    d.rectangle((x0, y0, x1, y1), fill=HERDR)
    d.rectangle((x0, y0, x1, y0 + 28), fill=BAR)
    d.ellipse((x0 + 12, y0 + 9, x0 + 22, y0 + 19), fill=(58, 64, 80))
    d.ellipse((x0 + 28, y0 + 9, x0 + 38, y0 + 19), fill=(58, 64, 80))
    d.ellipse((x0 + 44, y0 + 9, x0 + 54, y0 + 19), fill=(58, 64, 80))
    d.text((x0 + 66, y0 + 7), "herdr — cortex-demo", font=font(13), fill=DIM)

    sx1 = x0 + 188
    d.rectangle((x0, y0 + 28, sx1, y1), fill=SIDE)
    d.line((sx1, y0 + 28, sx1, y1), fill=(42, 49, 64))
    d.text((x0 + 14, y0 + 40), "spaces", font=font(12), fill=(107, 115, 134))
    d.rectangle((x0, y0 + 62, sx1, y0 + 86), fill=(42, 31, 20))
    d.ellipse((x0 + 16, y0 + 70, x0 + 24, y0 + 78), fill=(201, 162, 39))
    d.text((x0 + 32, y0 + 66), "cortex-demo", font=font(13), fill=(240, 213, 176))
    d.text((x0 + 14, y0 + 130), "agents", font=font(12), fill=(107, 115, 134))
    d.text((x0 + 14, y0 + 154), "cortex-demo · 1", font=font(13), fill=(208, 214, 226))
    d.text((x0 + 14, y0 + 174), "idle · pi", font=font(12), fill=DIM)
    d.text((x0 + 14, y0 + 210), "cortex-demo · HUD", font=font(13), fill=(208, 214, 226))
    d.text(
        (x0 + 14, y0 + 230),
        "working · cortex" if awake else "idle · cortex",
        font=font(12),
        fill=MINT,
    )

    d.rectangle((sx1, y0 + 28, x1, y0 + 56), fill=(22, 24, 31))
    d.rectangle((sx1, y0 + 28, sx1 + 70, y0 + 56), fill=HERDR)
    d.text((sx1 + 16, y0 + 35), "1  pi", font=font(13), fill=(232, 237, 247))
    d.text((sx1 + 86, y0 + 35), "2", font=font(13), fill=DIM)

    hud_top = y1 - 248
    d.rectangle((sx1 + 1, y0 + 56, x1, hud_top), fill=HERDR)
    d.text((sx1 + 22, y0 + 76), "Update Available", font=font(14, True), fill=GOLD)
    d.text((sx1 + 22, y0 + 100), "New version 0.84.4 is available. Run pi update", font=font(13), fill=PI)
    d.line((sx1 + 22, y0 + 128, x1 - 28, y0 + 128), fill=(58, 51, 68))
    d.text((sx1 + 22, y0 + 144), "spec/auth.md · plan listo · esperando tu próximo prompt", font=font(13), fill=DIM)
    d.text((sx1 + 22, y0 + 166), "no toqué src/ fuera de lo acordado.", font=font(13), fill=DIM)
    d.text((sx1 + 22, y0 + 210), "$", font=font(14), fill=PI)
    d.rectangle((sx1 + 40, y0 + 212, sx1 + 48, y0 + 226), fill=PI)

    # HUD
    d.rectangle((sx1 + 1, hud_top, x1, y1), fill=BG)
    d.line((sx1 + 1, hud_top, x1, hud_top), fill=FOREST)
    brand_w = 232
    paper = PAPER if awake else PAPER_DUSK
    d.rectangle((sx1 + 1, hud_top, sx1 + 1 + brand_w, y1), fill=paper)
    d.line((sx1 + 1 + brand_w, hud_top, sx1 + 1 + brand_w, y1), fill=(213, 221, 216))

    mark = Image.open(ROOT / "logo-mark.png").convert("RGBA")
    word = Image.open(ROOT / "logo-word.png").convert("RGBA")
    mw, mh = 200, 158
    mark_r = mark.copy()
    mark_r.thumbnail((mw, mh), Image.Resampling.LANCZOS)
    ww, wh = 208, 42
    word_r = word.copy()
    word_r.thumbnail((ww, wh), Image.Resampling.LANCZOS)
    bx = sx1 + 1 + (brand_w - mark_r.size[0]) // 2
    by = hud_top + 16
    img.paste(mark_r, (bx, by), mark_r)
    wx = sx1 + 1 + (brand_w - word_r.size[0]) // 2
    img.paste(word_r, (wx, y1 - 16 - word_r.size[1]), word_r)

    dx = sx1 + brand_w + 18
    dy = hud_top + 14
    d.text((dx, dy), "COMPANION", font=font(11), fill=MUTED)
    d.text((x1 - 90, dy), "pi idle", font=font(12), fill=MINT_SOFT if awake else MUTED)
    d.text((dx, dy + 22), "cortex-demo", font=font(13, True), fill=TEXT)
    d.text((dx + 118, dy + 22), "·  feature/obra17  ·  sesión 2026-08-29_auth", font=font(12), fill=MUTED)
    d.rectangle((dx + 500, dy + 20, dx + 548, dy + 38), outline=BORDER)
    d.text((dx + 508, dy + 22), "plan", font=font(12), fill=MINT_SOFT)
    d.line((dx, dy + 50, x1 - 22, dy + 50), fill=BORDER)

    if not awake:
        d.text((dx, dy + 62), "PROMPT PARA PI", font=font(11), fill=MUTED)
        d.text((dx, dy + 80), "descomponé el plan en tickets según la spec de auth;", font=font(14), fill=TEXT)
        d.text((dx, dy + 100), "no toques fuera de src/auth.", font=font(14), fill=TEXT)
        d.rectangle((x1 - 148, dy + 74, x1 - 22, dy + 108), outline=ACCENT)
        d.text((x1 - 126, dy + 84), "[ Copiar ]", font=font(13), fill=MINT_PALE)
        d.line((dx, dy + 122, x1 - 22, dy + 122), fill=BORDER)
        d.text((dx, dy + 136), "HIGIENE", font=font(11), fill=MUTED)
        d.text((dx + 80, dy + 134), "Validar documentos del vault", font=font(14), fill=MINT_SOFT)
        d.text((dx + 420, dy + 136), "score 8.0", font=font(12), fill=MUTED)
        d.rectangle((x1 - 286, dy + 130, x1 - 158, dy + 158), outline=ACCENT)
        d.text((x1 - 270, dy + 136), "[ Aprobar ]", font=font(13), fill=MINT_PALE)
        d.rectangle((x1 - 148, dy + 130, x1 - 22, dy + 158), outline=BORDER)
        d.text((x1 - 128, dy + 136), "[ Saltar ]", font=font(13), fill=MUTED)
    else:
        d.text((dx, dy + 62), "CONSULTA", font=font(11), fill=MUTED)
        d.text((dx, dy + 80), "sí — vault/decisions/2026-04-jwt-hs256.md", font=font(14), fill=MINT_SOFT)
        d.text((dx, dy + 100), "HS256 local, no RS256. el spec de auth lo cita.", font=font(14), fill=MINT_SOFT)
        d.text((dx, dy + 124), "prompt reescrito", font=font(11), fill=MUTED)
        d.text((dx, dy + 142), "implementá auth según …jwt-hs256.md (HS256). no toques fuera de src/auth.", font=font(13), fill=TEXT)
        d.rectangle((x1 - 148, dy + 110, x1 - 22, dy + 144), outline=ACCENT)
        d.text((x1 - 126, dy + 120), "[ Copiar ]", font=font(13), fill=MINT_PALE)

    d.line((dx, dy + 172, x1 - 22, dy + 172), fill=BORDER)
    d.text((dx, dy + 184), "›", font=font(14), fill=MINT)
    ask = "hay una decisión de jwt?" if awake else "preguntale a Cortex"
    d.text((dx + 18, dy + 184), ask, font=font(14), fill=TEXT if awake else MUTED)
    d.text(
        (x1 - 118, dy + 186),
        "LFM en RAM" if awake else "RAM libre",
        font=font(11),
        fill=MINT_SOFT if awake else MUTED,
    )
    return img


def main():
    render(False).save(ROOT / "idle.png")
    render(True).save(ROOT / "awake.png")
    print("wrote idle.png awake.png")


if __name__ == "__main__":
    main()
