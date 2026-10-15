#!/usr/bin/env python3
"""把抓好的帧 + 字幕层 + 程序化配乐合成为 B 站投稿用的 mp4。

- 帧序列按 frames/<seg>/meta.json 的 dt 拼成 VFR → 统一 20fps 输出
- 字幕/标题/结尾为带 alpha 的 PNG，按分镜时间轴叠加
- 音轨由 music.py 现场合成（含与画面同步的两声鹈鹕鸣叫）
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
FRAMES = ROOT / "frames"
OVER = ROOT / "overlays"
OUT = ROOT / "pelican-promo.mp4"
FPS = 20

ORDER = ["s1-chase", "s2-orbit", "s3-legs", "s4-low", "s5-sunset", "s6-honk", "s7-cine", "s8-outro"]
# 每个分镜叠加哪张字幕（None = 只叠标题/结尾）
CAPS = {"s1-chase": "title", "s2-orbit": "cap2", "s3-legs": "cap3", "s4-low": "cap4",
        "s5-sunset": "cap5", "s6-honk": "cap6", "s7-cine": "cap7", "s8-outro": "outro"}


def main() -> None:
    # ---------- 1. 读时间轴 ----------
    entries, t = [], 0.0
    spans = {}
    for sid in ORDER:
        meta = json.loads((FRAMES / sid / "meta.json").read_text(encoding="utf-8"))
        n, dt = meta["frames"], float(meta["dt"])
        start = t
        files = sorted((FRAMES / sid).glob("f*.jpg"))
        assert len(files) >= n, f"{sid}: 需要 {n} 帧，实际 {len(files)}"
        for i in range(n):
            entries.append((files[i], dt))
            t += dt
        spans[sid] = (start, t)
    total = t
    print(f"共 {len(entries)} 帧，成片 {total:.2f}s")
    for sid in ORDER:
        print(f"  {sid:10s} {spans[sid][0]:6.2f} → {spans[sid][1]:6.2f}")

    # ---------- 2. 音轨（鸣叫对齐 s6 的两次点击） ----------
    s6s = spans["s6-honk"][0]
    honks = [s6s + 1.2, s6s + 3.8]
    music = ROOT / "music.wav"
    subprocess.run([sys.executable, str(ROOT / "music.py"), str(music),
                    "--dur", f"{total:.3f}", "--honks", ",".join(f"{h:.2f}" for h in honks)], check=True)

    # ---------- 3. concat 列表 ----------
    lines = []
    for f, dt in entries:
        lines.append(f"file '{f.as_posix().replace('F:/Game/ComfyUI/_video/', '')}'")
        lines.append(f"duration {dt:.4f}")
    lines.append(f"file '{entries[-1][0].as_posix().replace('F:/Game/ComfyUI/_video/', '')}'")
    (ROOT / "concat.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ---------- 4. 滤镜图 ----------
    inputs = ["-f", "concat", "-safe", "0", "-i", "concat.txt"]
    caps = []
    for i, sid in enumerate(ORDER):
        p = OVER / f"{CAPS[sid]}.png"
        inputs += ["-loop", "1", "-i", str(p)]
        caps.append((i + 1, spans[sid][0], spans[sid][1], CAPS[sid]))
    inputs += ["-i", str(music)]
    aidx = len(ORDER) + 1

    fc = [f"[0:v]fps={FPS},scale=1920:1080,setsar=1[base]"]
    prev = "base"
    for k, (idx, a, b, name) in enumerate(caps):
        fi, fo = (0.0, min(0.7, (b - a) * 0.25)) if name == "title" else (0.45, 0.45)
        st_in, st_out = a, b - fo
        fc.append(f"[{idx}:v]format=rgba,fade=t=in:st={st_in:.2f}:d={fi:.2f}:alpha=1,"
                  f"fade=t=out:st={st_out:.2f}:d={fo:.2f}:alpha=1[o{k}]")
        out = f"v{k}"
        fc.append(f"[{prev}][o{k}]overlay=0:0:enable='between(t,{a:.2f},{b:.2f})'[{out}]")
        prev = out
    filter_complex = ";".join(fc)

    cmd = (["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning", "-stats"] + inputs +
           ["-filter_complex", filter_complex, "-map", f"[{prev}]", "-map", f"{aidx}:a",
            "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-pix_fmt", "yuv420p",
            "-r", str(FPS), "-movflags", "+faststart",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
            "-t", f"{total:.3f}", str(OUT)])
    print("ffmpeg …")
    subprocess.run(cmd, check=True, cwd=ROOT)
    print(f"完成 → {OUT}  ({OUT.stat().st_size/1024/1024:.1f} MB)")


if __name__ == "__main__":
    main()
