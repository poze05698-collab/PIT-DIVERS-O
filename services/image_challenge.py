# -*- coding: utf-8 -*-
"""Gerador de desafios visuais profissionais do PIT DIVERSÃO."""
import io
import math
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

W, H = 1080, 720


def _font(size: int):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _gradient():
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):
        t = y / (H - 1)
        r = int(9 + 18 * t)
        g = int(12 + 20 * t)
        b = int(28 + 42 * t)
        for x in range(W):
            glow = max(0, 1 - math.hypot(x - W * .78, y - H * .20) / 650)
            px[x, y] = (
                min(255, int(r + 8 * glow)),
                min(255, int(g + 22 * glow)),
                min(255, int(b + 45 * glow)),
            )
    return img


def _base(label: str, subtitle: str):
    image = _gradient()
    draw = ImageDraw.Draw(image, "RGBA")

    # Soft decorative lights.
    for x, y, r, a in [(120, 130, 170, 35), (930, 140, 210, 28), (850, 610, 260, 24)]:
        draw.ellipse((x-r, y-r, x+r, y+r), fill=(70, 140, 255, a))

    # Main glass card.
    draw.rounded_rectangle((34, 30, W-34, H-30), radius=42,
                           fill=(10, 14, 28, 210), outline=(95, 160, 255, 150), width=3)
    draw.rounded_rectangle((58, 54, W-58, 145), radius=28,
                           fill=(26, 37, 67, 230), outline=(110, 175, 255, 100), width=2)

    draw.text((88, 76), "PIT DIVERSÃO", font=_font(38), fill=(240, 248, 255, 255))
    draw.text((88, 119), label.upper(), font=_font(21), fill=(117, 193, 255, 255))
    draw.text((W-430, 91), subtitle, font=_font(22), fill=(205, 220, 240, 255))

    # Footer.
    draw.line((80, H-110, W-80, H-110), fill=(100, 160, 240, 80), width=2)
    draw.text((82, H-88), "⚡ Seja rápido. O primeiro acerto vence!", font=_font(24),
              fill=(210, 225, 245, 235))
    return image


def _save(image):
    out = io.BytesIO()
    out.name = "desafio_visual.png"
    image.save(out, format="PNG", optimize=True)
    out.seek(0)
    return out


def _fit_font(text, max_size=380, min_size=100, max_width=820):
    for size in range(max_size, min_size-1, -8):
        f = _font(size)
        box = f.getbbox(text)
        if box[2] - box[0] <= max_width:
            return f
    return _font(min_size)


def make_number_image(number: int) -> io.BytesIO:
    """Número enorme, central e propositalmente levemente embaçado."""
    image = _base("DESAFIO VISUAL", "🔢 QUAL É O NÚMERO?")
    draw = ImageDraw.Draw(image, "RGBA")
    text = str(number)
    font = _fit_font(text)

    box = draw.textbbox((0, 0), text, font=font)
    tw, th = box[2]-box[0], box[3]-box[1]
    x = (W-tw)//2
    y = 260 - th//2

    # Glow e sombra.
    for blur_radius, alpha in [(24, 55), (10, 90)]:
        layer = Image.new("RGBA", (W, H), (0,0,0,0))
        ld = ImageDraw.Draw(layer)
        ld.text((x, y), text, font=font, fill=(65, 155, 255, alpha),
                stroke_width=10, stroke_fill=(65, 155, 255, alpha))
        layer = layer.filter(ImageFilter.GaussianBlur(blur_radius))
        image = Image.alpha_composite(image.convert("RGBA"), layer).convert("RGB")

    # Número com embaçado leve para ser identificável, sem ficar ilegível.
    sharp = Image.new("RGBA", (W, H), (0,0,0,0))
    sd = ImageDraw.Draw(sharp)
    sd.text((x, y), text, font=font, fill=(245, 250, 255, 245),
            stroke_width=8, stroke_fill=(40, 95, 180, 230))
    blurred = sharp.filter(ImageFilter.GaussianBlur(radius=2.4))
    image = Image.alpha_composite(image.convert("RGBA"), blurred).convert("RGB")

    return _save(image)


def make_count_image(count: int, seed: int = 0) -> io.BytesIO:
    image = _base("DESAFIO VISUAL", "⭕ CONTE AS FORMAS")
    draw = ImageDraw.Draw(image, "RGBA")
    rng = random.Random(seed)

    cols, rows = 6, 3
    positions = []
    for r in range(rows):
        for c in range(cols):
            positions.append((165 + c*150, 225 + r*115))
    rng.shuffle(positions)

    for i, (x,y) in enumerate(positions[:count]):
        # subtle rotation via separate tile
        r=34
        draw.ellipse((x-r, y-r, x+r, y+r),
                     fill=(60, 145, 255, 245), outline=(220,240,255,230), width=4)
        draw.ellipse((x-12,y-12,x+12,y+12), fill=(230,245,255,120))

    return _save(image)


def make_odd_one_out_image(seed: int = 0):
    image = _base("DESAFIO VISUAL", "🧩 ENCONTRE O DIFERENTE")
    draw = ImageDraw.Draw(image, "RGBA")
    rng = random.Random(seed)
    cells = [(285+c*255, 220+r*160) for r in range(3) for c in range(3)]
    odd = rng.randrange(9)

    for i,(x,y) in enumerate(cells):
        if i == odd:
            # diamond
            pts=[(x,y-48),(x+48,y),(x,y+48),(x-48,y)]
            draw.polygon(pts, fill=(255, 90, 115, 245), outline=(255,235,240,255))
        else:
            draw.ellipse((x-45,y-45,x+45,y+45),
                         fill=(70,150,255,245), outline=(230,245,255,255), width=4)
        draw.text((x-10,y+62), str(i+1), font=_font(22), fill=(190,215,245,220))

    return _save(image), odd+1


def make_color_image(answer: int, seed: int = 0):
    image = _base("DESAFIO VISUAL", "🎨 QUAL É A COR?")
    draw = ImageDraw.Draw(image, "RGBA")
    palette = [
        ("AZUL",(55,145,255,255)),
        ("VERDE",(55,205,130,255)),
        ("VERMELHO",(255,80,105,255)),
        ("AMARELO",(255,205,70,255)),
        ("ROXO",(165,100,255,255)),
    ]
    name,rgb=palette[answer]
    draw.rounded_rectangle((250,205,830,500), radius=55, fill=rgb,
                           outline=(245,250,255,245), width=7)
    # leve textura/blur nas bordas
    glow=Image.new("RGBA",(W,H),(0,0,0,0))
    gd=ImageDraw.Draw(glow)
    gd.rounded_rectangle((245,200,835,505), radius=60, outline=rgb, width=22)
    glow=glow.filter(ImageFilter.GaussianBlur(14))
    image=Image.alpha_composite(image.convert("RGBA"),glow).convert("RGB")
    return _save(image)


def make_sequence_image(answer: int, seed: int = 0):
    image = _base("DESAFIO VISUAL", "🔺 COMPLETE A SEQUÊNCIA")
    draw = ImageDraw.Draw(image, "RGBA")
    rng = random.Random(seed)
    start=rng.randint(2,8)
    step=rng.randint(2,9)
    vals=[start+i*step for i in range(4)]
    vals.append(answer)
    x0=145
    for i,v in enumerate(vals):
        x=x0+i*180
        if i==4:
            # placeholder
            draw.rounded_rectangle((x-55,275,x+55,385),radius=22,
                                   fill=(55,80,125,170),outline=(130,200,255,240),width=4)
            draw.text((x-18,295),"?",font=_font(62),fill=(245,250,255,255))
        else:
            draw.rounded_rectangle((x-55,275,x+55,385),radius=22,
                                   fill=(42,125,220,235),outline=(210,235,255,240),width=4)
            txt=str(v); f=_fit_font(txt,120,60,90)
            b=draw.textbbox((0,0),txt,font=f)
            draw.text((x-(b[2]-b[0])//2,290),txt,font=f,fill=(250,252,255,255))
    return _save(image)


# Presets são apenas regras de geração, não 500 imagens armazenadas.
VISUAL_CHALLENGES = []
for i in range(1, 501):
    if i % 5 == 1:
        VISUAL_CHALLENGES.append({"id": i, "kind": "number", "value": (i*37)%999+1})
    elif i % 5 == 2:
        VISUAL_CHALLENGES.append({"id": i, "kind": "count", "value": (i*7)%13+4})
    elif i % 5 == 3:
        VISUAL_CHALLENGES.append({"id": i, "kind": "odd", "value": i})
    elif i % 5 == 4:
        VISUAL_CHALLENGES.append({"id": i, "kind": "color", "value": i%5})
    else:
        # sequência: 4, 7, 10, 13, ?
        step = (i % 8) + 2
        start = (i % 7) + 2
        value = start + 4*step
        VISUAL_CHALLENGES.append({"id": i, "kind": "sequence", "value": value, "start": start, "step": step})
