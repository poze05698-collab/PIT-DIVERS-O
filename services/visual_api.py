import io
import json
import random
import urllib.parse
import urllib.request
from PIL import Image, ImageFilter, ImageDraw, ImageFont

COMMONS = "https://commons.wikimedia.org/w/api.php"
TOPICS = ["dog", "cat", "lion", "football", "Brazil flag", "car", "airplane", "pizza", "hamburger", "guitar", "Eiffel Tower", "mountain", "elephant", "shark", "apple", "banana", "motorcycle", "basketball", "soccer ball", "parrot"]


def _font(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"):
        try: return ImageFont.truetype(p, size)
        except OSError: pass
    return ImageFont.load_default()


def fetch_visual():
    topic = random.choice(TOPICS)
    params = {"action":"query","format":"json","generator":"search","gsrsearch":topic,"gsrnamespace":6,"gsrlimit":10,"prop":"imageinfo","iiprop":"url|mime|extmetadata","iiurlwidth":900}
    url = COMMONS + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=10) as r:
        data = json.loads(r.read().decode("utf-8"))
    pages = list((data.get("query", {}).get("pages") or {}).values())
    random.shuffle(pages)
    for p in pages:
        info = (p.get("imageinfo") or [{}])[0]
        mime = info.get("mime", "")
        image_url = info.get("thumburl") or info.get("url")
        if not image_url or not mime.startswith("image/") or "svg" in mime:
            continue
        try:
            with urllib.request.urlopen(image_url, timeout=12) as r:
                raw = r.read()
            img = Image.open(io.BytesIO(raw)).convert("RGB")
            if img.width < 250 or img.height < 180:
                continue
            img.thumbnail((900, 600), Image.Resampling.LANCZOS)
            clear = io.BytesIO(); img.save(clear, format="JPEG", quality=88); clear.seek(0)
            blurred = img.filter(ImageFilter.GaussianBlur(radius=18))
            overlay = ImageDraw.Draw(blurred)
            overlay.rounded_rectangle((25,25,min(875,blurred.width-25),min(110,blurred.height-25)), radius=20, fill=(0,0,0))
            overlay.text((45,48), "🔒 IMAGEM SECRETA", font=_font(28), fill=(255,255,255))
            b = io.BytesIO(); blurred.save(b, format="JPEG", quality=82); b.seek(0)
            title = p.get("title", "").replace("File:", "").replace("_", " ").rsplit(".",1)[0].strip()
            return {"clear": clear.getvalue(), "blurred": b.getvalue(), "url": image_url, "title": title or topic.title()}
        except Exception:
            continue
    return None
