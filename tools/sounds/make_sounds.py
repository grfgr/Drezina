"""
Процедурный синтез звуков дрезины (моно, 44.1 кГц, OGG Vorbis через ffmpeg).

  roll_loop.ogg        гул качения колёс по рельсам, бесшовная петля 4 с
  clack_1..3.ogg       удар колеса на стыке рельсов («та-так» — по разу на каждую ось)
  creak_1..4.ogg       скрип коромысла/шарнира (старое железо + сухое дерево)
  knock_1..2.ogg       глухой стук рычага в крайнем положении
  brake_loop.ogg       визг колодок при торможении, петля 2 с

Запуск:  python tools/sounds/make_sounds.py Drezina/sounds
"""
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np

SR = 44100
rng = np.random.default_rng(1890)


def t_axis(sec):
    return np.arange(int(sec * SR)) / SR


def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def bandpass(x, f, q):
    """Двухполюсный резонатор (biquad band-pass)."""
    w = 2 * np.pi * f / SR
    alpha = np.sin(w) / (2 * q)
    b0, b2 = alpha, -alpha
    a0, a1, a2 = 1 + alpha, -2 * np.cos(w), 1 - alpha
    b0, b2, a1, a2 = b0 / a0, b2 / a0, a1 / a0, a2 / a0
    y = np.zeros_like(x)
    x1 = x2 = y1 = y2 = 0.0
    for i, v in enumerate(x):
        out = b0 * v + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1 = x1, v
        y2, y1 = y1, out
        y[i] = out
    return y


def modes(sec, freqs, decays, amps, attack=0.0015):
    t = t_axis(sec)
    out = np.zeros_like(t)
    for f, d, a in zip(freqs, decays, amps):
        ph = rng.uniform(0, 2 * np.pi)
        out += a * np.sin(2 * np.pi * f * t + ph) * np.exp(-t / d)
    env = np.minimum(t / attack, 1.0)
    return out * env


def normalize(x, peak=0.89):
    m = np.max(np.abs(x)) or 1.0
    return x * (peak / m)


def fade(x, fin=0.003, fout=0.02):
    n_in, n_out = int(fin * SR), int(fout * SR)
    x = x.copy()
    if n_in:
        x[:n_in] *= np.linspace(0, 1, n_in)
    if n_out:
        x[-n_out:] *= np.linspace(1, 0, n_out)
    return x


def make_loop(x, xfade=0.4):
    """Бесшовная петля: конец плавно перетекает в начало."""
    n = int(xfade * SR)
    head, body, tail = x[:n], x[n:-n], x[-n:]
    w = np.linspace(0, 1, n)
    return np.concatenate([tail * (1 - w) + head * w, body])


def write_ogg(path, x, quality=6):
    pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp = f.name
    with wave.open(tmp, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-c:a", "libvorbis", "-q:a", str(quality), path],
                   check=True)
    os.remove(tmp)


# ----------------------------------------------------------------------------- звуки

def roll_loop():
    sec = 4.4
    t = t_axis(sec)
    noise = rng.standard_normal(len(t))
    rumble = lowpass(lowpass(noise, 140), 140) * 6.0            # низкий гул
    grit = bandpass(noise, 900, 1.2) * 0.25                      # шуршание реборд
    # колесо чуть «бьёт» (неровный бандаж): модуляция ~3.1 Гц
    wobble = 1 + 0.25 * np.sin(2 * np.pi * 3.1 * t) + 0.1 * np.sin(2 * np.pi * 6.2 * t + 1)
    hum = 0.18 * np.sin(2 * np.pi * 72 * t) + 0.08 * np.sin(2 * np.pi * 144 * t + 0.5)
    ring = bandpass(noise, 2350, 30) * 0.5 + bandpass(noise, 3900, 40) * 0.25   # звон рельса
    x = (rumble + hum) * wobble + grit + ring
    return normalize(make_loop(x), 0.7)


def clack(variant):
    sec = 0.55
    t = t_axis(sec)
    base = [380, 1060, 2240, 3480]
    jitter = 1 + (variant - 1) * 0.04
    metal = modes(sec, [f * jitter for f in base], [0.09, 0.05, 0.035, 0.02], [0.6, 0.45, 0.3, 0.15])
    thump = modes(sec, [62 * jitter, 95], [0.07, 0.05], [1.0, 0.5], attack=0.002)
    burst = rng.standard_normal(len(t)) * np.exp(-t / 0.006) * 0.8
    x = metal + thump + bandpass(burst, 1800, 0.8)
    return normalize(fade(x, 0.0005, 0.08))


def creak(variant):
    """Скрип: stick-slip — серия импульсов с плавающей частотой через резонаторы."""
    sec = 0.45 + 0.12 * variant
    t = t_axis(sec)
    n = len(t)
    rate0, rate1 = [(18, 34), (40, 22), (26, 48), (30, 30)][variant - 1]
    rate = np.linspace(rate0, rate1, n) * (1 + 0.15 * np.sin(2 * np.pi * 3 * t))
    phase = np.cumsum(rate / SR)
    pulses = np.zeros(n)
    idx = np.nonzero(np.diff(np.floor(phase)) > 0)[0]
    pulses[idx] = rng.uniform(0.6, 1.0, len(idx))
    f1 = [720, 980, 610, 1250][variant - 1]
    x = bandpass(pulses, f1, 18) + bandpass(pulses, f1 * 2.13, 25) * 0.6 + bandpass(pulses, f1 * 3.4, 30) * 0.3
    # «дерево»: глухая составляющая
    x += bandpass(pulses, 240, 5) * 0.4
    env = np.sin(np.pi * np.clip(t / sec, 0, 1)) ** 0.7
    return normalize(fade(x * env, 0.01, 0.05), 0.8)


def knock(variant):
    sec = 0.35
    t = t_axis(sec)
    j = 1 + (variant - 1) * 0.07
    x = modes(sec, [140 * j, 310 * j, 820 * j], [0.05, 0.035, 0.02], [1.0, 0.6, 0.3], attack=0.001)
    x += bandpass(rng.standard_normal(len(t)) * np.exp(-t / 0.004), 1200, 1.0) * 0.6
    return normalize(fade(x, 0.0005, 0.05), 0.75)


def brake_loop():
    sec = 2.4
    t = t_axis(sec)
    vib = 1 + 0.012 * np.sin(2 * np.pi * 6.5 * t) + 0.006 * np.sin(2 * np.pi * 13.7 * t)
    f = 2900
    tone = np.sin(2 * np.pi * f * np.cumsum(vib) / SR) * 0.5 + np.sin(2 * np.pi * 2 * f * np.cumsum(vib) / SR) * 0.15
    am = 0.6 + 0.4 * np.abs(np.sin(2 * np.pi * 1.7 * t))
    scrape = bandpass(rng.standard_normal(len(t)), 1500, 1.5) * 0.35
    x = tone * am + scrape
    return normalize(make_loop(x, 0.3), 0.55)


def main():
    out = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "Drezina/sounds")
    os.makedirs(out, exist_ok=True)
    write_ogg(os.path.join(out, "roll_loop.ogg"), roll_loop())
    for v in (1, 2, 3):
        write_ogg(os.path.join(out, f"clack_{v}.ogg"), clack(v))
    for v in (1, 2, 3, 4):
        write_ogg(os.path.join(out, f"creak_{v}.ogg"), creak(v))
    for v in (1, 2):
        write_ogg(os.path.join(out, f"knock_{v}.ogg"), knock(v))
    write_ogg(os.path.join(out, "brake_loop.ogg"), brake_loop())
    print("[Drezina] sounds written to", out)


if __name__ == "__main__":
    main()
