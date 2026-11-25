"""
Процедурные текстуры для дрезины в стиле заброшенной постсоветской зоны: облупленная зелёная краска,
ржавчина, серое рассохшееся дерево, тёмная сталь, изолента, брезент, трафаретный номер.

  python tools/textures/make_textures.py Drezina/data/textures [размер]

На выходе PNG (*_co.png — цвет). Для игры: DayZ Tools -> ImageToPAA (png -> paa), пути в .rvmat/.p3d —
Drezina\\data\\textures\\<имя>_co.paa.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

rng = np.random.default_rng(17)


def noise(size, scale, octaves=5, persistence=0.5, stretch=(1, 1)):
    """Фрактальный шум 0..1 (апскейл случайных сеток, бикубика)."""
    out = np.zeros((size, size))
    amp, total = 1.0, 0.0
    for o in range(octaves):
        cells_x = max(2, int(size / scale * (2 ** o) / stretch[0]))
        cells_y = max(2, int(size / scale * (2 ** o) / stretch[1]))
        grid = rng.random((cells_y, cells_x)).astype(np.float32)
        img = Image.fromarray((grid * 255).astype(np.uint8)).resize((size, size), Image.BICUBIC)
        out += amp * (np.asarray(img, dtype=np.float32) / 255.0)
        total += amp
        amp *= persistence
    out /= total
    return (out - out.min()) / (out.max() - out.min() + 1e-6)


def lerp(a, b, t):
    t = t[..., None]
    return a * (1 - t) + b * t


def col(*rgb):
    return np.array(rgb, dtype=np.float32) / 255.0


def vanilla_grade(c, blur=0.9):
    """Под ванильные текстуры DayZ: приглушённые цвета, мягкий контраст, без пёстрого «шума»."""
    lum = c.mean(axis=2, keepdims=True)
    c = c * 0.55 + lum * 0.45                       # меньше насыщенности
    c = (c - 0.5) * 0.75 + 0.5 - 0.04              # мягче контраст, чуть темнее
    img = Image.fromarray((np.clip(c, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(img, dtype=np.float32) / 255.0


def save(arr, path):
    Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8)).save(path)


def streaks(size, density=0.6, length=0.35):
    """Вертикальные потёки (ржавчина/грязь стекает вниз)."""
    base = noise(size, 6, 3, stretch=(1, 40))
    drip = noise(size, 40, 4)
    m = np.clip((base - (1 - density)) * 3, 0, 1) * np.clip(drip * 1.5 - 0.3, 0, 1)
    img = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))
    return np.asarray(img, dtype=np.float32) / 255.0 * length * 2


def rust_tex(size):
    n1 = noise(size, 64, 6)
    n2 = noise(size, 12, 4)
    pits = (noise(size, 4, 2) > 0.78).astype(np.float32)
    c = lerp(col(70, 42, 26), col(118, 66, 36), n1)
    c = lerp(c, col(50, 32, 22), n2 * 0.6)
    c = lerp(c, col(138, 84, 46), np.clip(n1 - 0.7, 0, 1) * 1.5)
    c *= (1 - pits[..., None] * 0.35)
    return c


def paint_tex(size, paint_rgb):
    """Советская краска по металлу, облупилась до ржавчины, потёки и грязь."""
    rust = rust_tex(size)
    paint = lerp(col(*paint_rgb), col(*paint_rgb) * 0.75, noise(size, 48, 5))
    paint = lerp(paint, col(150, 150, 130), noise(size, 128, 3) * 0.25)       # выгорела
    chip = noise(size, 30, 6, 0.55)
    chip_mask = np.clip((chip - 0.71) * 9, 0, 1)                              # облупилось (редко, как у ванильных машин)
    edge = np.clip((chip - 0.67) * 9, 0, 1) - chip_mask                       # тёмный край скола
    c = lerp(paint, rust, chip_mask)
    c *= (1 - np.clip(edge, 0, 1)[..., None] * 0.35)
    c = lerp(c, col(90, 55, 32), np.clip(streaks(size), 0, 1) * 0.5)
    c = lerp(c, col(45, 40, 32), noise(size, 180, 3) ** 2 * 0.5)             # крупные пятна грязи, как на ванильных машинах
    return c


def wood_tex(size):
    """Рассохшиеся серые доски (волокна вдоль U после транспонирования), щели, сучки, пятна."""
    grain = noise(size, 3, 4, stretch=(1, 60))
    rings = np.sin(noise(size, 50, 3, stretch=(1, 8)) * 40) * 0.5 + 0.5
    c = lerp(col(98, 84, 66), col(140, 126, 104), grain * 0.7 + rings * 0.3)
    c = lerp(c, col(70, 58, 44), noise(size, 70, 5) * 0.5)
    c = lerp(c, col(150, 146, 136), noise(size, 120, 3) * 0.35)               # серость
    # щели между досками (каждые 1/4 ширины)
    x = np.arange(size)
    gap = (np.abs((x % (size // 4)) - 0) < size // 160).astype(np.float32)
    c *= (1 - gap[None, :, None] * 0.75)
    # сучки
    img = Image.fromarray((np.clip(c, 0, 1) * 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    for _ in range(int(size / 128)):
        cx, cy = rng.integers(0, size, 2)
        r = rng.integers(size // 120, size // 50)
        d.ellipse([cx - r, cy - r * 2, cx + r, cy + r * 2], fill=(55, 42, 30))
    c = np.asarray(img, dtype=np.float32) / 255.0
    c = lerp(c, col(95, 50, 25), np.clip(streaks(size, 0.3), 0, 1) * 0.6)   # ржавые потёки от болтов
    # волокна вдоль U: при кубической развёртке пола они идут вдоль досок (по X),
    # а щели через 1/4 тайла (~0.25 м) совпадают с шириной досок
    return np.transpose(c, (1, 0, 2))


def steel_tex(size):
    n = noise(size, 20, 5, stretch=(30, 1))
    c = lerp(col(48, 48, 50), col(92, 92, 96), n)
    c = lerp(c, rust_tex(size), np.clip(noise(size, 60, 5) - 0.55, 0, 1) * 2.2)
    c = lerp(c, col(30, 28, 25), noise(size, 40, 4) ** 4)                   # мазут
    return c


def tape_tex(size):
    n = noise(size, 8, 3, stretch=(1, 20))
    c = lerp(col(28, 28, 30), col(55, 55, 58), n)
    stripes = (np.sin(np.arange(size) / size * 2 * np.pi * 24) > 0.85).astype(np.float32)
    return lerp(c, col(20, 20, 20), stripes[:, None] * np.ones(size)[None, :] * 0.6)


def canvas_tex(size):
    """Армейский брезент: плотное полотняное плетение, выгоревшие складки, пятна масла и грязи, штопка."""
    x = np.arange(size)
    f = size / 1024 * 1.6
    weave = (np.sin(x / f)[None, :] * np.sin(x / f)[:, None]) * 0.5 + 0.5
    base = lerp(col(78, 82, 54), col(108, 110, 76), noise(size, 50, 5))
    c = base * (0.93 + 0.1 * weave[..., None])
    c = lerp(c, col(130, 128, 96), np.clip(noise(size, 160, 3) - 0.5, 0, 1) * 1.2)       # выгорело
    c = lerp(c, col(42, 38, 30), np.clip(noise(size, 90, 5) - 0.62, 0, 1) * 2.5)         # масло
    c = lerp(c, col(92, 76, 52), np.clip(noise(size, 30, 4) - 0.6, 0, 1) * 1.8)          # грязь
    return c


def leather_tex(size):
    """Старая кожа ремней: зерно, трещины, вытертые края."""
    grain = noise(size, 3, 3)
    cracks = np.clip((noise(size, 18, 5) - 0.72) * 6, 0, 1)
    c = lerp(col(60, 38, 22), col(98, 64, 36), noise(size, 40, 5) * 0.7 + grain * 0.3)
    c = lerp(c, col(28, 18, 10), cracks * 0.8)
    c = lerp(c, col(130, 96, 62), np.clip(noise(size, 120, 3) - 0.6, 0, 1) * 1.5)         # вытерто
    return c


def plate_tex(size):
    """Табличка с трафаретным номером и полосой."""
    c = paint_tex(size, (60, 78, 58))
    img = Image.fromarray((np.clip(c, 0, 1) * 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    try:
        font = ImageFont.truetype(font_path, size // 4)
        small = ImageFont.truetype(font_path, size // 10)
    except OSError:
        font = small = ImageFont.load_default()
    d.text((size * 0.08, size * 0.12), "ДР-17", font=font, fill=(205, 200, 180))
    d.text((size * 0.08, size * 0.55), "ПЧ-4  МПС СССР", font=small, fill=(205, 200, 180))
    d.rectangle([0, size * 0.82, size, size * 0.9], fill=(170, 40, 30))
    stencil = np.asarray(img, dtype=np.float32) / 255.0
    # трафарет облупился вместе с краской
    wear = np.clip((noise(size, 25, 5) - 0.6) * 6, 0, 1)
    return lerp(stencil, c, wear * 0.8)


def lamp_glass_tex(size):
    n = noise(size, 30, 4)
    return lerp(col(170, 140, 70), col(90, 70, 40), n * 0.8)


# ----------------------------------------------------------------------------- бункер / метро

def concrete_tex(size, base=(118, 116, 108)):
    """Бетон: опалубочные швы, раковины, сырые пятна, потёки."""
    c = lerp(col(*base) * 0.8, col(*base), noise(size, 40, 6))
    c = lerp(c, col(60, 60, 56), np.clip(noise(size, 100, 4) - 0.55, 0, 1) * 1.6)        # сырость
    pores = (noise(size, 3, 2) > 0.82).astype(np.float32)
    c *= (1 - pores[..., None] * 0.25)
    # швы опалубки каждые 1/3 тайла
    y = np.arange(size)
    seam = ((y % (size // 3)) < 3).astype(np.float32)
    c *= (1 - seam[:, None, None] * 0.25)
    c = lerp(c, col(70, 52, 35), np.clip(streaks(size, 0.5), 0, 1) * 0.5)                # ржавые потёки
    c = lerp(c, col(30, 30, 28), noise(size, 70, 5) ** 4 * 0.8)                           # копоть
    return c


def wall_two_tone_tex(size):
    """Стена 3 x 3 м: снизу советская зелёная масляная краска до 1.4 м, сверху побелка, всё облезло.
    Низ текстуры = пол (UV v=0)."""
    conc = concrete_tex(size)
    green = lerp(col(54, 84, 66), col(40, 64, 50), noise(size, 50, 5))
    white = lerp(col(178, 176, 164), col(150, 148, 136), noise(size, 60, 5))
    rows = np.arange(size)[:, None] / size                    # 0 вверху, 1 внизу
    band_top = 1 - 1.4 / 3.0
    is_green = (rows > band_top).astype(np.float32) * np.ones((1, size))
    paint = lerp(white, green, is_green)
    line = (np.abs(rows - band_top) < 0.006).astype(np.float32) * np.ones((1, size))
    paint = lerp(paint, col(30, 40, 32), line)
    peel = np.clip((noise(size, 35, 6) - 0.6) * 7, 0, 1)
    c = lerp(paint, conc, peel)
    c = lerp(c, col(60, 55, 40), np.clip(streaks(size, 0.7, 0.5), 0, 1) * (1 - rows) * 0.8)   # потёки сверху
    c = lerp(c, col(35, 32, 28), np.clip(rows - 0.85, 0, 1) * 4 * noise(size, 30, 4))         # грязь у пола
    return c


def hazard_tex(size):
    """Жёлто-чёрные диагональные полосы, затёртые и ржавые."""
    x = np.arange(size)
    diag = ((x[None, :] + x[:, None]) // (size // 6)) % 2
    c = np.where(diag[..., None] == 0, col(196, 156, 30), col(26, 24, 20))
    wear = np.clip((noise(size, 30, 6) - 0.62) * 6, 0, 1)
    c = lerp(c, rust_tex(size), wear)
    return lerp(c, col(40, 35, 28), noise(size, 80, 4) ** 3 * 0.6)


def door_tex(size):
    return paint_tex(size, (88, 98, 88))


def tubing_tex(size):
    """Чугунные тюбинги: тёмный металл, ржавчина, известковые потёки."""
    c = lerp(col(40, 40, 40), col(66, 64, 60), noise(size, 30, 5))
    c = lerp(c, rust_tex(size), np.clip(noise(size, 50, 5) - 0.45, 0, 1) * 1.8)
    c = lerp(c, col(170, 165, 150), np.clip(streaks(size, 0.4, 0.4), 0, 1) * 0.6)
    return c


def dirt_tex(size):
    c = lerp(col(58, 48, 34), col(84, 72, 52), noise(size, 30, 6))
    c = lerp(c, col(60, 72, 40), np.clip(noise(size, 60, 4) - 0.5, 0, 1) * 1.5)          # мох/трава
    return c


def sign_tex(size, lines, bg=(150, 30, 25), fg=(225, 220, 205)):
    w, h = size, size // 2
    img = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(img)
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    fs = h // (len(lines) + 1)
    try:
        font = ImageFont.truetype(font_path, fs)
        while fs > 8 and max(d.textlength(t, font=font) for t in lines) > w * 0.88:
            fs -= 2
            font = ImageFont.truetype(font_path, fs)
    except OSError:
        font = ImageFont.load_default()
    line_h = h / len(lines)
    for i, t in enumerate(lines):
        tw = d.textlength(t, font=font)
        d.text(((w - tw) / 2, line_h * i + (line_h - fs) / 2 - fs * 0.1), t, font=font, fill=fg)
    a = np.asarray(img, dtype=np.float32) / 255.0
    wear = np.clip((noise(h, 20, 5)[:, :] - 0.6) * 5, 0, 1)
    wear = np.asarray(Image.fromarray((wear * 255).astype(np.uint8)).resize((w, h)), dtype=np.float32) / 255.0
    rust = np.asarray(Image.fromarray((rust_tex(h) * 255).astype(np.uint8)).resize((w, h)), dtype=np.float32) / 255.0
    return lerp(a, rust, wear * 0.85)


def ballast_tex(size):
    """Щебень: угловатые камни разного серого, тени между ними, мазутные пятна."""
    rng_l = np.random.default_rng(65)
    n_pts = int(size * size / 120)
    pts = rng_l.random((n_pts, 2)) * size
    shade = rng_l.uniform(0.55, 1.0, n_pts)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    best = np.full((size, size), 1e9, dtype=np.float32)
    second = np.full((size, size), 1e9, dtype=np.float32)
    idx = np.zeros((size, size), dtype=np.int32)
    for k in range(n_pts):
        px, py = pts[k]
        dx = np.abs(xx - px)
        dy = np.abs(yy - py)
        dx = np.minimum(dx, size - dx)                 # бесшовно
        dy = np.minimum(dy, size - dy)
        d = np.maximum(dx * 0.8 + dy * 0.45, dy * 0.8 + dx * 0.45)   # угловатые камни
        closer = d < best
        second = np.where(closer, best, np.minimum(second, d))
        idx = np.where(closer, k, idx)
        best = np.where(closer, d, best)
    edge = np.clip((second - best) / 3.0, 0, 1) ** 0.6  # мягкая тень на стыке камней
    tone = shade[idx]
    base = lerp(col(78, 76, 72), col(146, 142, 134), tone)
    base = lerp(base, col(120, 92, 70), (rng_l.random(n_pts)[idx] > 0.85).astype(np.float32) * 0.45)  # ржавые камни
    facet = noise(size, 3, 2)                               # шероховатость граней
    c = base * (0.55 + 0.45 * edge[..., None]) * (0.85 + 0.3 * facet[..., None])
    c = lerp(c, col(25, 22, 18), noise(size, 90, 4) ** 3 * 0.7)            # мазут
    return c


def railtop_tex(size):
    """Поверхность катания: накатанная до блеска сталь с продольными полосами."""
    n = noise(size, 4, 3, stretch=(40, 1))
    c = lerp(col(120, 122, 126), col(185, 188, 192), n)
    return lerp(c, col(90, 70, 55), noise(size, 50, 4) ** 4 * 0.5)


def tile_tex(size):
    """Кафель платформы 4x4 плитки на тайл: грязные швы, сколы, трещины."""
    c = lerp(col(150, 146, 132), col(120, 118, 106), noise(size, 40, 5))
    x = np.arange(size)
    seam = ((x % (size // 4)) < 4).astype(np.float32)
    grid = np.maximum(seam[None, :], seam[:, None])
    c = lerp(c, col(55, 52, 45), grid)
    chips = np.clip((noise(size, 18, 5) - 0.72) * 8, 0, 1)
    c = lerp(c, concrete_tex(size) * 0.8, chips)
    return lerp(c, col(40, 38, 32), noise(size, 80, 4) ** 3 * 0.7)


RVMAT = """ambient[] = {1, 1, 1, 1};
diffuse[] = {1, 1, 1, 1};
forcedDiffuse[] = {0, 0, 0, 0};
emmisive[] = {%(emissive)s};
specular[] = {%(spec)s, %(spec)s, %(spec)s, 1};
specularPower = %(power)s;
PixelShaderID = "Super";
VertexShaderID = "Super";
class Stage1
{
	texture = "#(argb,8,8,3)color(0.5,0.5,1,1,NOHQ)";
	uvSource = "tex";
};
class Stage2
{
	texture = "#(argb,8,8,3)color(0.5,0.5,0.5,1,DT)";
	uvSource = "tex";
};
class Stage3
{
	texture = "#(argb,8,8,3)color(0,0,0,0,MC)";
	uvSource = "tex";
};
class Stage4
{
	texture = "#(argb,8,8,3)color(1,1,1,1,AS)";
	uvSource = "tex";
};
class Stage5
{
	texture = "#(argb,8,8,3)color(%(metal)s,%(gloss)s,1,1,SMDI)";
	uvSource = "tex";
};
class Stage6
{
	texture = "#(ai,64,64,1)fresnel(1.5,0.4)";
	uvSource = "none";
};
class Stage7
{
	texture = "dz\\data\\data\\env_land_co.paa";
	uvSource = "none";
};
"""

# материал -> (блеск, сила блика, металл, глянец, свечение)
RVMAT_PARAMS = {
    "drezina_paint_green": (0.12, 40, 0.3, 0.35, "0, 0, 0, 1"),
    "drezina_paint_blue": (0.12, 40, 0.3, 0.35, "0, 0, 0, 1"),
    "drezina_rust": (0.04, 15, 0.2, 0.15, "0, 0, 0, 1"),
    "drezina_wood": (0.03, 10, 0.0, 0.1, "0, 0, 0, 1"),
    "drezina_steel": (0.3, 80, 0.8, 0.55, "0, 0, 0, 1"),
    "drezina_tape": (0.08, 30, 0.0, 0.3, "0, 0, 0, 1"),
    "drezina_canvas": (0.02, 8, 0.0, 0.05, "0, 0, 0, 1"),
    "drezina_leather": (0.06, 20, 0.0, 0.2, "0, 0, 0, 1"),
    "drezina_plate": (0.12, 40, 0.3, 0.35, "0, 0, 0, 1"),
    "drezina_glass": (0.6, 120, 0.0, 0.9, "1, 0.7, 0.3, 1"),
    "metro_concrete": (0.03, 10, 0.0, 0.1, "0, 0, 0, 1"),
    "drezina_ballast": (0.02, 8, 0.0, 0.05, "0, 0, 0, 1"),
    "drezina_railtop": (0.6, 120, 1.0, 0.75, "0, 0, 0, 1"),
    "metro_wall": (0.05, 15, 0.0, 0.15, "0, 0, 0, 1"),
    "metro_hazard": (0.1, 30, 0.2, 0.3, "0, 0, 0, 1"),
    "metro_door": (0.15, 40, 0.4, 0.35, "0, 0, 0, 1"),
    "metro_tubing": (0.15, 30, 0.6, 0.3, "0, 0, 0, 1"),
    "metro_dirt": (0.02, 5, 0.0, 0.05, "0, 0, 0, 1"),
    "metro_sign_entrance": (0.1, 30, 0.2, 0.3, "0, 0, 0, 1"),
    "metro_sign_exit": (0.1, 30, 0.2, 0.3, "0, 0, 0, 1"),
    "metro_sign_station": (0.1, 30, 0.2, 0.3, "0, 0, 0, 1"),
    "metro_sign_depot": (0.1, 30, 0.2, 0.3, "0, 0, 0, 1"),
    "metro_tile": (0.15, 40, 0.0, 0.4, "0, 0, 0, 1"),
}


# материалы, для которых делаем карты нормалей и блеска (_nohq, _smdi): сила рельефа, блеск металла
DETAIL_MAPS = {
    "drezina_paint_green": (0.8, 0.35),
    "drezina_paint_blue": (0.8, 0.35),
    "drezina_rust": (1.6, 0.08),
    "drezina_wood": (2.2, 0.06),
    "drezina_steel": (1.0, 0.5),
    "drezina_tape": (0.6, 0.2),
    "drezina_canvas": (1.2, 0.03),
    "drezina_leather": (1.2, 0.15),
    "drezina_plate": (0.8, 0.3),
    "metro_concrete": (1.4, 0.05),
    "metro_wall": (0.9, 0.12),
    "metro_door": (1.0, 0.3),
    "metro_tubing": (1.2, 0.25),
    "metro_tile": (1.0, 0.25),
    "metro_hazard": (0.6, 0.15),
    "drezina_ballast": (2.0, 0.04),
}


def detail_maps(out, name, strength, shine):
    """Из цветовой текстуры: рельеф по яркости -> карта нормалей (_nohq), блеск (_smdi: G — блеск, B — глянец).
    Тёмное (ржавчина, щели, грязь) — ниже и матовее, светлое — выше и блестит."""
    co = np.asarray(Image.open(os.path.join(out, name + "_co.png")).convert("RGB"), dtype=np.float32) / 255.0
    lum = co.mean(axis=2)
    h = np.asarray(Image.fromarray((lum * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.0)), dtype=np.float32) / 255.0
    dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * strength
    dy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * strength
    n = np.stack([-dx, dy, np.ones_like(h)], axis=2)
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    save(n * 0.5 + 0.5, os.path.join(out, name + "_nohq.png"))
    # ржавые/грязные места (красноватые и тёмные) почти не блестят
    rusty = np.clip((co[..., 0] - co[..., 2]) * 3.0, 0, 1)
    spec = np.clip(shine * (0.35 + 0.9 * lum) * (1 - rusty * 0.8), 0, 1)
    gloss = np.clip(spec * 0.9 + 0.05, 0, 1)
    smdi = np.stack([np.ones_like(h), spec, gloss], axis=2)
    save(smdi, os.path.join(out, name + "_smdi.png"))


def write_rvmats(out):
    """Простые материалы Super: цвет из *_co.paa, нормаль/блеск — константы (можно заменить своими картами)."""
    for name, (spec, power, metal, gloss, emissive) in RVMAT_PARAMS.items():
        text = RVMAT % dict(spec=spec, power=power, metal=metal, gloss=gloss, emissive=emissive)
        if name in DETAIL_MAPS:
            tex = "Drezina\\data\\textures\\" + name
            text = text.replace('"#(argb,8,8,3)color(0.5,0.5,1,1,NOHQ)"', '"%s_nohq.paa"' % tex)
            text = text.replace('"#(argb,8,8,3)color(%s,%s,1,1,SMDI)"' % (metal, gloss), '"%s_smdi.paa"' % tex)
            text = text.replace("specular[] = {%s, %s, %s, 1};" % (spec, spec, spec), "specular[] = {0.35, 0.35, 0.35, 1};")
        with open(os.path.join(out, name + ".rvmat"), "w") as f:
            f.write(text)


def main():
    out = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "Drezina/data/textures")
    size = int(sys.argv[2]) if len(sys.argv) > 2 else 1024
    big = size * 2          # основные материалы дрезины — 2048, чтобы вблизи не мылило
    os.makedirs(out, exist_ok=True)
    save(vanilla_grade(paint_tex(big, (78, 88, 62))), os.path.join(out, "drezina_paint_green_co.png"))
    save(vanilla_grade(paint_tex(big, (70, 84, 96))), os.path.join(out, "drezina_paint_blue_co.png"))
    save(vanilla_grade(rust_tex(big)), os.path.join(out, "drezina_rust_co.png"))
    save(vanilla_grade(wood_tex(big)), os.path.join(out, "drezina_wood_co.png"))
    save(vanilla_grade(steel_tex(big)), os.path.join(out, "drezina_steel_co.png"))
    save(vanilla_grade(tape_tex(size // 2)), os.path.join(out, "drezina_tape_co.png"))
    save(vanilla_grade(canvas_tex(size)), os.path.join(out, "drezina_canvas_co.png"))
    save(vanilla_grade(leather_tex(size // 2)), os.path.join(out, "drezina_leather_co.png"))
    save(plate_tex(size // 2), os.path.join(out, "drezina_plate_co.png"))
    save(lamp_glass_tex(size // 4), os.path.join(out, "drezina_glass_co.png"))
    save(vanilla_grade(concrete_tex(size), 0.6), os.path.join(out, "metro_concrete_co.png"))
    save(vanilla_grade(ballast_tex(size // 2), 0.6), os.path.join(out, "drezina_ballast_co.png"))
    save(railtop_tex(size // 4), os.path.join(out, "drezina_railtop_co.png"))
    save(vanilla_grade(wall_two_tone_tex(size), 0.6), os.path.join(out, "metro_wall_co.png"))
    save(vanilla_grade(hazard_tex(size // 2), 0.6), os.path.join(out, "metro_hazard_co.png"))
    save(vanilla_grade(door_tex(size), 0.6), os.path.join(out, "metro_door_co.png"))
    save(vanilla_grade(tubing_tex(size), 0.6), os.path.join(out, "metro_tubing_co.png"))
    save(vanilla_grade(dirt_tex(size // 2), 0.6), os.path.join(out, "metro_dirt_co.png"))
    save(sign_tex(size // 2, ["ОБЪЕКТ 17", "ВХОД ВОСПРЕЩЁН"]), os.path.join(out, "metro_sign_entrance_co.png"))
    save(sign_tex(size // 2, ["ВЫХОД"], bg=(40, 110, 50)), os.path.join(out, "metro_sign_exit_co.png"))
    save(sign_tex(size // 2, ["СТАНЦИЯ", "«ОБЪЕКТ 17»"], bg=(30, 50, 110)), os.path.join(out, "metro_sign_station_co.png"))
    save(sign_tex(size // 2, ["ВЫДАЧА", "ДРЕЗИН"], bg=(170, 120, 20), fg=(25, 22, 18)), os.path.join(out, "metro_sign_depot_co.png"))
    save(vanilla_grade(tile_tex(size), 0.6), os.path.join(out, "metro_tile_co.png"))
    for name, (strength, shine) in DETAIL_MAPS.items():
        detail_maps(out, name, strength, shine)
    write_rvmats(out)
    print("[Drezina] textures written to", out)


if __name__ == "__main__":
    main()
