"""Текстуры насыпи входа под землю карты NHChernobyl.
metro_grass_co/nohq — бесшовный тайл из снимка земли карты (src/nhchernobyl_ground.png),
metro_soil_co — та же земля темнее и без травинок (проплешины),
metro_drygrass_ca — пучки тёмной травы (как кустики травы на карте), альфа по травинкам.
Запуск: python3 tools/textures/make_mound_textures.py"""
import os, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "Drezina", "data", "textures")


def seamless(a):
    """Тайл без швов: середина — исходник, к краям плавно переходит в сдвинутую на полтайла копию."""
    h, w = a.shape[:2]
    b = np.roll(np.roll(a, h // 2, 0), w // 2, 1)
    yy = np.abs(np.linspace(-1, 1, h))[:, None]
    xx = np.abs(np.linspace(-1, 1, w))[None, :]
    m = np.clip((1 - np.maximum(xx, yy)) / 0.45, 0, 1)
    m = (m * m * (3 - 2 * m))[..., None]
    return a * m + b * (1 - m)


def normal_from(gray, strength=2.5):
    gy, gx = np.gradient(gray)
    nx, ny, nz = -gx * strength, -gy * strength, np.ones_like(gray)
    l = np.sqrt(nx * nx + ny * ny + nz * nz)
    n = np.stack([nx / l, ny / l, nz / l], -1)
    return ((n * 0.5 + 0.5) * 255).clip(0, 255).astype(np.uint8)


def ground():
    src = np.array(Image.open(os.path.join(HERE, "src", "nhchernobyl_ground.png")).convert("RGB")).astype(np.float32)
    # нижняя середина снимка — ближе к камере, почти без перспективы
    crop = src[120:1080, 480:1440]
    t = seamless(crop)
    t = np.array(Image.fromarray(t.clip(0, 255).astype(np.uint8)).resize((1024, 1024), Image.LANCZOS)).astype(np.float32)
    t = (t * 0.68).clip(0, 255)                      # снимок уже освещён, в игре свет ложится ещё раз — темнее (1.08 было слишком светло)
    Image.fromarray(t.astype(np.uint8)).save(os.path.join(OUT, "metro_grass_co.png"))
    gray = t.mean(-1) / 255.0
    Image.fromarray(normal_from(gray)).save(os.path.join(OUT, "metro_grass_nohq.png"))
    # проплешины: та же земля, травинки размыты и притушены — тёмный бурый грунт
    blur = np.array(Image.fromarray(t.astype(np.uint8)).filter(ImageFilter.GaussianBlur(3))).astype(np.float32)
    soil = blur * np.array([0.72, 0.62, 0.55]) + t * 0.12
    rr = np.random.RandomState(7)
    grain = np.array(Image.fromarray((rr.rand(256, 256) * 255).astype(np.uint8)).resize((1024, 1024), Image.BICUBIC)).astype(np.float32) / 255.0
    soil *= (0.85 + 0.3 * grain)[..., None]
    soil = seamless(soil)
    Image.fromarray(soil.clip(0, 255).astype(np.uint8)).save(os.path.join(OUT, "metro_soil_co.png"))
    Image.fromarray(normal_from(soil.mean(-1) / 255.0, 3.0)).save(os.path.join(OUT, "metro_soil_nohq.png"))


def tufts():
    """Пучки: густые изогнутые травинки от низа, тёмно-оливковые и бурые, кончики светлее (без «колосков»)."""
    S = 4
    N = 512 * S
    im = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    rnd = random.Random(5)
    # тёмные: пучки освещаются сверху как земля и в игре выходят заметно светлее текстуры
    cols = [(22, 28, 12), (27, 32, 14), (32, 35, 17), (37, 36, 19), (45, 39, 22), (54, 46, 26), (30, 26, 15)]
    for i in range(900):
        x0 = rnd.gauss(N * 0.5, N * 0.2)
        x0 = min(max(x0, N * 0.04), N * 0.96)
        h = N * rnd.uniform(0.35, 0.95)
        lean = rnd.uniform(-0.45, 0.45) * h
        w = S * rnd.uniform(5, 11)
        c = rnd.choice(cols)
        tipc = tuple(min(255, int(v * rnd.uniform(1.1, 1.35))) for v in c)
        steps = 14
        prev = (x0, N - 1)
        for k in range(1, steps + 1):
            t = k / steps
            x = x0 + lean * t * t
            y = N - 1 - h * t
            ww = max(S, w * (1 - t * 0.85))
            cc = tuple(int(c[j] + (tipc[j] - c[j]) * t) for j in range(3)) + (255,)
            d.line([prev, (x, y)], fill=cc, width=int(ww))
            prev = (x, y)
    im = im.resize((512, 512), Image.LANCZOS)
    a = np.array(im)
    a[..., 3] = np.where(a[..., 3] > 110, 255, 0)     # чёткий край (альфа-тест)
    # цвет под прозрачными пикселями — средний, чтобы на мипах не было светлой каймы
    mean = a[a[..., 3] > 0][:, :3].mean(0)
    a[a[..., 3] == 0, :3] = mean
    Image.fromarray(a).save(os.path.join(OUT, "metro_drygrass_ca.png"))


if __name__ == "__main__":
    ground()
    tufts()
    print("ok")
