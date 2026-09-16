import io
import random
from PIL import Image, ImageDraw, ImageFilter

def make_number_image(number: int) -> io.BytesIO:
    """Creates a simple visual challenge image containing one target number."""
    w, h = 700, 420
    bg = Image.new("RGB", (w, h), (245, 245, 245))
    draw = ImageDraw.Draw(bg)

    # Decorative noise makes it a visual challenge without hiding the answer.
    for _ in range(90):
        x = random.randint(20, w - 20)
        y = random.randint(20, h - 20)
        r = random.randint(2, 9)
        shade = random.randint(150, 225)
        draw.ellipse((x-r, y-r, x+r, y+r), fill=(shade, shade, shade))

    # Render a large number using Pillow's default font, then scale it up.
    font = ImageDraw.Draw(Image.new("L", (1, 1)))._font
    text = str(number)
    bbox = font.getbbox(text)
    tw, th = max(1, bbox[2]-bbox[0]), max(1, bbox[3]-bbox[1])
    mask = Image.new("L", (tw + 20, th + 20), 0)
    md = ImageDraw.Draw(mask)
    md.text((10-bbox[0], 10-bbox[1]), text, fill=255, font=font)
    scale = 18
    mask = mask.resize((mask.width * scale, mask.height * scale), Image.Resampling.NEAREST)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=0.4))
    x = (w - mask.width) // 2
    y = (h - mask.height) // 2
    bg.paste((25, 25, 25), (x, y), mask)

    # Header/footer for clarity.
    draw = ImageDraw.Draw(bg)
    draw.rectangle((0, 0, w, 55), fill=(35, 35, 35))
    draw.rectangle((0, h-42, w, h), fill=(35, 35, 35))
    small = ImageDraw.Draw(Image.new("RGB", (1,1)))._font
    draw.text((20, 20), "PIT DIVERSÃO • DESAFIO VISUAL", fill=(255,255,255), font=small)
    draw.text((20, h-30), "Qual número aparece na imagem?", fill=(255,255,255), font=small)

    out = io.BytesIO()
    out.name = "desafio_numero.png"
    bg.save(out, format="PNG", optimize=True)
    out.seek(0)
    return out
