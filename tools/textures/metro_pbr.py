"""
Материалы метро «как в Москве», 2048 px на 3 x 3 м, с настоящей картой высот (не из яркости):

  metro_wall    кафель 15x15 см: внизу 5 рядов зелёного, ряд белого, ряд зелёного, выше белый.
                Глазурь блестит, швы утоплены, у каждой плитки фаска и свой лёгкий наклон (неровная
                укладка даёт живые блики), сколы, трещины, редкие выпавшие плитки, грязь у пола, потёки.
  metro_brick   кирпичная кладка тоннеля (250x65, шов 10 мм, перевязка в полкирпича): у каждого
                кирпича свой тон, обожжённые тёмные, скруглённые края и сколы, утопленный зернистый
                раствор, копоть, высолы, сырость внизу.
  metro_plaster штукатурка свода: затирка разводами, волосяные трещины, рыжие следы протечек,
                отвалившиеся куски до бетона, копоть.

Для каждого: _co (цвет), _nohq (нормали из карты высот), _smdi (блеск: G — сила, B — глянец).
Низ текстуры = пол (v = высота / 3 м).
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

N = 4096                             # 4096 на 3 м: ~1365 px/м, вблизи не «мылит»
METERS = 3.0
PX = N / METERS                      # пикселей на метр


def _noise(size, scale, octaves, rng, stretch=(1, 1)):
    out = np.zeros((size, size), np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        cx = max(2, int(size / scale * (2 ** o) / stretch[0]))
        cy = max(2, int(size / scale * (2 ** o) / stretch[1]))
        g = rng.random((cy, cx)).astype(np.float32)
        img = Image.fromarray((g * 255).astype(np.uint8)).resize((size, size), Image.BICUBIC)
        out += amp * np.asarray(img, np.float32) / 255.0
        total += amp
        amp *= 0.5
    out /= total
    return (out - out.min()) / (out.max() - out.min() + 1e-6)


def _blur(a, r):
    img = Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8))
    return np.asarray(img.filter(ImageFilter.GaussianBlur(r)), np.float32) / 255.0


def _blurf(a, r):
    """размытие float-карты (без потери точности на 8 битах)"""
    lo, hi = float(a.min()), float(a.max())
    n = (a - lo) / (hi - lo + 1e-9)
    img = Image.fromarray((n * 65535).astype(np.uint16).astype(np.int32), mode="I")
    b = np.asarray(img.convert("F").filter(ImageFilter.GaussianBlur(r)), np.float32) / 65535.0
    return b * (hi - lo) + lo


def _cracks(size, count, rng, step=0.012, width=2):
    img = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(img)
    for _ in range(count):
        x, y = rng.random() * size, rng.random() * size
        ang = rng.random() * 6.283
        for _s in range(int(rng.integers(15, 50))):
            ang += rng.normal(0, 0.5)
            nx, ny = x + np.cos(ang) * size * step, y + np.sin(ang) * size * step
            d.line((x, y, nx, ny), fill=int(rng.integers(160, 255)), width=width)
            x, y = nx, ny
    return np.asarray(img.filter(ImageFilter.GaussianBlur(0.5)), np.float32) / 255.0


def _fine(rng, amp=1.0):
    """попиксельное зерно (без размытия) — мелкая чёткая фактура"""
    g = rng.random((N, N)).astype(np.float32) - 0.5
    return g * amp


def _speckles(rng, density, size_px=2):
    """точки-вкрапления (щебень, раковины): маска 0..1 с чёткими краями"""
    m = (rng.random((N // size_px, N // size_px)) < density).astype(np.uint8) * 255
    img = Image.fromarray(m).resize((N, N), Image.NEAREST).filter(ImageFilter.GaussianBlur(0.6))
    return np.asarray(img, np.float32) / 255.0


def _streaks(size, rng, density=0.6):
    base = _noise(size, 6, 3, rng, stretch=(1, 40))
    drip = _noise(size, 40, 4, rng)
    m = np.clip((base - (1 - density)) * 3, 0, 1) * np.clip(drip * 1.5 - 0.3, 0, 1)
    return _blur(m, 1.5)


def col(*c):
    return np.array(c, np.float32) / 255.0


def lerp(a, b, t):
    return a * (1 - t[..., None]) + b * t[..., None]


def height_to_normal(h, strength):
    """h в метрах-эквиваленте (0..1), strength — во сколько раз усилить уклоны"""
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * strength
    n = np.stack([-dx, dy, np.ones_like(h)], 2)
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n * 0.5 + 0.5


def save(arr, path):
    Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8)).save(path)


def write(out, name, co, h, strength, spec, gloss):
    save(co, os.path.join(out, name + "_co.png"))
    save(height_to_normal(h, strength), os.path.join(out, name + "_nohq.png"))
    smdi = np.stack([np.ones_like(spec), np.clip(spec, 0, 1), np.clip(gloss, 0, 1)], 2)
    img = Image.fromarray((np.clip(smdi, 0, 1) * 255).astype(np.uint8)).resize((N // 2, N // 2), Image.LANCZOS)
    img.save(os.path.join(out, name + "_smdi.png"))      # блеск — в половину разрешения (его вблизи не видно)


# ============================================================================ кафель

def tile_wall(out, seed=101):
    rng = np.random.default_rng(seed)
    T = 0.15 * PX                                  # плитка 15 см
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    zb = (N - 1 - yy)                              # высота от пола в пикселях
    ix = np.floor(xx / T).astype(int)
    iy = np.floor(zb / T).astype(int)
    fx = xx / T - ix                               # 0..1 внутри плитки
    fy = zb / T - iy
    nx, ny = int(np.ceil(N / T)) + 1, int(np.ceil(N / T)) + 1
    # раскладка цвета по рядам (как на фото): 0-4 зелёные, 5 белый, 6 зелёный, выше белые
    green_rows = np.isin(iy, [0, 1, 2, 3, 4, 6])
    white = col(214, 212, 202)
    green = col(22, 92, 54)
    base = np.where(green_rows[..., None], green, white)
    # тон и глазурь у каждой плитки свои
    jit = rng.normal(0, 1, (ny, nx, 3)).astype(np.float32)
    tone = jit[iy.clip(0, ny - 1), ix.clip(0, nx - 1)]
    base = base * (1 + tone[..., :1] * 0.035) + tone * 0.008
    glaze = _noise(N, 30, 4, rng)
    base = base * (0.95 + glaze[..., None] * 0.08)

    # шов: ~3 мм, фаска плитки ~6 мм
    g = 0.003 * PX / T                             # доля плитки
    bev = 0.007 * PX / T
    ex = np.minimum(fx, 1 - fx)
    ey = np.minimum(fy, 1 - fy)
    e = np.minimum(ex, ey)
    grout = (e < g).astype(np.float32)
    bevel = np.clip((e - g) / bev, 0, 1)
    h = np.where(grout > 0, 0.0, 0.6 + 0.4 * np.sqrt(bevel))
    # наклон каждой плитки (неровная укладка) и лёгкая волна глазури
    tilt = rng.normal(0, 1, (ny, nx, 2)).astype(np.float32)
    tx = tilt[iy.clip(0, ny - 1), ix.clip(0, nx - 1), 0]
    ty = tilt[iy.clip(0, ny - 1), ix.clip(0, nx - 1), 1]
    h = h + (1 - grout) * ((fx - 0.5) * tx + (fy - 0.5) * ty) * 0.06
    h = h + (1 - grout) * (_noise(N, 8, 3, rng) - 0.5) * 0.02

    grout_col = col(78, 76, 70) * (0.85 + _noise(N, 20, 3, rng)[..., None] * 0.3)
    grout_col = grout_col * (1 + _fine(rng, 0.35)[..., None])          # песок в шве
    base = base * (1 + _fine(rng, 0.04)[..., None])                     # микрорябь глазури
    pin = _speckles(rng, 0.004, 1)                                      # точечные выбоины глазури
    base = base * (1 - pin[..., None] * 0.35)
    c = lerp(base, grout_col, grout)
    h = h + grout * _fine(rng, 0.08) - pin * 0.08 * (1 - grout)
    conc = lerp(col(120, 116, 106), col(88, 84, 76), _noise(N, 25, 5, rng))

    # выпавшие плитки (~1.2%) — клей и бетон, утоплено; сколы углов; трещины
    miss = rng.random((ny, nx)) < 0.005
    mm = miss[iy.clip(0, ny - 1), ix.clip(0, nx - 1)].astype(np.float32)
    adhesive = lerp(conc, col(150, 146, 134), (_noise(N, 6, 3, rng) > 0.55).astype(np.float32) * 0.6)
    c = lerp(c, adhesive, mm)
    h = np.where(mm > 0, 0.05 + _noise(N, 4, 2, rng) * 0.08, h)
    chip_tiles = rng.random((ny, nx)) < 0.06
    corner = rng.integers(0, 4, (ny, nx))
    ct = chip_tiles[iy.clip(0, ny - 1), ix.clip(0, nx - 1)]
    cc = corner[iy.clip(0, ny - 1), ix.clip(0, nx - 1)]
    cx_ = np.where(cc % 2 == 0, fx, 1 - fx)
    cy_ = np.where(cc < 2, fy, 1 - fy)
    chip = ct & (cx_ + cy_ < 0.22 + _noise(N, 3, 2, rng) * 0.12)
    c = np.where(chip[..., None], conc * 0.95, c)
    h = np.where(chip, 0.12, h)
    cr = _cracks(N, 14, rng, 0.006)
    c = c * (1 - cr[..., None] * 0.55)
    h = h - cr * 0.15

    # старение: грязь у пола, потёки сверху, пятна копоти
    floor_dirt = np.clip(1 - zb / (0.45 * PX), 0, 1) ** 1.5 * (0.6 + _noise(N, 10, 4, rng) * 0.4)
    c = lerp(c, col(52, 46, 38), floor_dirt * 0.65)
    st = _streaks(N, rng, 0.4) * np.clip(zb / N, 0.2, 1)
    c = lerp(c, col(110, 96, 74), np.clip(st, 0, 1) * 0.35)
    soot = _noise(N, 90, 5, rng) ** 4
    c = lerp(c, col(60, 56, 50), soot * 0.3)
    grime = np.clip(grout * 0.5 + floor_dirt, 0, 1)

    spec = np.where(grout > 0, 0.05, 0.75) * (1 - mm * 0.9) * (1 - floor_dirt * 0.6) * (1 - soot * 0.5)
    spec = np.where(chip, 0.05, spec)
    gloss = np.where(grout > 0, 0.1, 0.9) * (1 - mm * 0.85) * (1 - grime * 0.4)
    write(out, "metro_wall", np.clip(c, 0, 1), h, 9.0, spec, gloss)


# ============================================================================ кирпич

def brick_wall(out, seed=202):
    rng = np.random.default_rng(seed)
    BW, BH, J = 0.25 * PX, 0.075 * PX, 0.010 * PX          # модуль: 250 x 75 мм с швом 10 мм
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    zb = (N - 1 - yy)
    row = np.floor(zb / BH).astype(int)
    off = (row % 2) * 0.5 * BW
    colx = np.floor((xx + off) / BW).astype(int)
    fx = (xx + off) / BW - colx
    fy = zb / BH - row
    jx = J / BW
    jy = J / BH
    ex = np.minimum(fx, 1 - fx) / jx
    ey = np.minimum(fy, 1 - fy) / jy
    e = np.minimum(ex, ey)                        # <1 — шов
    mortar = (e < 0.5).astype(np.float32)
    nr, nc = int(N / BH) + 2, int(N / BW) + 3
    tone = rng.normal(0, 1, (nr, nc)).astype(np.float32)
    t = tone[row.clip(0, nr - 1), colx.clip(0, nc - 1)]
    burnt = (rng.random((nr, nc)) < 0.12)[row.clip(0, nr - 1), colx.clip(0, nc - 1)]
    b1, b2 = col(138, 66, 44), col(108, 52, 36)
    brick = lerp(b1, b2, np.clip(0.5 + t * 0.35, 0, 1))
    brick = np.where(burnt[..., None], brick * 0.62 + col(30, 20, 18) * 0.3, brick)
    brick = brick * (0.9 + _noise(N, 4, 4, rng)[..., None] * 0.2)
    brick = brick * (1 + _fine(rng, 0.12)[..., None])                   # зерно обожжённой глины
    pits = (_noise(N, 2, 2, rng) > 0.8).astype(np.float32)
    brick = brick * (1 - pits[..., None] * 0.25)
    mort_c = lerp(col(150, 144, 130), col(110, 104, 94), _noise(N, 3, 3, rng))
    mort_c = mort_c * (1 + _fine(rng, 0.3)[..., None])
    c = lerp(brick, mort_c, mortar)
    # высота: скруглённые края кирпича, сколы по углам и рёбрам, зернистый утопленный раствор
    edge = np.clip((e - 0.5) / 2.2, 0, 1)
    chips = np.clip((_noise(N, 5, 3, rng) - 0.72) * 6, 0, 1) * (edge < 0.9)
    h = np.where(mortar > 0, 0.15 + _noise(N, 2, 2, rng) * 0.08, 0.55 + 0.45 * np.sqrt(edge) - chips * 0.35)
    h = h + (1 - mortar) * (_noise(N, 6, 3, rng) - 0.5) * 0.06
    h = h + _fine(rng, 0.06) * (1 + mortar)
    c = np.where((chips > 0.3)[..., None], c * 0.8, c)
    # копоть по всей кладке, высолы у швов, сырость внизу
    soot = 0.25 + _noise(N, 60, 5, rng) * 0.5
    c = lerp(c, col(32, 28, 26), soot * 0.45)
    eff = np.clip(_streaks(N, rng, 0.35) * 1.2, 0, 1) * (0.25 + mortar * 0.75)
    c = lerp(c, col(196, 190, 176), eff * 0.3)
    damp = np.clip(1 - zb / (0.9 * PX), 0, 1) * (0.5 + _noise(N, 15, 4, rng) * 0.5)
    c = lerp(c, col(40, 32, 28), damp * 0.55)
    spec = (0.12 + damp * 0.3) * (1 - mortar * 0.5)
    gloss = 0.15 + damp * 0.35
    write(out, "metro_brick", np.clip(c, 0, 1), h, 10.0, spec, gloss)


# ============================================================================ штукатурка свода

def plaster(out, seed=303):
    rng = np.random.default_rng(seed)
    base = lerp(col(176, 172, 162), col(152, 148, 138), _noise(N, 60, 5, rng))
    trowel = _noise(N, 18, 3, rng, stretch=(3, 1)) * 0.6 + _noise(N, 10, 3, rng, stretch=(1, 2)) * 0.4
    c = base * (0.94 + trowel[..., None] * 0.1)
    h = trowel * 0.25 + _noise(N, 2, 3, rng) * 0.05 + _fine(rng, 0.05)
    c = c * (1 + _fine(rng, 0.06)[..., None])
    # отвалившиеся куски: бетон под штукатуркой, резкий край
    flake_m = _noise(N, 35, 5, rng)
    flake = (flake_m > 0.84).astype(np.float32)
    edge = np.clip((flake_m - 0.80) / 0.04, 0, 1) * (1 - flake)
    conc = lerp(col(116, 112, 104), col(90, 88, 82), _noise(N, 8, 4, rng))
    c = lerp(c, conc, flake)
    c = c * (1 - edge[..., None] * 0.25)
    h = np.where(flake > 0, -0.35 + _noise(N, 3, 3, rng) * 0.1, h)
    # трещины, рыжие разводы протечек, копоть
    cr = _cracks(N, 12, rng, 0.01)
    c = c * (1 - cr[..., None] * 0.5)
    h = h - cr * 0.12
    leak = np.clip((_noise(N, 70, 4, rng) - 0.6) * 4, 0, 1)
    ring = np.clip(1 - np.abs(_noise(N, 70, 4, rng) - 0.62) * 25, 0, 1)
    c = lerp(c, col(150, 120, 80), leak * 0.4)
    c = lerp(c, col(120, 90, 55), ring * 0.35)
    soot = _noise(N, 80, 5, rng) ** 2.5
    c = lerp(c, col(48, 44, 40), soot * 0.55)
    spec = 0.06 + leak * 0.1
    gloss = 0.1 + leak * 0.15
    write(out, "metro_plaster", np.clip(c, 0, 1), h, 6.0, spec, gloss)


# ============================================================================ бетонный пол

def concrete_floor(out, seed=404):
    rng = np.random.default_rng(seed)
    base = lerp(col(124, 120, 112), col(98, 96, 90), _noise(N, 50, 6, rng))
    c = base * (1 + _fine(rng, 0.10)[..., None])
    # щебень в бетоне: светлые и тёмные зёрна, раковины
    light = _speckles(rng, 0.010, 2)
    dark = _speckles(rng, 0.008, 2)
    pits = _speckles(rng, 0.003, 3)
    c = lerp(c, col(160, 156, 146), light * 0.6)
    c = lerp(c, col(70, 68, 62), dark * 0.6)
    c = c * (1 - pits[..., None] * 0.45)
    # швы плит пола через 1.5 м (по ширине и длине), трещины, сколы у швов
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    step = 1.5 * PX
    jw = 0.006 * PX
    jx = (np.minimum(xx % step, step - xx % step) < jw).astype(np.float32)
    jy = (np.minimum(yy % step, step - yy % step) < jw).astype(np.float32)
    joint = np.maximum(jx, jy)
    c = lerp(c, col(50, 48, 44), joint * 0.85)
    cr = _cracks(N, 18, rng, 0.008)
    c = c * (1 - cr[..., None] * 0.6)
    # пятна: масло, сырость, натоптанная полоса посередине
    oil = np.clip((_noise(N, 40, 4, rng) - 0.7) * 5, 0, 1)
    c = lerp(c, col(38, 36, 34), oil * 0.55)
    wet = np.clip((_noise(N, 70, 4, rng) - 0.62) * 4, 0, 1)
    c = lerp(c, col(70, 66, 60), wet * 0.4)
    h = _noise(N, 6, 4, rng) * 0.12 + _fine(rng, 0.06) + light * 0.08 + dark * 0.05 - pits * 0.25 - joint * 0.4 - cr * 0.2
    spec = 0.06 + wet * 0.35 + oil * 0.2
    gloss = 0.1 + wet * 0.5 + oil * 0.3
    write(out, "metro_concrete", np.clip(c, 0, 1), h, 8.0, spec, gloss)


# ============================================================================ детальная текстура (DT)

def detail_dt(out, seed=505):
    """512 px, нейтрально-серая (0.5) мелкая фактура: движок кладёт её поверх цвета с повтором x8 —
    вблизи поверхность не расплывается (так сделаны ванильные материалы)."""
    rng = np.random.default_rng(seed)
    n = 512
    g = rng.random((n, n)).astype(np.float32)
    img = Image.fromarray((g * 255).astype(np.uint8))
    f1 = np.asarray(img.filter(ImageFilter.GaussianBlur(0.6)), np.float32) / 255.0
    f2 = np.asarray(img.resize((n // 4, n // 4)).resize((n, n), Image.BICUBIC), np.float32) / 255.0
    d = 0.5 + (f1 - 0.5) * 0.35 + (f2 - 0.5) * 0.25
    d = np.repeat(np.clip(d, 0, 1)[..., None], 3, 2)
    save(d, os.path.join(out, "metro_detail_dt.png"))


# ============================================================================ наружный бетон входа

def concrete_ext(out, seed=606):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    zb = (N - 1 - yy)
    base = lerp(col(138, 136, 128), col(108, 106, 100), _noise(N, 60, 6, rng))
    c = base * (1 + _fine(rng, 0.09)[..., None])
    # доски опалубки по 15 см: свой тон, волокно, ступенька на стыке
    bh = 0.15 * PX
    board = np.floor(zb / bh).astype(int)
    tone = rng.normal(0, 1, board.max() + 2).astype(np.float32)[board]
    fib = _noise(N, 3, 3, rng, stretch=(40, 1))
    c = c * (1 + tone[..., None] * 0.03) * (0.96 + fib[..., None] * 0.07)
    fy = zb / bh - board
    seam = (np.minimum(fy, 1 - fy) < 0.03).astype(np.float32)
    c = c * (1 - seam[..., None] * 0.2)
    # отверстия от стяжек опалубки сеткой ~0.6 м
    g = 0.6 * PX
    dx = (xx % g) - g / 2
    dy = (zb % g) - g / 2
    tie = ((dx ** 2 + dy ** 2) < (0.018 * PX) ** 2).astype(np.float32)
    c = c * (1 - tie[..., None] * 0.55)
    # дождевые потёки сверху, мох и лишайник у земли и пятнами, трещины, отколы с арматурой
    st = _streaks(N, rng, 0.7)
    c = lerp(c, col(70, 68, 62), np.clip(st, 0, 1) * 0.55)
    moss_m = np.clip(1 - zb / (0.6 * PX), 0, 1) * _noise(N, 12, 5, rng) + np.clip((_noise(N, 30, 5, rng) - 0.72) * 3, 0, 1)
    moss = np.clip(moss_m * 1.4 - 0.3, 0, 1)
    c = lerp(c, lerp(col(70, 84, 44), col(52, 62, 34), _noise(N, 4, 3, rng)), moss * 0.75)
    lich = _speckles(rng, 0.006, 3) * (_noise(N, 40, 4, rng) > 0.5)
    c = lerp(c, col(150, 150, 110), lich * 0.6)
    cr = _cracks(N, 14, rng, 0.01)
    c = c * (1 - cr[..., None] * 0.6)
    spall_m = _noise(N, 25, 5, rng)
    spall = (spall_m > 0.86).astype(np.float32)
    c = lerp(c, col(96, 94, 88), spall)
    rebar = spall * ((np.abs((xx % (0.2 * PX)) - 0.1 * PX) < 0.006 * PX)).astype(np.float32)
    c = lerp(c, col(110, 60, 32), rebar)
    c = lerp(c, col(120, 70, 40), np.clip(_streaks(N, rng, 0.25), 0, 1) * 0.3)      # ржавые потёки
    h = (_noise(N, 6, 4, rng) * 0.1 + fib * 0.06 + _fine(rng, 0.05) - seam * 0.15 - tie * 0.5
         - cr * 0.25 - spall * 0.35 + rebar * 0.3 + moss * 0.08)
    spec = 0.05 + st * 0.05
    gloss = 0.08 + moss * 0.05
    write(out, "metro_concrete_ext", np.clip(c, 0, 1), h, 8.0, spec, gloss)


# ============================================================================ гермодверь, разметка, насыпь (2048)

def _write2k(out, name, co, h, strength, spec, gloss):
    """то же, что write, но в 2048 (у этих текстур тайл меньше метра — плотность и так высокая)"""
    def down(a):
        if a.ndim == 2:
            img = Image.fromarray(np.clip(a, 0, 1).astype(np.float32), mode="F")
            return np.asarray(img.resize((N // 2, N // 2), Image.LANCZOS), np.float32)
        return np.stack([down(a[..., i]) for i in range(a.shape[2])], 2)
    co2 = down(co)
    h2 = down(h)
    save(co2, os.path.join(out, name + "_co.png"))
    save(height_to_normal(h2, strength), os.path.join(out, name + "_nohq.png"))
    smdi = np.stack([np.ones_like(h2), np.clip(down(spec), 0, 1), np.clip(down(gloss), 0, 1)], 2)
    save(smdi, os.path.join(out, name + "_smdi.png"))


def painted_metal(out, rng, name, paint, stripes=False):
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    rust = lerp(col(112, 58, 30), col(66, 36, 22), _noise(N, 6, 5, rng))
    rust = rust * (1 + _fine(rng, 0.25)[..., None])
    if stripes:
        d = ((xx + yy) // (N / 6)) % 2
        p = np.where(d[..., None] == 0, col(200, 158, 30), col(28, 26, 22))
    else:
        p = lerp(col(*paint), col(*paint) * 0.82, _noise(N, 40, 5, rng))
    p = p * (1 + _fine(rng, 0.05)[..., None])
    chip_m = _noise(N, 90, 7, rng)                      # крупные пятна облупившейся краски с рваным краем
    chip = np.clip((chip_m - 0.68) * 14, 0, 1)
    edge = np.clip(1 - np.abs(chip_m - 0.68) * 35, 0, 1)
    c = lerp(p, rust, chip)
    c = c * (1 - edge[..., None] * 0.3)
    scr = _cracks(N, 40, rng, 0.004, 1)                 # царапины
    c = lerp(c, col(150, 146, 136), scr * 0.5)
    run = np.clip(_streaks(N, rng, 0.35), 0, 1)
    c = lerp(c, col(120, 66, 34), run * 0.45)
    h = 0.5 + (1 - chip) * 0.25 + _fine(rng, 0.03) - scr * 0.15 + chip * _noise(N, 3, 3, rng) * 0.1
    spec = (1 - chip) * 0.35 + chip * 0.05
    gloss = (1 - chip) * 0.45 + 0.05
    _write2k(out, name, np.clip(c, 0, 1), h, 6.0, spec, gloss)


def soil(out, seed=707):
    rng = np.random.default_rng(seed)
    c = lerp(col(78, 64, 46), col(104, 88, 64), _noise(N, 30, 6, rng))
    c = c * (1 + _fine(rng, 0.14)[..., None])
    peb = _speckles(rng, 0.012, 4)
    c = lerp(c, lerp(col(130, 126, 116), col(90, 88, 82), _noise(N, 3, 2, rng)), peb * 0.8)
    grass_m = np.clip((_noise(N, 25, 5, rng) - 0.42) * 3, 0, 1)
    blades = np.clip(_noise(N, 1.2, 2, rng, stretch=(1, 8)) + _fine(rng, 0.3), 0, 1)
    grass = grass_m * (blades > 0.5)
    c = lerp(c, lerp(col(70, 86, 38), col(108, 112, 54), _noise(N, 5, 3, rng)), grass * 0.85)
    h = _noise(N, 8, 4, rng) * 0.2 + peb * 0.25 + grass * blades * 0.15 + _fine(rng, 0.06)
    spec = 0.04 + grass * 0.04
    gloss = 0.06 + grass * 0.05
    _write2k(out, "metro_dirt", np.clip(c, 0, 1), h, 6.0, spec, gloss)


def main(out):
    tile_wall(out)
    brick_wall(out)
    plaster(out)
    concrete_floor(out)
    concrete_ext(out)
    rng = np.random.default_rng(808)
    painted_metal(out, rng, "metro_door", (88, 98, 88))
    painted_metal(out, rng, "metro_hazard", None, stripes=True)
    soil(out)
    detail_dt(out)


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
