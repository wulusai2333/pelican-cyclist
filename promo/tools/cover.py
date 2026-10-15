#!/usr/bin/env python3
"""生成 B 站封面（1146x717，官方推荐比例）：主图在上，底部渐变文字带"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

OUT = Path(__file__).parent / "cover.png"
FRAME = Path(__file__).parent / "frames/s7-cine/f00060.jpg"
W, H = 1146, 717
BOLD = r"C:\Windows\Fonts\msyhbd.ttc"
REG = r"C:\Windows\Fonts\msyh.ttc"

src = Image.open(FRAME).convert("RGB")
sw, sh = src.size
ar = W / H
if sw / sh > ar:
    nw = int(sh * ar); src = src.crop(((sw - nw) // 2, 0, (sw - nw) // 2 + nw, sh))
else:
    nh = int(sw / ar); src = src.crop((0, (sh - nh) // 2, sw, (sh - nh) // 2 + nh))
src = src.resize((W, H), Image.LANCZOS)
src = ImageEnhance.Color(ImageEnhance.Brightness(src).enhance(1.08)).enhance(1.12)
im = src.convert("RGBA")

# 底部渐变黑带（自上而下加深），让文字压在图上也清晰
band = int(H * 0.42)
grad = Image.new("L", (1, H), 0)
for y in range(H):
    t = max(0.0, (y - (H - band)) / band)
    grad.putpixel((0, y), int(238 * (t ** 1.15)))
grad = grad.resize((W, H))
im = Image.composite(Image.new("RGBA", (W, H), (5, 8, 13, 255)), im, grad).convert("RGBA")

d = ImageDraw.Draw(im)
f1 = ImageFont.truetype(BOLD, 92)
f2 = ImageFont.truetype(REG, 36)
f3 = ImageFont.truetype(BOLD, 41)
f4 = ImageFont.truetype(REG, 31)
x = 56
y = H - 302
d.text((x, y), "鹈鹕骑自行车", font=f1, fill=(255, 255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0, 190))
y += 104
d.line([(x + 4, y), (x + 388, y)], fill=(95, 211, 228, 255), width=5)
y += 18
d.text((x, y), "Pelican Cyclist  ·  Three.js", font=f2, fill=(230, 240, 250, 255))
y += 52
d.text((x, y), "全部由 DeepSeek V4.1 Flash 一次性生成", font=f3, fill=(95, 211, 228, 255),
       stroke_width=2, stroke_fill=(0, 0, 0, 190))
y += 56
d.text((x, y), "单文件 1780 行 · 无模型 / 无贴图 / 无预渲染动画", font=f4, fill=(216, 230, 242, 255))

im.convert("RGB").save(OUT, quality=95)
print(f"{OUT}  {im.size}")
