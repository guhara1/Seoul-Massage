# -*- coding: utf-8 -*-
"""Generate brand favicon/PWA/OG images (rose-gold gradient). Run: python3 tools/gen_icons.py"""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BG = (11, 11, 14)
G0, G1, G2 = (244, 210, 156), (233, 184, 167), (201, 138, 107)

def lerp(a, b, t): return tuple(round(a[i] + (b[i]-a[i])*t) for i in range(3))

def grad(size):
    img = Image.new("RGB", (size, size), BG)
    px = img.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2*size)
            c = lerp(G0, G1, t*2) if t < .5 else lerp(G1, G2, (t-.5)*2)
            px[x, y] = c
    return img

def rounded(img, rad):
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, img.size[0]-1, img.size[1]-1], rad, fill=255)
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out

def font(sz):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"]:
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()

def icon(size, pad_ratio=.14, maskable=False):
    base = Image.new("RGBA", (size, size), (*BG, 255))
    pad = 0 if maskable else round(size*pad_ratio)
    inner = size - pad*2
    g = rounded(grad(inner), round(inner*0.22))
    base.alpha_composite(g, (pad, pad))
    d = ImageDraw.Draw(base)
    f = font(round(inner*0.62))
    d.text((size/2, size/2 - inner*0.04), "S", font=f, fill=(26, 18, 8), anchor="mm")
    return base

# PWA + apple
icon(192).save(os.path.join(ROOT, "icon-192.png"))
icon(512).save(os.path.join(ROOT, "icon-512.png"))
icon(512, maskable=True).save(os.path.join(ROOT, "icon-maskable-512.png"))
icon(180).save(os.path.join(ROOT, "apple-touch-icon.png"))
# favicon.ico (multi-size)
ico = icon(64)
ico.save(os.path.join(ROOT, "favicon.ico"), sizes=[(16,16),(32,32),(48,48),(64,64)])

# OG cover 1200x630
og = grad(1200).resize((1200, 630))
og = og.point(lambda v: round(v*0.20))  # darken
ov = Image.new("RGBA", (1200, 630), (0, 0, 0, 0))
d = ImageDraw.Draw(ov)
try:
    fb = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 72)
    fs = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 34)
except Exception:
    fb, fs = font(72), font(34)
d.text((220, 150), "Seoul 마사지", font=fb, fill=(243, 243, 245))
d.text((222, 250), "서울 전지역 출장마사지·홈타이 예약 안내 · 연중무휴 24시간", font=fs, fill=(154, 154, 163))
mark = rounded(grad(120), 26)
ov.alpha_composite(mark, (80, 110))
md = ImageDraw.Draw(ov)
md.text((140, 158), "S", font=font(70), fill=(26, 18, 8), anchor="mm")
out = Image.alpha_composite(og.convert("RGBA"), ov).convert("RGB")
os.makedirs(os.path.join(ROOT, "assets"), exist_ok=True)
out.save(os.path.join(ROOT, "assets", "og-cover.jpg"), quality=86)
print("Icons + OG generated.")
