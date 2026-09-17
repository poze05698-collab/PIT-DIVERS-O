import io
import random
from PIL import Image, ImageDraw, ImageFont


def _font(size: int):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


def _base(title: str):
    image = Image.new("RGB", (900, 560), (18, 22, 32))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((25, 25, 875, 535), radius=28, fill=(245, 247, 250))
    draw.rounded_rectangle((25, 25, 875, 100), radius=28, fill=(30, 30, 35))
    draw.text((55, 45), title, font=_font(30), fill=(255, 255, 255))
    return image, draw


def make_number_image(number: int) -> io.BytesIO:
    """Generate a visual number challenge entirely locally."""
    image, draw = _base("PIT DIVERSÃO • DESAFIO VISUAL")
    font = _font(260)
    text = str(number)
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (900 - (bbox[2] - bbox[0])) // 2
    y = 160
    draw.text((x, y), text, font=font, fill=(20, 25, 35))
    draw.text((55, 485), "Qual número aparece na imagem?", font=_font(25), fill=(45, 45, 50))
    return _save(image)


def make_count_image(count: int, seed: int = 0) -> io.BytesIO:
    """Generate a visual counting challenge."""
    image, draw = _base("PIT DIVERSÃO • CONTE AS FORMAS")
    rng = random.Random(seed)
    positions = []
    for row in range(3):
        for col in range(6):
            positions.append((145 + col * 125, 175 + row * 90))
    rng.shuffle(positions)
    for i, (x, y) in enumerate(positions[:count]):
        r = 22
        draw.ellipse((x-r, y-r, x+r, y+r), fill=(35, 70, 150), outline=(15, 20, 30), width=3)
    draw.text((55, 485), "Quantos círculos aparecem?", font=_font(25), fill=(45, 45, 50))
    return _save(image)


def make_odd_one_out_image(seed: int = 0) -> tuple[io.BytesIO, int]:
    """Create a grid where one symbol is different; return image and 1-based position."""
    image, draw = _base("PIT DIVERSÃO • ENCONTRE O DIFERENTE")
    cells = [(270 + c * 120, 170 + r * 105) for r in range(3) for c in range(3)]
    odd = random.Random(seed).randint(0, 8)
    for i, (x, y) in enumerate(cells):
        if i == odd:
            draw.rectangle((x-30, y-30, x+30, y+30), fill=(200, 55, 55), outline=(20, 20, 25), width=3)
        else:
            draw.rectangle((x-30, y-30, x+30, y+30), fill=(35, 70, 150), outline=(20, 20, 25), width=3)
    draw.text((55, 485), "Qual posição é diferente? (1 a 9)", font=_font(25), fill=(45, 45, 50))
    return _save(image), odd + 1


# 500 presets visuais. Os desenhos são gerados localmente a partir do preset.
VISUAL_CHALLENGES = []
for _i in range(1, 501):
    if _i % 3 == 1:
        VISUAL_CHALLENGES.append({"id": _i, "kind": "number", "value": ((_i * 37) % 999) + 1})
    elif _i % 3 == 2:
        VISUAL_CHALLENGES.append({"id": _i, "kind": "count", "value": ((_i * 7) % 13) + 4})
    else:
        VISUAL_CHALLENGES.append({"id": _i, "kind": "odd", "value": _i})


def _save(image: Image.Image) -> io.BytesIO:
    out = io.BytesIO()
    out.name = "desafio_visual.png"
    image.save(out, format="PNG", optimize=True)
    out.seek(0)
    return out
