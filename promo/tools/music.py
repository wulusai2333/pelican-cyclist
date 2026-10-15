#!/usr/bin/env python3
"""程序生成宣传片配乐（无版权素材，全部由代码合成）。

结构：Am - F - C - G 循环，92 BPM
  pad   柔和锯齿垫（每小节一个三和弦）
  bass  根音（1、3 拍）
  arp   八分音符琶音
  kick  1、3 拍
  hat   反拍沙锤
外加一声"鹈鹕鸣叫"——按 index.html 里 WebAudio 图的实际参数复刻：
  168Hz 锯齿 + 252Hz 方波 + 336Hz 锯齿，频率在 0.45s 内降到 0.62 倍，
  过低通（1500→480Hz, Q=5），包络 35ms 起音 + 0.4s 后指数衰减。
"""
import argparse
import wave

import numpy as np

SR = 44100


def env(n, a, d, s=0.0, r=0.0, sustain=1.0):
    """简化 ADSR（样本数）"""
    e = np.zeros(n)
    ai = min(n, int(a * SR))
    e[:ai] = np.linspace(0, 1, ai, endpoint=False)
    di = min(n - ai, int(d * SR))
    if di > 0:
        e[ai:ai + di] = np.linspace(1, sustain, di, endpoint=False)
    e[ai + di:] = sustain
    if r > 0:
        ri = min(n, int(r * SR))
        e[n - ri:] *= np.linspace(1, 0, ri)
    return e


def saw(f, t):
    return 2.0 * ((f * t) % 1.0) - 1.0


def sine(f, t):
    return np.sin(2 * np.pi * f * t)


def lowpass_fir(x, fc, taps=129):
    """窗函数法 FIR 低通（卷积实现，够快）"""
    n = np.arange(taps) - (taps - 1) / 2
    h = np.sinc(2 * fc / SR * n) * np.hamming(taps)
    h /= h.sum()
    return np.convolve(x, h, mode='same')


def bandpass_fir(x, f0, bw, taps=129):
    n = np.arange(taps) - (taps - 1) / 2
    lo = (f0 - bw / 2) / SR
    hi = (f0 + bw / 2) / SR
    h = 2 * hi * np.sinc(2 * hi * n) - 2 * lo * np.sinc(2 * lo * n)
    h *= np.hamming(taps)
    h /= np.abs(h).sum()
    return np.convolve(x, h, mode='same')


def note(freq, dur, kind='sine', amp=1.0, attack=0.01, decay=0.3):
    n = int(dur * SR)
    t = np.arange(n) / SR
    if kind == 'saw':
        w = saw(freq, t) * 0.5 + saw(freq * 1.005, t) * 0.5
    elif kind == 'tri':
        w = 2 / np.pi * np.arcsin(np.sin(2 * np.pi * freq * t))
    elif kind == 'pluck':
        w = sine(freq, t) + 0.35 * sine(freq * 2, t) + 0.12 * sine(freq * 3, t)
    else:
        w = sine(freq, t)
    e = env(n, attack, decay, sustain=0.35 if kind == 'saw' else 0.05)
    return w * e * amp


def honk(dur=0.75):
    """复刻 index.html 里的鸣叫合成"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    k = np.clip(t / 0.45, 0, 1)
    drop = 1.0 - 0.38 * k                                   # 频率降到 0.62 倍
    x = np.zeros(n)
    for f, a in ((168, 0.55), (252, 0.30), (336, 0.18)):
        ph = 2 * np.pi * np.cumsum(f * drop) / SR
        # 正弦 + 方波成分 → 与页面里 sawtooth/square 振荡器叠加的音色接近
        x += a * (0.7 * np.sin(ph) + 0.3 * np.sign(np.sin(ph)))
    x = lowpass_fir(x, 1100, taps=97)
    # 噪声成分（气声）
    rng = np.random.default_rng(7)
    nz = rng.normal(0, 1, n) * np.power(np.clip(1 - t / dur, 0, 1), 2.5)
    x += 0.16 * bandpass_fir(nz, 700, 900, taps=97)
    # 包络：35ms 起音，0.4s 后指数衰减
    e = np.ones(n)
    ai = int(0.035 * SR)
    e[:ai] = np.linspace(0, 1, ai)
    tail = t > 0.40
    e[tail] = np.exp(-(t[tail] - 0.40) / 0.10)
    e[:int(0.01 * SR)] = 0
    return x * e * 0.5


def build(dur, honks):
    N = int((dur + 0.6) * SR)
    t = np.arange(N) / SR
    out = np.zeros(N)

    bpm = 92.0
    beat = 60.0 / bpm
    bar = beat * 4
    # Am - F - C - G
    chords = [
        ([220.00, 261.63, 329.63], 110.00),
        ([174.61, 220.00, 261.63], 87.31),
        ([196.00, 261.63, 329.63], 130.81),
        ([196.00, 246.94, 293.66], 98.00),
    ]
    nbars = int(np.ceil(dur / bar)) + 1

    def put(sig, at):
        i = int(at * SR)
        j = min(N, i + len(sig))
        if i < N:
            out[i:j] += sig[:j - i]

    for b in range(nbars):
        t0 = b * bar
        if t0 > dur:
            break
        notes, root = chords[b % 4]
        # pad：整小节，慢起音
        for f in notes:
            put(note(f, bar * 1.05, 'saw', amp=0.055, attack=0.5, decay=0.8), t0)
        # bass：1、3 拍
        for k in (0, 2):
            put(note(root, beat * 1.6, 'tri', amp=0.30, attack=0.012, decay=0.55), t0 + k * beat)
        # arp：八分音符
        seq = [notes[0], notes[1], notes[2], notes[1], notes[2], notes[0], notes[1], notes[2]]
        for k in range(8):
            f = seq[k] * 2
            put(note(f, beat * 0.5, 'pluck', amp=0.085, attack=0.004, decay=0.18), t0 + k * beat * 0.5)
        # kick：1、3 拍
        for k in (0, 2):
            kn = int(0.22 * SR)
            kt = np.arange(kn) / SR
            fk = 120 * np.exp(-kt * 26) + 45
            kick = np.sin(2 * np.pi * np.cumsum(fk) / SR) * np.exp(-kt * 13) * 0.55
            put(kick, t0 + k * beat)
        # hat：反拍
        rng = np.random.default_rng(b)
        for k in range(4):
            hn = int(0.07 * SR)
            ht = np.arange(hn) / SR
            hat = bandpass_fir(rng.normal(0, 1, hn), 8000, 6000, taps=41) * np.exp(-ht * 90) * 0.10
            put(hat, t0 + k * beat + beat * 0.5)

    for h in honks:
        put(honk(), h)

    # 母带：轻低通 + 软限幅 + 淡入淡出
    out = lowpass_fir(out, 11000, taps=65)
    out = np.tanh(out * 1.25) * 0.82
    fi = int(1.5 * SR)
    out[:fi] *= np.linspace(0, 1, fi) ** 1.5
    fo = int(2.8 * SR)
    out[-fo:] *= np.linspace(1, 0, fo) ** 1.2
    out *= 0.94 / max(1e-9, np.abs(out).max())
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--dur", type=float, required=True)
    ap.add_argument("--honks", default="")
    a = ap.parse_args()
    hs = [float(x) for x in a.honks.split(",") if x.strip()]
    y = build(a.dur, hs)
    pcm = np.int16(np.clip(y, -1, 1) * 32767)
    with wave.open(a.out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    rms = float(np.sqrt(np.mean(y ** 2)))
    print(f"{a.out}  {len(y)/SR:.2f}s  peak={np.abs(y).max():.3f}  rms={rms:.4f} ({20*np.log10(rms+1e-9):.1f} dBFS)  honks={hs}")
