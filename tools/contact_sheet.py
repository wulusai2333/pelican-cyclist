#!/usr/bin/env python3
"""把多张截图拼成一张对比图（用于一屏核查动作的多个相位）。

用法:
    python tools/contact_sheet.py out.png a.png b.png c.png d.png [--cols 2] [--scale 0.52]
"""
import argparse
from pathlib import Path

from PIL import Image


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("images", nargs="+")
    ap.add_argument("--cols", type=int, default=2)
    ap.add_argument("--scale", type=float, default=0.52)
    ap.add_argument("--bg", default="101216")
    args = ap.parse_args()

    ims = [Image.open(p).convert("RGB") for p in args.images]
    w, h = ims[0].size
    tw, th = max(1, int(w * args.scale)), max(1, int(h * args.scale))
    rows = (len(ims) + args.cols - 1) // args.cols
    sheet = Image.new("RGB", (tw * args.cols, th * rows), tuple(bytes.fromhex(args.bg)))
    for i, im in enumerate(ims):
        sheet.paste(im.resize((tw, th), Image.LANCZOS), ((i % args.cols) * tw, (i // args.cols) * th))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(f"{out} {sheet.size[0]}x{sheet.size[1]}")


if __name__ == "__main__":
    main()
