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
    c = lerp(col(92, 45, 22), col(160, 78, 34), n1)
    c = lerp(c, col(60, 32, 18), n2 * 0.6)
    c = lerp(c, col(190, 110, 50), np.clip(n1 - 0.65, 0, 1) * 2)
    c *= (1 - pits[..., None] * 0.35)
    return c


def paint_tex(size, paint_rgb):
    """Советская краска по металлу, облупилась до ржавчины, потёки и грязь."""
    rust = rust_tex(size)
    paint = lerp(col(*paint_rgb), col(*paint_rgb) * 0.75, noise(size, 48, 5))
    paint = lerp(paint, col(150, 150, 130), noise(size, 128, 3) * 0.25)       # выгорела
    chip = noise(size, 30, 6, 0.55)
    chip_mask = np.clip((chip - 0.62) * 9, 0, 1)                              # облупилось
    edge = np.clip((chip - 0.58) * 9, 0, 1) - chip_mask                       # тёмный край скола
    c = lerp(paint, rust, chip_mask)
    c *= (1 - np.clip(edge, 0, 1)[..., None] * 0.35)
    c = lerp(c, col(110, 55, 25), np.clip(streaks(size), 0, 1))
    c = lerp(c, col(45, 40, 32), noise(size, 90, 4) ** 3 * 0.6)              # грязь
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
    x = np.arange(size)
    weave = (np.sin(x / 2.0)[None, :] * np.sin(x / 2.0)[:, None]) * 0.5 + 0.5
    c = lerp(col(84, 88, 60), col(110, 112, 80), weave * 0.4 + noise(size, 40, 5) * 0.6)
    c = lerp(c, col(50, 45, 35), noise(size, 70, 4) ** 2 * 0.7)
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
    "drezina_plate": (0.12, 40, 0.3, 0.35, "0, 0, 0, 1"),
    "drezina_glass": (0.6, 120, 0.0, 0.9, "1, 0.7, 0.3, 1"),
    "metro_concrete": (0.03, 10, 0.0, 0.1, "0, 0, 0, 1"),
    "metro_wall": (0.05, 15, 0.0, 0.15, "0, 0, 0, 1"),
    "metro_hazard": (0.1, 30, 0.2, 0.3, "0, 0, 0, 1"),
    "metro_door": (0.15, 40, 0.4, 0.35, "0, 0, 0, 1"),
    "metro_tubing": (0.15, 30, 0.6, 0.3, "0, 0, 0, 1"),
    "metro_dirt": (0.02, 5, 0.0, 0.05, "0, 0, 0, 1"),
    "metro_sign_entrance": (0.1, 30, 0.2, 0.3, "0, 0, 0, 1"),
    "metro_sign_exit": (0.1, 30, 0.2, 0.3, "0, 0, 0, 1"),
}


def write_rvmats(out):
    """Простые материалы Super: цвет из *_co.paa, нормаль/блеск — константы (можно заменить своими картами)."""
    for name, (spec, power, metal, gloss, emissive) in RVMAT_PARAMS.items():
        text = RVMAT % dict(spec=spec, power=power, metal=metal, gloss=gloss, emissive=emissive)
        with open(os.path.join(out, name + ".rvmat"), "w") as f:
            f.write(text)


def main():
    out = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "Drezina/data/textures")
    size = int(sys.argv[2]) if len(sys.argv) > 2 else 1024
    os.makedirs(out, exist_ok=True)
    save(paint_tex(size, (66, 86, 60)), os.path.join(out, "drezina_paint_green_co.png"))
    save(paint_tex(size, (60, 82, 104)), os.path.join(out, "drezina_paint_blue_co.png"))
    save(rust_tex(size), os.path.join(out, "drezina_rust_co.png"))
    save(wood_tex(size), os.path.join(out, "drezina_wood_co.png"))
    save(steel_tex(size), os.path.join(out, "drezina_steel_co.png"))
    save(tape_tex(size // 2), os.path.join(out, "drezina_tape_co.png"))
    save(canvas_tex(size // 2), os.path.join(out, "drezina_canvas_co.png"))
    save(plate_tex(size // 2), os.path.join(out, "drezina_plate_co.png"))
    save(lamp_glass_tex(size // 4), os.path.join(out, "drezina_glass_co.png"))
    save(concrete_tex(size), os.path.join(out, "metro_concrete_co.png"))
    save(wall_two_tone_tex(size), os.path.join(out, "metro_wall_co.png"))
    save(hazard_tex(size // 2), os.path.join(out, "metro_hazard_co.png"))
    save(door_tex(size), os.path.join(out, "metro_door_co.png"))
    save(tubing_tex(size), os.path.join(out, "metro_tubing_co.png"))
    save(dirt_tex(size // 2), os.path.join(out, "metro_dirt_co.png"))
    save(sign_tex(size // 2, ["ОБЪЕКТ 17", "ВХОД ВОСПРЕЩЁН"]), os.path.join(out, "metro_sign_entrance_co.png"))
    save(sign_tex(size // 2, ["ВЫХОД"], bg=(40, 110, 50)), os.path.join(out, "metro_sign_exit_co.png"))
    write_rvmats(out)
    print("[Drezina] textures written to", out)


if __name__ == "__main__":
    main()
