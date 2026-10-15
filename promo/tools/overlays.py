#!/usr/bin/env python3
"""生成宣传视频用的字幕 / 标题 / 结尾图层（PNG + alpha），全部由代码绘制。"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).with_name("overlays")
OUT.mkdir(exist_ok=True)

W, H = 1920, 1080
BOLD = r"C:\Windows\Fonts\msyhbd.ttc"
REG = r"C:\Windows\Fonts\msyh.ttc"
MONO = r"C:\Windows\Fonts\consola.ttf"

ACCENT = (95, 211, 228, 255)
ACCENT2 = (255, 179, 92, 255)
WHITE = (240, 246, 252, 255)
DIM = (168, 186, 204, 255)
PANEL = (10, 14, 20, 200)

f_title = ImageFont.truetype(BOLD, 132)
f_sub = ImageFont.truetype(REG, 46)
f_hl = ImageFont.truetype(BOLD, 54)
f_small = ImageFont.truetype(REG, 36)
f_cap = ImageFont.truetype(BOLD, 50)
f_cap2 = ImageFont.truetype(REG, 34)
f_mono = ImageFont.truetype(MONO, 52)
f_mono2 = ImageFont.truetype(MONO, 40)


def new():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def center_text(d, y, text, font, fill, stroke=0, stroke_fill=(0, 0, 0, 200), spacing=0):
    """居中绘制，返回下一行的 y。spacing 用于手动字距。"""
    if spacing:
        widths = [d.textlength(c, font=font) for c in text]
        total = sum(widths) + spacing * (len(text) - 1)
        x = (W - total) / 2
        for c, w in zip(text, widths):
            d.text((x, y), c, font=font, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
            x += w + spacing
        return y + font.size + 12
    box = d.textbbox((0, 0), text, font=font)
    x = (W - (box[2] - box[0])) / 2 - box[0]
    d.text((x, y), text, font=font, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
    return y + (box[3] - box[1]) + 22


# --------------------------------------------------------------------------- 标题
def title_card():
    im = new()
    d = ImageDraw.Draw(im)
    # 背景柔光板，保证在明亮草原上也能读
    panel = Image.new("RGBA", (W, 560), (0, 0, 0, 0))
    pd = ImageDraw.Draw(panel)
    pd.rounded_rectangle([200, 40, W - 200, 520], radius=40, fill=(8, 12, 18, 132))
    im.alpha_composite(panel, (0, 150))
    d = ImageDraw.Draw(im)

    y = 300
    y = center_text(d, y, "鹈 鹕 骑 自 行 车", f_title, WHITE, stroke=3)
    d.line([(W / 2 - 260, y + 4), (W / 2 + 260, y + 4)], fill=ACCENT, width=3)
    y += 34
    y = center_text(d, y, "Pelican Cyclist  ·  Three.js", f_sub, DIM)
    y += 18
    center_text(d, y, "全部由 DeepSeek V4.1 Flash 一次性生成", f_hl, ACCENT, stroke=2)
    y += 88
    center_text(d, y, "单条中文需求  →  可直接运行的 3D 场景  ·  人类未写一行代码", f_small, WHITE)
    im.save(OUT / "title.png")
    print("title.png")


# --------------------------------------------------------------------------- 字幕条
def caption(name, line1, line2=None):
    im = new()
    d = ImageDraw.Draw(im)
    pad, x, bar = 34, 96, 10
    w1 = d.textlength(line1, font=f_cap)
    w2 = d.textlength(line2, font=f_cap2) if line2 else 0
    w = max(w1, w2) + pad * 2 + bar + 22
    h = 108 + (46 if line2 else 0)
    y = H - 132 - h
    d.rounded_rectangle([x, y, x + w, y + h], radius=20, fill=PANEL)
    d.rounded_rectangle([x, y, x + bar, y + h], radius=5, fill=ACCENT)
    d.text((x + bar + 24, y + 24), line1, font=f_cap, fill=WHITE)
    if line2:
        d.text((x + bar + 24, y + 84), line2, font=f_cap2, fill=DIM)
    im.save(OUT / f"{name}.png")
    print(f"{name}.png")


# --------------------------------------------------------------------------- 结尾
def outro():
    im = new()
    d = ImageDraw.Draw(im)
    veil = Image.new("RGBA", (W, H), (6, 9, 14, 172))
    im.alpha_composite(veil)
    d = ImageDraw.Draw(im)
    panel = Image.new("RGBA", (W - 320, 520), (0, 0, 0, 0))
    pd = ImageDraw.Draw(panel)
    pd.rounded_rectangle([0, 0, W - 320, 520], radius=44, outline=(95, 211, 228, 120), width=3, fill=(8, 12, 18, 165))
    im.alpha_composite(panel, (160, 280))
    d = ImageDraw.Draw(im)

    y = 340
    y = center_text(d, y, "github.com/wulusai2333/pelican-cyclist", f_mono, WHITE, stroke=2)
    y += 6
    y = center_text(d, y, "在线体验  wulusai2333.github.io/pelican-cyclist", f_mono2, ACCENT)
    y += 46
    d.line([(W / 2 - 420, y), (W / 2 + 420, y)], fill=(255, 255, 255, 60), width=2)
    y += 44
    y = center_text(d, y, "全部由 DeepSeek V4.1 Flash 一次性生成", f_hl, ACCENT2, stroke=2)
    y += 20
    center_text(d, y, "Three.js 单文件 80 KB / 1780 行  ·  无模型 无贴图 无 SVG 无预渲染动画", f_small, DIM)
    im.save(OUT / "outro.png")
    print("outro.png")


if __name__ == "__main__":
    title_card()
    caption("cap2", "全部几何由代码实时生成", "自写参数曲面：身体 / 喙 / 喉囊 / 羽片 / 车架 / 地形")
    caption("cap3", "双腿 IK 锁定脚踏：脚踏到哪，脚就在哪", "膝盖随行程屈伸 · 1/5 速慢动作")
    caption("cap4", "前轮绕真实头管轴转向 · 过弯自动侧倾", "侧倾角 = atan(v²κ/g)，与真实骑行一致")
    caption("cap5", "拖动时刻滑块：光色 / 雾 / 阴影 / 星空联动", "5:00 – 21:00 实时改变光照")
    caption("cap6", "点击鹈鹕 → 喉囊充气 + 鸣叫", "声音由 WebAudio 实时合成，无音频文件")
    caption("cap7", "6 种机位 · 键盘 / 鼠标 / 触屏全交互", "跟随 · 环绕 · 电影 · 正面 · 低角 · 特写")
    outro()
