"""
Реалистичный путь: рельс Р65 (настоящий профиль: подошва, шейка, головка), железобетонные шпалы
с креплением типа КБ (подкладка, резиновая прокладка, клеммы, закладные болты), щебёночная призма.
Колея 1520 мм. Origin звена — верх головки рельса по центру колеи (туда сервер ставит точку пути).

  rail_10m — прямое звено 10 м (18 шпал, стыковые накладки на одном конце)
  rail_2m  — короткое звено для кривых
"""
import math

import bmesh
import bpy

import handcar_zone as hz

GAUGE = 1.520
HEAD_HALF = 0.0375
RAIL_X = GAUGE / 2 + HEAD_HALF            # ось рельса
RAIL_H = 0.180                            # высота рельса Р65
PLATE_T = 0.02                            # подкладка + прокладка
SLEEPER_H = 0.19
SLEEPER_TOP = -(RAIL_H + PLATE_T)         # -0.20
SLEEPER_BOTTOM = SLEEPER_TOP - SLEEPER_H  # -0.39
SLEEPER_STEP = 0.55                       # эпюра 1840 шт/км

# полупрофиль Р65 (x от оси рельса, z от низа подошвы), против часовой от края подошвы
R65_HALF = [
    (0.075, 0.000), (0.075, 0.011), (0.060, 0.016), (0.030, 0.026), (0.012, 0.038),
    (0.009, 0.050), (0.009, 0.128), (0.012, 0.138), (0.030, 0.144), (0.036, 0.150),
    (0.0375, 0.162), (0.036, 0.172), (0.030, 0.178), (0.016, 0.1805), (0.000, 0.181),
]


def r65_profile():
    left = [(-x, z) for (x, z) in reversed(R65_HALF[:-1])]
    return R65_HALF + left


def extrude_rail(name, length, x_center, m):
    """Рельс: профиль Р65, вытянутый по Y. Поверхность катания (верх головки) — блестящая сталь."""
    prof = r65_profile()
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    rings = []
    for y in (-length / 2, length / 2):
        rings.append([bm.verts.new((x_center + x, y, z - RAIL_H)) for (x, z) in prof])
    a, b = rings
    n = len(prof)
    bm.faces.new(a[::-1])
    bm.faces.new(b)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])     # нормали наружу
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    o = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(m["rust"])
    o.data.materials.append(m["railtop"])
    for poly in o.data.polygons:                 # верх головки — накатанная сталь
        c = poly.center
        if poly.normal.z > 0.6 and c.z > -0.012:
            poly.material_index = 1
    return o


def sleeper(name, y, m):
    """ЖБ шпала: 2.7 м, сужается кверху и к середине."""
    s = hz.box(name, (2.70, 0.30, SLEEPER_H), (0, y, SLEEPER_BOTTOM + SLEEPER_H / 2), m["concrete"])
    for v in s.data.vertices:
        if v.co.z > SLEEPER_BOTTOM + SLEEPER_H / 2:
            v.co.y = y + (v.co.y - y) * 0.62    # верх уже низа
        if abs(v.co.x) < 0.5:
            v.co.z = min(v.co.z, SLEEPER_TOP - 0.025) if v.co.z > SLEEPER_BOTTOM + 0.05 else v.co.z
    return s


def fastening(prefix, x, y, m, out):
    """Крепление КБ на одной шпале под одним рельсом."""
    out.append(hz.box(f"{prefix}_plate", (0.36, 0.17, 0.016), (x, y, SLEEPER_TOP + 0.008), m["rust"]))
    out.append(hz.box(f"{prefix}_pad", (0.16, 0.15, 0.006), (x, y, SLEEPER_TOP + 0.018), m["tape"], round_edges=False))
    for sx in (-1, 1):
        cx = x + sx * 0.105
        # клемма (прижимает подошву) + клеммный болт с гайкой и шайбой
        out.append(hz.box(f"{prefix}_clamp{sx}", (0.07, 0.05, 0.022), (x + sx * 0.085, y, SLEEPER_TOP + 0.03), m["steel"], (0, math.radians(-12 * sx), 0)))
        out.append(hz.cyl(f"{prefix}_bolt{sx}", 0.011, 0.07, (cx, y, SLEEPER_TOP + 0.045), m["steel"], (0, 0, 0), 6))
        out.append(hz.cyl(f"{prefix}_nut{sx}", 0.018, 0.016, (cx, y, SLEEPER_TOP + 0.062), m["steel"], (0, 0, 0), 6))
        # закладные болты подкладки к шпале
        out.append(hz.cyl(f"{prefix}_anchor{sx}", 0.016, 0.02, (x + sx * 0.155, y, SLEEPER_TOP + 0.02), m["rust"], (0, 0, 0), 6))


def ballast(name, length, m):
    """Щебёночная призма: трапеция с неровным верхом, плечи уходят ниже шпал."""
    top_w, bot_w = 3.3, 4.6
    z_top, z_bot = SLEEPER_TOP - 0.06, SLEEPER_BOTTOM - 0.28
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    seg = max(2, int(length / 0.5))
    cols = 9
    grid = []
    for j in range(seg + 1):
        y = -length / 2 + length * j / seg
        row = []
        for i in range(cols):
            f = i / (cols - 1)
            # профиль: плечо - откос - верх - откос - плечо
            x = -bot_w / 2 + f * bot_w
            if abs(x) <= top_w / 2:
                z = z_top + 0.02 * math.sin(x * 9 + y * 7) * math.sin(y * 5.3)
            else:
                k = (abs(x) - top_w / 2) / ((bot_w - top_w) / 2)
                z = z_top + (z_bot - z_top) * k
            row.append(bm.verts.new((x, y, z)))
        grid.append(row)
    for j in range(seg):
        for i in range(cols - 1):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    o = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(m["ballast"])
    return o


def fishplates(prefix, y_end, m, out):
    """Стыковые накладки с 6 болтами на конце звена."""
    for sx in (-1, 1):
        for side in (-1, 1):
            x = sx * RAIL_X + side * 0.017
            out.append(hz.box(f"{prefix}{sx}{side}", (0.012, 0.8, 0.08), (x, y_end - 0.4, -RAIL_H + 0.09), m["rust"]))
            for k in range(3):
                out.append(hz.cyl(f"{prefix}b{sx}{side}{k}", 0.014, 0.02, (x + side * 0.012, y_end - 0.12 - k * 0.2, -RAIL_H + 0.09), m["steel"], hz.ROT_X, 6))


def build_rail(outdir, save_fn, reset_fn, tex_dir, length=10.0, name="rail_10m"):
    reset_fn()
    hz.TEX_DIR = tex_dir
    m = hz.materials()
    m["concrete"] = hz.tex_material("metro_concrete", "metro_concrete", 0.95)
    m["ballast"] = hz.tex_material("drezina_ballast", "drezina_ballast", 1.0)
    m["railtop"] = hz.tex_material("drezina_railtop", "drezina_railtop", 0.25, 1.0)
    parts = []
    for sx in (-1, 1):
        parts.append(extrude_rail(f"rail{sx}", length, sx * RAIL_X, m))
    count = int(round(length / SLEEPER_STEP))
    for k in range(count):
        y = -length / 2 + SLEEPER_STEP / 2 + k * (length / count)
        parts.append(sleeper(f"sl{k}", y, m))
        for sx in (-1, 1):
            fastening(f"f{k}{sx}", sx * RAIL_X, y, m, parts)
    if length >= 5:
        fishplates("fp", length / 2, m, parts)
    parts.append(ballast("ballast", length if length >= 5 else 2.0, m))
    o = hz.join(parts, name)
    hz.set_origin(o, (0, 0, 0))
    import metro_bunker
    metro_bunker.uv_box(o, 1.5)
    hz.smooth(o, 30)
    hz.selection(o, "rail")
    g = hz.box("geometry_bed", (3.3, length, 0.25), (0, 0, SLEEPER_TOP + 0.05 - 0.125), m["concrete"], round_edges=False)
    g.display_type = "WIRE"
    print(f"[Drezina] {name} faces: {len(o.data.polygons)}")
    save_fn(outdir, name)
