"""
Метро в стиле заброшенного советского бункера.

  bunker_entrance    голова бункера на поверхности: бетонный блок в земляной обваловке, гермодверь
                     в жёлто-чёрной окантовке, откосные стенки, вентиляционный грибок, табличка.
  bunker_inner_door  та же гермодверь изнутри — на верхней площадке лестницы («ВЫХОД»).
  bunker_stairs      лестничная шахта: 4 марша вниз (9.6 м) с площадками, перила, разделительная стена.
  bunker_corridor    коридор 8 м от лестницы к станции: трубы, кабели, балки.
  metro_station      станция 24 x 12 м: тюбинги, трубы, кабели, мусор, проход в коридор.
  tunnel_10m/2m      перегонный тоннель: тюбинги, трубы, кабели (2 м — для поворотов).

Освещения нет — внизу темно, нужен фонарик (свет даёт только дрезина).

Все размеры согласованы со скриптом (DrezinaConst в DrezinaConstants.c).
"""
import math
import os
import random

import bmesh
import bpy

import handcar_zone as hz

rnd = random.Random(17)

# --- размеры (см. DrezinaConst)
ST_W, ST_WALL_H, ST_RISE, ST_LEN = 12.0, 3.0, 2.6, 24.0
TUN_W, TUN_WALL_H, TUN_RISE = 6.0, 2.2, 2.8
WALL_T = 0.35
DOOR_X = -3.0                     # проход из станции в коридор (локальный X станции)
COR_LEN, COR_W, COR_H = 8.0, 2.4, 2.8
SH_X, SH_Y = 1.6, 3.0             # полуразмеры шахты изнутри
LEVEL = 2.4                       # высота марша
FLIGHTS = 4
STAIR_TOP = LEVEL * FLIGHTS       # 9.6
SH_H = STAIR_TOP + 3.2


# ============================================================================ материалы

def mats():
    hz.TEX_DIR = TEX_DIR
    m = hz.materials()
    m.update({
        "concrete": hz.tex_material("metro_concrete", "metro_concrete", 0.95),
        "wall": hz.tex_material("metro_wall", "metro_wall", 0.9),
        "hazard": hz.tex_material("metro_hazard", "metro_hazard", 0.8, 0.2),
        "door": hz.tex_material("metro_door", "metro_door", 0.7, 0.5),
        "tubing": hz.tex_material("metro_tubing", "metro_tubing", 0.7, 0.6),
        "dirt": hz.tex_material("metro_dirt", "metro_dirt", 1.0),
        "sign_in": hz.tex_material("metro_sign_entrance", "metro_sign_entrance", 0.8),
        "sign_out": hz.tex_material("metro_sign_exit", "metro_sign_exit", 0.8),
        "sign_station": hz.tex_material("metro_sign_station", "metro_sign_station", 0.8),
        "sign_depot": hz.tex_material("metro_sign_depot", "metro_sign_depot", 0.8),
        "tile": hz.tex_material("metro_tile", "metro_tile", 0.6),
        "puddle": hz.tex_material("metro_puddle", "metro_puddle", 0.05),
        "sign_rad": hz.tex_material("metro_sign_rad", "metro_sign_rad", 0.7),
        "board1": hz.tex_material("metro_sign_board1", "metro_sign_board1", 0.9),
        "board2": hz.tex_material("metro_sign_board2", "metro_sign_board2", 0.9),
        "board3": hz.tex_material("metro_sign_board3", "metro_sign_board3", 0.9),
        "board4": hz.tex_material("metro_sign_board4", "metro_sign_board4", 0.9),
        "board5": hz.tex_material("metro_sign_board5", "metro_sign_board5", 0.9),
        "board6": hz.tex_material("metro_sign_board6", "metro_sign_board6", 0.9),
        "board7": hz.tex_material("metro_sign_board7", "metro_sign_board7", 0.9),
        "board8": hz.tex_material("metro_sign_board8", "metro_sign_board8", 0.9),
        "board9": hz.tex_material("metro_sign_board9", "metro_sign_board9", 0.9),
        "board10": hz.tex_material("metro_sign_board10", "metro_sign_board10", 0.9),
        "board11": hz.tex_material("metro_sign_board11", "metro_sign_board11", 0.9),
        "sign_tp": hz.tex_material("metro_sign_tp", "metro_sign_tp", 0.7, 0.3),
        "wall_b": hz.tex_material("metro_wall_b", "metro_wall_b", 0.9),
        "wall_c": hz.tex_material("metro_wall_c", "metro_wall_c", 0.6),
        "concrete_ext": hz.tex_material("metro_concrete_ext", "metro_concrete_ext", 0.95),
        "plaster": hz.tex_material("metro_plaster", "metro_plaster", 0.95),
    })
    return m


TEX_DIR = None
box, cyl, torus, sphere, smooth = hz.box, hz.cyl, hz.torus, hz.sphere, hz.smooth
ROT_X, ROT_Y = hz.ROT_X, hz.ROT_Y


# ============================================================================ утилиты

# размер тайла по материалу (м): мелкий рисунок — мельче тайл
TILE_BY_MATERIAL = {"metro_hazard": 0.7, "metro_door": 1.2, "drezina_steel": 1.0, "drezina_rust": 1.0,
                    "drezina_paint_green": 1.0, "drezina_paint_blue": 1.0, "drezina_wood": 1.2,
                    "drezina_canvas": 0.8, "drezina_tape": 0.5, "metro_tubing": 1.5,
                    "drezina_ballast": 0.9, "drezina_railtop": 1.0, "metro_tile": 1.2}


def uv_box(obj, tile=3.0):
    """Плоская проекция по доминирующей оси в координатах объекта: v = высота / tile.
    Для стен это значит, что зелёная полоса краски всегда снизу (origin объекта на уровне пола)."""
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    uv = bm.loops.layers.uv.verify()
    slots = [ms.material.name if ms.material else "" for ms in obj.material_slots]
    for f in bm.faces:
        if f.material_index < len(slots) and (slots[f.material_index].startswith(("metro_sign", "drezina_plate"))
                                               or slots[f.material_index].endswith("_v")):
            continue   # таблички уже развёрнуты на всю текстуру
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        mname = slots[f.material_index] if f.material_index < len(slots) else ""
        t = TILE_BY_MATERIAL.get(mname, tile)
        for l in f.loops:
            x, y, z = l.vert.co
            if ax == 2:
                l[uv].uv = (x / t, y / t)
            elif ax == 0:
                l[uv].uv = (y / t, z / t)
            else:
                l[uv].uv = (x / t, z / t)
    bm.to_mesh(me)
    bm.free()


def join(parts, name):
    """Объединить и вернуть origin в (0,0,0): координаты вершин = координаты модели.
    Расстановка в скрипте считает от этой точки (в Object Builder — autocenter = 0)."""
    o = hz.join(parts, name)
    hz.set_origin(o, (0, 0, 0))
    return o


def finish(parts, name, tile=3.0):
    o = join(parts, name)
    uv_box(o, tile)
    smooth(o)
    hz.selection(o, name)
    return o


def uv_front(obj):
    """Табличка: лицевые грани (нормаль по ±Y) получают текстуру целиком, 0..1."""
    me = obj.data
    xs = [v.co.x for v in me.vertices]
    zs = [v.co.z for v in me.vertices]
    x0, x1, z0, z1 = min(xs), max(xs), min(zs), max(zs)
    bm = bmesh.new()
    bm.from_mesh(me)
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:
        for l in f.loops:
            x, y, z = l.vert.co
            # лицо смотрит в +Y: для зрителя +X слева, поэтому u растёт к -X (иначе надпись зеркальная)
            l[uv].uv = ((x1 - x) / (x1 - x0 + 1e-6), (z - z0) / (z1 - z0 + 1e-6))
    bm.to_mesh(me)
    bm.free()


def uv_top(obj, tile=4.0):
    """Развёртка сверху (по X/Y) для всей поверхности: на насыпи нет швов смены проекции."""
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:
        for l in f.loops:
            x, y, z = l.vert.co
            l[uv].uv = (x / tile, (y + z * 0.3) / tile)
    bm.to_mesh(me)
    bm.free()


def sign_plate(name, size, loc, mat):
    o = box(name, size, loc, mat, round_edges=False)
    uv_front(o)
    return o


def boolean_cut(target, cutter):
    mod = target.modifiers.new("cut", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    mod.solver = "EXACT"
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter)
    return target


def profile_prism(name, w, wall_h, rise, depth, y, segs=16):
    """Призма с сечением «стены + эллиптический свод» вдоль Y (для вырезов проёмов)."""
    pts = [(-w / 2, -0.01), (-w / 2, wall_h)]
    for i in range(1, segs):
        a = math.pi - math.pi * i / segs
        pts.append((math.cos(a) * w / 2, wall_h + math.sin(a) * rise))
    pts += [(w / 2, wall_h), (w / 2, -0.01)]
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    front = [bm.verts.new((x, y - depth / 2, z)) for x, z in pts]
    back = [bm.verts.new((x, y + depth / 2, z)) for x, z in pts]
    bm.faces.new(front[::-1])
    bm.faces.new(back)
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((front[i], front[j], back[j], back[i]))
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    o = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(o)
    return o


def keep_uv(mat):
    """Копия материала с суффиксом _v: uv_box не трогает её развёртку (своя, по длине дуги)."""
    name = mat.name + "_v"
    got = bpy.data.materials.get(name)
    if got:
        return got
    c = mat.copy()
    c.name = name
    return c


def arch_shell(name, a_in, b_in, t, wall_h, y, length, wall_mat, arc_mat, tile=3.0, segs=28):
    """Цельная оболочка «стены + эллиптический свод» одним мешем.
    Вершины общие по всей дуге, поэтому нормали плавные и свет фонаря ложится без полос;
    UV идёт по длине дуги — текстура не тянется и не прыгает между гранями."""
    wm, am = keep_uv(wall_mat), keep_uv(arc_mat)

    def profile(a, b):
        pts = [(-a, 0.0, True), (-a, wall_h, True)]
        for i in range(1, segs):
            th = math.pi - math.pi * i / segs
            pts.append((math.cos(th) * a, wall_h + math.sin(th) * b, False))
        pts += [(a, wall_h, True), (a, 0.0, True)]
        return pts

    inner, outer = profile(a_in, b_in), profile(a_in + t, b_in + t)
    s_in = [0.0]
    for i in range(1, len(inner)):
        s_in.append(s_in[-1] + math.dist(inner[i - 1][:2], inner[i][:2]))
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    y0, y1 = y - length / 2, y + length / 2
    vi = [(bm.verts.new((x, y0, z)), bm.verts.new((x, y1, z))) for x, z, _ in inner]
    vo = [(bm.verts.new((x, y0, z)), bm.verts.new((x, y1, z))) for x, z, _ in outer]
    uv = bm.loops.layers.uv.verify()
    faces = []
    n = len(inner)
    for k in range(n - 1):
        is_wall = inner[k][2] and inner[k + 1][2]
        mi = 0 if is_wall else 1
        # внутренняя поверхность (нормаль внутрь тоннеля)
        f = bm.faces.new((vi[k][0], vi[k][1], vi[k + 1][1], vi[k + 1][0]))
        f.material_index = mi
        for l in f.loops:
            j = vi.index(next(p for p in vi if l.vert in p))
            yy = l.vert.co.y
            l[uv].uv = (yy / tile, l.vert.co.z / tile) if is_wall else (yy / tile, s_in[j] / tile)
        faces.append(f)
        # внешняя поверхность
        f = bm.faces.new((vo[k][0], vo[k + 1][0], vo[k + 1][1], vo[k][1]))
        f.material_index = 1
        for l in f.loops:
            j = vo.index(next(p for p in vo if l.vert in p))
            l[uv].uv = (l.vert.co.y / tile, s_in[j] / tile)
    # торцы
    for e in (0, 1):
        for k in range(n - 1):
            q = (vi[k][e], vo[k][e], vo[k + 1][e], vi[k + 1][e])
            f = bm.faces.new(q if e == 1 else q[::-1])
            f.material_index = 1
            for l in f.loops:
                l[uv].uv = (l.vert.co.x / tile, l.vert.co.z / tile)
    # низ стен
    for k in (0, n - 1):
        f = bm.faces.new((vi[k][0], vo[k][0], vo[k][1], vi[k][1]) if k == 0 else (vi[k][0], vi[k][1], vo[k][1], vo[k][0]))
        f.material_index = 0
        for l in f.loops:
            l[uv].uv = (l.vert.co.x / tile, l.vert.co.y / tile)
    # замкнутое тело: нормали наружу от бетона = внутрь тоннеля на внутренней поверхности
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    # имя UV-слоя как у примитивов: иначе при join развёртка уходит во второй слой и
    # в игре на всю поверхность растягивается один пиксель («голая мыльная» текстура)
    if mesh.uv_layers:
        mesh.uv_layers[0].name = "UVMap"
        mesh.uv_layers.active = mesh.uv_layers[0]
    o = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(wm)
    o.data.materials.append(am)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def vault(prefix, w, wall_h, rise, length, y, wall_mat, vault_mat, t=WALL_T, segs=28):
    """Стены (двухцветная краска) + эллиптический свод — одной гладкой оболочкой."""
    return [arch_shell(f"{prefix}_vault", w / 2, rise, t, wall_h, y, length, wall_mat, vault_mat, 3.0, segs)]


def rib(prefix, w, wall_h, rise, y, mat, depth=0.22, t=0.14, segs=28):
    """Чугунный тюбинг-ребро по контуру свода (выступает внутрь) — цельное кольцо."""
    parts = [arch_shell(f"{prefix}_ring", w / 2 - t, rise - t, t, wall_h, y, depth, mat, mat, 1.5, segs)]
    a = w / 2 - t / 2
    # болты на стыке сегментов
    for sx in (-1, 1):
        for z in (0.6, 1.4, 2.0):
            if z < wall_h:
                parts.append(hz.bolt(f"{prefix}_b{sx}{z}", (sx * (a - t / 2), y + depth / 2 - 0.02, z), "x" if sx < 0 else "-x", mat, 0.018))
    # заклёпки по дуге на обеих гранях кольца и фланцы стыков сегментов
    ra, rb = a, rise - t / 2
    for k in range(1, 12):
        th = math.pi * k / 12
        px, pz = math.cos(th) * ra, wall_h + math.sin(th) * rb
        for sy in (-1, 1):
            if (k + (sy > 0)) % 2 == 0:     # через одну на каждой грани (бюджет треугольников станции)
                parts.append(hz.bolt(f"{prefix}_r{k}{sy}", (px, y + sy * (depth / 2 + 0.004), pz), "y" if sy > 0 else "-y", mat, 0.014))
        if k % 3 == 0:     # стык сегментов: утолщённый фланец
            ang = th - math.pi / 2
            parts.append(box(f"{prefix}_fl{k}", (0.05, depth + 0.04, t + 0.04), (px, y, pz), mat, (0, ang, 0)))
    return parts


def pipes_along(prefix, x, zs, length, y, m, radii=None, brackets=3.0):
    parts = []
    radii = radii or [0.07] * len(zs)
    for k, (z, r) in enumerate(zip(zs, radii)):
        parts.append(cyl(f"{prefix}_p{k}", r, length, (x, y, z), m["rust"] if k % 2 == 0 else m["paint"], ROT_Y))
    n = max(1, int(length / brackets))
    for i in range(n):
        yy = y - length / 2 + (i + 0.5) * length / n
        parts.append(box(f"{prefix}_br{i}", (0.06, 0.05, (max(zs) - min(zs)) + 0.25), (x + math.copysign(0.05, -x), yy, (max(zs) + min(zs)) / 2), m["steel"]))
        # фланец
        parts.append(cyl(f"{prefix}_fl{i}", radii[0] * 1.35, 0.04, (x, yy + 0.3, zs[0]), m["rust"], ROT_Y))
    return parts


def cables_along(prefix, x, z, length, y, m, count=4):
    parts = []
    for k in range(count):
        parts.append(cyl(f"{prefix}_c{k}", 0.018, length, (x, y, z - k * 0.045), m["tape"], ROT_Y, 10))
    n = max(1, int(length / 1.5))
    for i in range(n):
        yy = y - length / 2 + (i + 0.5) * length / n
        parts.append(box(f"{prefix}_hook{i}", (0.12, 0.02, 0.02), (x + math.copysign(0.05, -x), yy, z - count * 0.045), m["steel"]))
    return parts


def debris(prefix, center, count, spread, m):
    parts = []
    for i in range(count):
        s = rnd.uniform(0.08, 0.3)
        p = (center[0] + rnd.uniform(-spread, spread), center[1] + rnd.uniform(-spread, spread), s * 0.35)
        parts.append(box(f"{prefix}{i}", (s, s * rnd.uniform(0.6, 1.2), s * 0.6), p, m["concrete"],
                         (rnd.uniform(-0.4, 0.4), rnd.uniform(-0.4, 0.4), rnd.uniform(0, 3))))
    return parts


def geo(name, size, loc, rot=(0, 0, 0)):
    o = box(name, size, loc, hz.tex_material("geometry", "geometry"), rot, round_edges=False)
    o.display_type = "WIRE"
    return o


# ============================================================================ гермодверь

def blast_door(prefix, w, h, y_front, m, z0=0.0):
    """Гермодверь: толстое полотно со скруглёнными углами, обвязка, заклёпки, петли, штурвал, засовы,
    смотровой глазок. Полотно лицом к +Y, низ на z0."""
    p = []
    t = 0.18
    yc = y_front - t / 2
    leaf = box(f"{prefix}_leaf", (w, t, h), (0, yc, z0 + h / 2), m["door"], round_edges=False)
    hz.bevel(leaf, 0.06, 3)
    p.append(leaf)
    # обвязка по периметру
    for sx in (-1, 1):
        p.append(box(f"{prefix}_st{sx}", (0.1, 0.04, h - 0.1), (sx * (w / 2 - 0.07), y_front + 0.02, z0 + h / 2), m["door"]))
    for sz in (0, 1):
        p.append(box(f"{prefix}_rl{sz}", (w - 0.1, 0.04, 0.1), (0, y_front + 0.02, z0 + 0.07 + sz * (h - 0.14)), m["door"]))
    p.append(box(f"{prefix}_mid", (w - 0.2, 0.03, 0.08), (0, y_front + 0.015, z0 + h * 0.55), m["door"]))
    # заклёпки
    for i in range(12):
        f = i / 11
        for sx in (-1, 1):
            p.append(sphere(f"{prefix}_rv{sx}{i}", 0.014, (sx * (w / 2 - 0.07), y_front + 0.04, z0 + 0.12 + f * (h - 0.24)), m["steel"], (1, 0.6, 1), (8, 5)))
    # петли
    for z in (0.35, h - 0.35):
        p.append(cyl(f"{prefix}_hinge{z}", 0.05, 0.28, (-w / 2 - 0.03, y_front - 0.05, z0 + z), m["rust"]))
        p.append(box(f"{prefix}_hplate{z}", (0.3, 0.025, 0.14), (-w / 2 + 0.1, y_front + 0.01, z0 + z), m["rust"]))
    # штурвал
    wz = z0 + h * 0.55
    p.append(torus(f"{prefix}_wheel", 0.24, 0.022, (0, y_front + 0.14, wz), m["steel"], ROT_Y, (32, 10)))
    for k in range(4):
        a = k * math.pi / 4
        p.append(box(f"{prefix}_ws{k}", (0.46, 0.025, 0.025), (0, y_front + 0.14, wz), m["steel"], (0, a, 0)))
    p.append(cyl(f"{prefix}_hub", 0.05, 0.16, (0, y_front + 0.08, wz), m["rust"], ROT_Y))
    # засовы
    for sz in (-1, 1):
        p.append(box(f"{prefix}_bolt{sz}", (w * 0.75, 0.04, 0.05), (0.05, y_front + 0.05, wz + sz * 0.42), m["steel"]))
        p.append(box(f"{prefix}_bguide{sz}", (0.08, 0.06, 0.09), (w / 2 - 0.15, y_front + 0.05, wz + sz * 0.42), m["rust"]))
    # глазок
    p.append(cyl(f"{prefix}_port", 0.06, 0.05, (0, y_front + 0.02, z0 + h * 0.82), m["steel"], ROT_Y))
    p.append(cyl(f"{prefix}_glass", 0.04, 0.06, (0, y_front + 0.025, z0 + h * 0.82), m["tape"], ROT_Y))
    return p


def door_frame(prefix, w, h, y_front, m, z0=0.0):
    """Стальная коробка с жёлто-чёрной окантовкой вокруг проёма."""
    p = []
    fw = 0.18
    for sx in (-1, 1):
        p.append(box(f"{prefix}_fs{sx}", (fw, 0.3, h + fw), (sx * (w / 2 + fw / 2), y_front - 0.1, z0 + (h + fw) / 2), m["hazard"]))
    p.append(box(f"{prefix}_ft", (w + 2 * fw, 0.3, fw), (0, y_front - 0.1, z0 + h + fw / 2), m["hazard"]))
    p.append(box(f"{prefix}_sill", (w + 2 * fw, 0.3, 0.06), (0, y_front - 0.1, z0 + 0.03), m["steel"]))
    return p


# ============================================================================ голова бункера на поверхности

def earth_mound(name, center, scale, cut_y, mat, bottom=-0.05):
    """Земляной купол, обрезанный вертикальной плоскостью спереди (y > cut_y) и снизу (z < 0)."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=40, ring_count=20, radius=1, location=(0, 0, 0))
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    o.location = center
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    me = o.data
    bm = bmesh.new()
    bm.from_mesh(me)
    # бугристость
    for v in bm.verts:
        n = math.sin(v.co.x * 1.3) * math.sin(v.co.y * 1.1) + 0.5 * math.sin(v.co.x * 3.1 + v.co.y * 2.3)
        v.co += v.normal * n * 0.18
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, cut_y, 0), plane_no=(0, 1, 0), clear_outer=True)
    bmesh.ops.holes_fill(bm, edges=bm.edges[:], sides=0)          # закрыть срез спереди
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, bottom), plane_no=(0, 0, -1), clear_outer=True)
    bmesh.ops.holes_fill(bm, edges=bm.edges[:], sides=0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    o.data.materials.append(mat)
    return o


def control_panel(prefix, loc, m):
    """Пульт у двери: шкаф с козырьком, красная лампа, рубильник, кабель в стену."""
    x, y, z = loc
    p = [box(f"{prefix}_box", (0.45, 0.18, 0.6), (x, y + 0.09, z), m["paint"]),
         box(f"{prefix}_visor", (0.5, 0.12, 0.03), (x, y + 0.2, z + 0.32), m["rust"], (math.radians(-15), 0, 0)),
         box(f"{prefix}_door", (0.38, 0.02, 0.5), (x, y + 0.19, z), m["paint"]),
         sphere(f"{prefix}_lamp", 0.035, (x - 0.1, y + 0.21, z + 0.15), m["sign_in"], (1, 0.7, 1), (12, 8)),
         box(f"{prefix}_slot", (0.12, 0.02, 0.02), (x + 0.08, y + 0.205, z + 0.15), m["tape"]),
         box(f"{prefix}_switch", (0.04, 0.05, 0.14), (x + 0.1, y + 0.22, z - 0.1), m["steel"], (math.radians(-25), 0, 0)),
         cyl(f"{prefix}_conduit", 0.02, 0.9, (x, y + 0.05, z - 0.75), m["steel"])]
    return p


def mh_rod(name, a, b, r, mat, out):
    import motor_handcar as mh
    mh.rod(name, a, b, r, mat, out)


def hull(name, pts, mat):
    """Выпуклый многогранник по точкам (подпорные стенки, оголовки, обломки)."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    for p in pts:
        bm.verts.new(p)
    bmesh.ops.convex_hull(bm, input=bm.verts[:])
    loose = [v for v in bm.verts if not v.link_faces]          # точки внутри оболочки — не нужны
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(mat)
    return o


# подпорные стенки входа: от портала (y=0) вперёд на WING_L, расходятся наружу и понижаются к краю
WING_L = 3.6
WING_X0 = 2.15          # внутренняя грань у портала
WING_FLARE = math.radians(22)
WING_T = 0.45
WING_H0, WING_H1 = 3.3, 0.25


def wing_x(y):
    return WING_X0 + y * math.tan(WING_FLARE)


def wing_top(y):
    return WING_H0 + (WING_H1 - WING_H0) * max(0.0, min(1.0, y / WING_L))


def smax(a, b, k=2.5):
    """Гладкий максимум: без излома на стыке двух поверхностей."""
    m = max(a, b)
    return m + math.log(math.exp((a - m) * k) + math.exp((b - m) * k)) / k


def smin(a, b, k=2.5):
    return -smax(-a, -b, k)


def soil_patch(x, y):
    """Проплешины земли на насыпи: несколько крупных пятен и вытоптанная полоса вдоль стенок."""
    v = 0.5 + 0.5 * math.sin(x * 0.55 + 1.3) * math.sin(y * 0.47 + 0.4) + 0.25 * math.sin(x * 1.3 + y * 0.9 + 2.0)
    if y > -1.5:
        wx = wing_x(max(y, 0.0)) + WING_T
        if abs(x) - wx < 1.2:
            v += 0.6
    return v


def bunker_mound(name, mat, soil_mat=None):
    """Насыпь: неровный холм за порталом, по бокам спускается по стенкам, края уходят в землю."""
    nx, ny = 110, 66                 # ~0.2 м: края проплешин и перегибы без «ступенек»
    x0, x1, y0, y1 = -11.0, 11.0, -9.5, WING_L + 1.5
    rnd = random.Random(41)
    waves = [(rnd.uniform(0.15, 0.5), rnd.uniform(0.15, 0.5), rnd.uniform(0, 6.28), a) for a in (0.3, 0.2, 0.12, 0.08, 0.05)]
    def noise(x, y):
        return sum(a * math.sin(fx * x * (1 + i) + fy * y * (1 + i) + ph) for i, (fx, fy, ph, a) in enumerate(waves))
    def height(x, y):
        # короткий холм: укрывает только тело бункера (4 м за дверью) и сразу сходит назад
        dx, dy = x / 9.0, (y + 2.2) / 5.2
        d = math.sqrt(dx * dx + dy * dy)
        h = 4.4 * max(0.0, 1 - d * d) ** 1.2 - 0.7
        h += noise(x, y) * 0.5 * max(0.0, 1 - d)
        if y < -0.3:
            # насыпь укрывает тело бункера до козырька и плавно сходит в стороны и назад
            ax = max(0.0, abs(x) - 2.6)
            ay = max(0.0, -y - 4.3)
            h = smax(h, 3.85 - 0.16 * ax * ax - 0.45 * ay * ay + noise(x, y) * 0.1, 1.6)
        else:
            # перед порталом: внутри стенок — земли нет, снаружи — земля держится по верху стенок
            wx = wing_x(min(max(y, 0.0), WING_L)) + WING_T
            if y <= WING_L and abs(x) < wx - 0.1:
                return -0.9                       # между стенками (срез прячется в их толще)
            top = wing_top(max(y, 0.0)) - 0.05
            if y > WING_L:
                # за торцами стенок — плавно сходит к земле, без обрывов
                top = smin(top, 0.25 - 0.7 * (y - WING_L), 3.0)
            fall = (abs(x) - wx) / 3.5
            h = smin(smax(h, top - fall * fall * 2.5, 1.6), top, 3.0) + noise(x, y) * 0.08
        return max(h, -0.9)
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    vs = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            x = x0 + (x1 - x0) * i / nx
            y = y0 + (y1 - y0) * j / ny
            row.append(bm.verts.new((x, y, height(x, y))))
        vs.append(row)
    jr = random.Random(13)
    for j in range(ny):
        for i in range(nx):
            # квадрат — двумя треугольниками, диагональ чередуется (не видно сетки)
            a, b, c2, d = vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]
            tris = ((a, b, c2), (a, c2, d)) if (i + j) % 2 == 0 else ((a, b, d), (b, c2, d))
            for tri in tris:
                f = bm.faces.new(tri)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(mat)
    if soil_mat is not None:
        o.data.materials.append(soil_mat)
    MOUND_PTS[:] = [tuple(v.co) for v in me.vertices]
    MOUND_H[0] = height
    MOUND_GRID[:] = [x0, x1, y0, y1, nx, ny]
    return o


MOUND_H = [None]
MOUND_GRID = []


def mound_texture(tex_dir):
    """Одна текстура на всю насыпь (2048x2048): трава и земля смешаны плавно — по проплешинам
    (soil_patch) и крутизне склона. Плавный переход без «ступенек» по треугольникам."""
    import numpy as np
    x0, x1, y0, y1, nx, ny = MOUND_GRID
    N = 2048
    def load(name):
        img = bpy.data.images.load(os.path.join(tex_dir, name), check_existing=True)
        w, h = img.size
        a = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, img.channels)[:, :, :3]
        return a                                       # строки снизу вверх (как в Blender)
    gr = load("metro_grass_co.png")
    so = load("metro_soil_co.png")
    gn = load("metro_grass_nohq.png")
    sn = load("metro_soil_nohq.png")
    xs = x0 + (np.arange(N) + 0.5) / N * (x1 - x0)
    ys = y0 + (np.arange(N) + 0.5) / N * (y1 - y0)    # строка 0 — низ (y0), как пиксели Blender
    X, Y = np.meshgrid(xs, ys)
    tile = 3.5
    def sample(t):
        th, tw = t.shape[:2]
        ui = ((X / tile) * tw).astype(np.int64) % tw
        vi = ((Y / tile) * th).astype(np.int64) % th
        return t[vi, ui]
    G, S, GN, SN = sample(gr), sample(so), sample(gn), sample(sn)
    sp = 0.5 + 0.5 * np.sin(X * 0.55 + 1.3) * np.sin(Y * 0.47 + 0.4) + 0.25 * np.sin(X * 1.3 + Y * 0.9 + 2.0)
    wx = WING_X0 + np.maximum(Y, 0.0) * math.tan(WING_FLARE) + WING_T
    sp = sp + np.where((Y > -1.5) & (np.abs(X) - wx < 1.2), 0.6, 0.0)
    # рваный край — случайным шумом (не синусоидами: от них шли полосы)
    rr = np.random.RandomState(3)
    nz = rr.rand(N // 16 + 2, N // 16 + 2)
    nzx = np.array([np.interp(np.arange(N) / 16.0, np.arange(nz.shape[1]), row) for row in nz])
    nzi = np.array([np.interp(np.arange(N) / 16.0, np.arange(nz.shape[0]), nzx[:, c]) for c in range(N)]).T
    fine = rr.rand(N // 4 + 2, N // 4 + 2)
    fx = np.array([np.interp(np.arange(N) / 4.0, np.arange(fine.shape[1]), row) for row in fine])
    fi = np.array([np.interp(np.arange(N) / 4.0, np.arange(fine.shape[0]), fx[:, c]) for c in range(N)]).T
    sp = sp + (nzi - 0.5) * 0.28 + (fi - 0.5) * 0.12
    # крутизна по высотам сетки насыпи
    Z = np.array([p[2] for p in MOUND_PTS]).reshape(ny + 1, nx + 1)
    gx = np.linspace(x0, x1, nx + 1)
    gy = np.linspace(y0, y1, ny + 1)
    # крутизна — по узлам сетки (сглаженная), потом плавно растягиваем на пиксели
    dzdy, dzdx = np.gradient(Z, (y1 - y0) / ny, (x1 - x0) / nx)
    sg = np.sqrt(dzdx ** 2 + dzdy ** 2)
    for _ in range(3):
        sg = (sg + np.roll(sg, 1, 0) + np.roll(sg, -1, 0) + np.roll(sg, 1, 1) + np.roll(sg, -1, 1)) / 5.0
    sx = np.array([np.interp(xs, gx, row) for row in sg])
    slope = np.array([np.interp(ys, gy, sx[:, c]) for c in range(N)]).T
    def sstep(a, b, v):
        t = np.clip((v - a) / (b - a), 0, 1)
        return t * t * (3 - 2 * t)
    m = np.maximum(sstep(0.82, 1.08, sp), sstep(1.1, 1.8, slope))[..., None]
    col = G * (1 - m) + S * m
    nrm = GN * (1 - m) + SN * m
    def save(arr, name):
        img = bpy.data.images.new(name, N, N, alpha=False)
        rgba = np.concatenate([arr, np.ones((N, N, 1), dtype=arr.dtype)], axis=2)
        img.pixels = rgba.astype(np.float32).ravel().tolist()
        img.filepath_raw = os.path.join(tex_dir, name + ".png")
        img.file_format = "PNG"
        img.save()
    save(col, "metro_mound_co")
    save(nrm, "metro_mound_nohq")


def uv_mound(obj):
    """Насыпь целиком на одну текстуру: проекция сверху по её границам."""
    x0, x1, y0, y1 = MOUND_GRID[:4]
    me = obj.data
    # развёртка — в обычный слой UVMap: сетка насыпи создана без UV, и bmesh иначе заводит отдельный
    # слой, который при объединении с бетоном не становится основным (насыпь была одним цветом)
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    bm = bmesh.new()
    bm.from_mesh(me)
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:
        for l in f.loops:
            x, y, z = l.vert.co
            l[uv].uv = ((x - x0) / (x1 - x0), (y - y0) / (y1 - y0))
    bm.to_mesh(me)
    bm.free()


def grass_tufts(name, count, seed):
    """Пучки сухой травы на насыпи: по три перекрещенные двусторонние плоскости с текстурой
    травы с альфой (_ca). Нормали смотрят вверх — пучки освещаются как земля под ними."""
    height = MOUND_H[0]
    rnd = random.Random(seed)
    mat = bpy.data.materials.get("metro_drygrass") or bpy.data.materials.new("metro_drygrass")
    mat["dayz_texture"] = "Drezina\\data\\textures\\metro_drygrass_ca.paa"
    mat["dayz_rvmat"] = ""
    # для превью в Blender: та же текстура с альфой
    mat.use_nodes = True
    path = os.path.join(TEX_DIR or "", "metro_drygrass_ca.png")
    if TEX_DIR and os.path.exists(path) and not any(n.type == "TEX_IMAGE" for n in mat.node_tree.nodes):
        img = mat.node_tree.nodes.new("ShaderNodeTexImage")
        img.image = bpy.data.images.load(path, check_existing=True)
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        mat.node_tree.links.new(img.outputs["Color"], bsdf.inputs["Base Color"])
        mat.node_tree.links.new(img.outputs["Alpha"], bsdf.inputs["Alpha"])
        mat.blend_method = "CLIP" if hasattr(mat, "blend_method") else None
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new()
    placed = 0
    tries = 0
    while placed < count and tries < count * 30:
        tries += 1
        cx, cy = rnd.uniform(-10.5, 10.5), rnd.uniform(-9.0, WING_L + 1.2)
        if cy > -0.6 and abs(cx) < wing_x(max(cy, 0.0)) + WING_T + 0.3:
            continue                                  # перед дверью и на стенках — нет
        if (cx - 1.8) ** 2 + (cy + 2.6) ** 2 < 0.6:
            continue                                  # у вентиляционной трубы
        h = height(cx, cy)
        sp = soil_patch(cx, cy)
        if h < 0.1 or sp > 1.02 or (sp > 0.85 and rnd.random() < 0.3):
            continue                                  # на проплешинах травы нет, по их краю — гуще
        for _ in range(rnd.randint(1, 3)):            # куртинка из 1-3 пучков
            x, y = cx + rnd.uniform(-0.6, 0.6), cy + rnd.uniform(-0.6, 0.6)
            z = height(x, y) - 0.08
            w = rnd.uniform(0.6, 1.1)
            th = rnd.uniform(0.45, 0.85)
            a0 = rnd.uniform(0, math.pi)
            for k in range(3):
                a = a0 + k * math.pi / 3
                dx, dy = math.cos(a) * w / 2, math.sin(a) * w / 2
                lean = rnd.uniform(-0.08, 0.08)
                # нижние углы — по склону (каждый на своей высоте), иначе на склоне под пучком торчали
                # треугольники голой земли
                za = height(x - dx, y - dy) - 0.1
                zb = height(x + dx, y + dy) - 0.1
                corners = [(x - dx, y - dy, za), (x + dx, y + dy, zb), (x + dx + lean, y + dy, zb + th), (x - dx + lean, y - dy, za + th)]
                for order in ((0, 1, 2, 3), (1, 0, 3, 2)):          # обе стороны (свои вершины у каждой)
                    vv = [bm.verts.new(corners[i]) for i in order]
                    f = bm.faces.new(vv)
                    for l, i in zip(f.loops, order):
                        l[uv].uv = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))[i]
            placed += 1
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(mat)
    me.normals_split_custom_set([(0.0, 0.0, 1.0)] * len(me.loops))
    return o


MOUND_PTS = []


def rock(name, loc, size, mat, seed):
    """Камень: сглаженная икосфера с буграми, приплюснутая, наполовину в земле."""
    r = random.Random(seed)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=size, location=loc)
    o = bpy.context.active_object
    o.name = name
    for v in o.data.vertices:
        n = v.co.normalized()
        k = 1 + 0.22 * math.sin(n.x * 4.1 + seed) * math.sin(n.y * 3.3 + seed * 0.7) + r.uniform(-0.06, 0.06)
        v.co = v.co * k
    o.scale = (r.uniform(0.9, 1.3), r.uniform(0.8, 1.1), r.uniform(0.45, 0.7))
    o.rotation_euler = (0, 0, r.uniform(0, 6.28))
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    o.data.materials.append(mat)
    hz.smooth(o, 60)
    return o


def rubble(name, loc, size, mat, seed):
    """Бетонный обломок: неправильный многогранник."""
    r = random.Random(seed)
    x, y, z = loc
    pts = [(x + r.uniform(-1, 1) * size, y + r.uniform(-1, 1) * size * 0.8, z + r.uniform(0, 1) * size * 0.7) for _ in range(12)]
    return hull(name, pts, mat)


def sandbag(name, loc, rotz, m):
    o = box(name, (0.62, 0.34, 0.16), loc, m["canvas"], (0, 0, rotz))
    hz.bevel(o, 0.06, 3)
    return o


def build_entrance(outdir, save_fn, reset_fn):
    """Голова бункера в духе советских объектов: бетонный портал с фаской, дверь в нише, подпорные
    стенки-трапеции, неровная земляная насыпь с травой. Origin — земля перед порталом по центру
    двери. Фасад смотрит в +Y."""
    reset_fn()
    m = mats()
    m["grass"] = hz.tex_material("metro_grass", "metro_grass", 1.0)
    ce = m["concrete_ext"]
    p = []
    BW, BD, BH = 4.6, 4.0, 3.2
    # тело бункера в насыпи (видно только портал)
    p.append(box("block", (BW, BD, BH + 3.0), (0, -BD / 2, (BH - 3.0) / 2), ce))
    # портал: массивная рамка с фаской, ниша двери глубиной 0.5 м
    p.append(box("portal_l", (1.0, 0.7, 3.6), (-1.48, 0.15, 1.8), ce))
    p.append(box("portal_r", (1.0, 0.7, 3.6), (1.48, 0.15, 1.8), ce))
    p.append(box("portal_top", (1.96, 0.7, 0.98), (0, 0.15, 3.11), ce))
    # козырёк — плита с капельником и косыми консолями
    p.append(box("visor", (4.9, 1.3, 0.24), (0, 0.55, 3.72), ce))
    p.append(box("visor_drip", (4.9, 0.08, 0.1), (0, 1.17, 3.56), ce))
    for sx in (-1, 1):
        p.append(hull(f"visor_bracket{sx}", [(sx * 1.6, 0.5, 3.6), (sx * 2.0, 0.5, 3.6), (sx * 1.6, 1.1, 3.6), (sx * 2.0, 1.1, 3.6),
                                             (sx * 1.6, 0.5, 2.9), (sx * 2.0, 0.5, 2.9)], ce))
    # проём ниши: бетонные откосы и порог
    p.append(box("niche_floor", (2.2, 1.0, 0.12), (0, 0.0, 0.06), m["concrete"]))
    for sx in (-1, 1):
        p.append(box(f"portal_foot{sx}", (1.0, 0.7, 2.0), (sx * 1.48, 0.15, -1.0), ce))
    # подпорные стенки-трапеции и их оголовки
    for sx in (-1, 1):
        pts = []
        for y, zt in ((0.0, WING_H0), (WING_L, WING_H1)):
            xi = sx * wing_x(y)
            xo = sx * (wing_x(y) + WING_T)
            for x in (xi, xo):
                pts += [(x, y, zt), (x, y, -1.2)]
        p.append(hull(f"wing{sx}", pts, ce))
        cap = []
        for y, zt in ((-0.05, WING_H0), (WING_L + 0.05, WING_H1)):
            for x in (sx * (wing_x(y) - 0.06), sx * (wing_x(y) + WING_T + 0.06)):
                cap += [(x, y, zt + 0.14), (x, y, zt - 0.02)]
        p.append(hull(f"wing_cap{sx}", cap, ce))
        # торчащая арматура на торце стенки
        for k in range(3):
            y = WING_L - 0.02
            x = sx * (wing_x(y) + 0.1 + k * 0.12)
            mh_rod(f"rebar{sx}{k}", (x, y, WING_H1 + 0.1), (x + sx * 0.05 * (k - 1), y + 0.15, WING_H1 + 0.45 + k * 0.08), 0.009, m["rust"], p)
    # отмостка перед дверью с водостоком и решёткой
    p.append(box("apron", (4.2, WING_L + 0.4, 2.0), (0, WING_L / 2, -0.98), m["concrete"]))
    p.append(box("drain", (3.0, 0.3, 0.06), (0, 1.6, 0.0), m["rust"]))
    for k in range(14):
        p.append(box(f"drain_bar{k}", (0.03, 0.3, 0.04), (-1.4 + k * 0.215, 1.6, 0.03), m["steel"]))
    # дверь в жёлто-чёрной коробке, глубже лица портала
    dw, dh = 1.6, 2.4
    p += door_frame("df", dw, dh, 0.2, m)
    p += blast_door("door", dw, dh, 0.2, m)
    p += control_panel("panel", (1.48, 0.5, 1.35), m)
    p.append(sign_plate("sign", (0.8, 0.03, 0.4), (-1.48, 0.515, 1.95), m["sign_in"]))
    # светильник-клетка над дверью и кабель к нему
    # над дверью — аварийный маячок (ставит скрипт: Drezina_AlarmLamp со светом и звуком)
    mh_rod("lamp_cable", (0.0, 0.5, 3.08), (1.2, 0.52, 3.08), 0.012, m["tape"], p)
    mh_rod("lamp_cable2", (1.2, 0.52, 3.08), (1.3, 0.52, 1.7), 0.012, m["tape"], p)
    # мешки с песком у левой стенки и обломки бетона у правой
    for k, (x, y, z, r) in enumerate([(-1.55, 2.3, 0.08, 0.1), (-1.5, 2.95, 0.08, -0.15), (-1.52, 2.62, 0.24, 0.05)]):
        p.append(sandbag(f"sandbag{k}", (x, y, z), r, m))
    for k, (x, y, s) in enumerate([(1.7, 2.9, 0.28), (1.45, 3.4, 0.18), (3.9, 3.8, 0.35), (-4.2, 3.2, 0.3)]):
        p.append(rubble(f"rubble{k}", (x, y, -0.05), s, ce, 100 + k))
    # вентиляционная труба над насыпью: фланец, колпак, растяжки
    p.append(cyl("vent", 0.16, 2.6, (1.8, -2.6, 3.0), m["rust"]))
    p.append(cyl("vent_flange", 0.26, 0.06, (1.8, -2.6, 3.55), m["rust"]))
    p.append(hz.cone("vent_cap", 0.38, 0.05, 0.28, (1.8, -2.6, 4.4), m["rust"], (0, 0, 0), 24))
    for k in range(3):
        a = k * 2.094
        p.append(box(f"vent_leg{k}", (0.03, 0.03, 0.3), (1.8 + math.cos(a) * 0.2, -2.6 + math.sin(a) * 0.2, 4.15), m["rust"]))
    concrete = join(p, "bunker_entrance")
    uv_box(concrete, 2.4)
    mound = bunker_mound("mound", None)
    mound_texture(TEX_DIR)
    m["mound"] = hz.tex_material("metro_mound", "metro_mound", 1.0)
    mound.data.materials.clear()
    mound.data.materials.append(m["mound"])
    uv_mound(mound)
    # камни на насыпи — в основном на проплешинах
    sr = random.Random(5)
    stones = []
    tries = 0
    while len(stones) < 34 and tries < 3000:
        tries += 1
        x, y = sr.uniform(-10, 10), sr.uniform(-8.5, WING_L + 1.0)
        if y > -0.6 and abs(x) < wing_x(max(y, 0.0)) + WING_T + 0.3:
            continue
        if soil_patch(x, y) < 0.8 and sr.random() < 0.8:
            continue
        hz_ = MOUND_H[0](x, y)
        if hz_ < -0.2:
            continue
        stones.append(rock(f"stone{len(stones)}", (x, y, hz_ - 0.05), sr.uniform(0.12, 0.34), m["concrete_ext"], 300 + len(stones)))
    st = join(stones, "stones")
    uv_box(st, 1.5)
    o = join([concrete, mound, st], "bunker_entrance")
    smooth(o, 40)
    hz.selection(o, "bunker_entrance")
    tufts = grass_tufts("bunker_grass", 520, 77)
    hz.selection(tufts, "bunker_entrance")
    # геометрия
    geo("geometry_block", (BW, BD, 6.6), (0, -BD / 2, 0.3))
    geo("geometry_apron", (4.2, WING_L + 0.4, 2.0), (0, WING_L / 2, -0.98))
    for sx in (-1, 1):
        geo(f"geometry_portal{sx}", (1.0, 0.7, 3.6), (sx * 1.48, 0.15, 1.8))
        ym = WING_L / 2
        geo(f"geometry_wing{sx}", (WING_T, WING_L / math.cos(WING_FLARE), (WING_H0 + WING_H1) / 2 + 1.2),
            (sx * (wing_x(ym) + WING_T / 2), ym, ((WING_H0 + WING_H1) / 2 - 1.2) / 2), (0, 0, -sx * WING_FLARE))
    geo("geometry_portal_top", (1.96, 0.7, 0.98), (0, 0.15, 3.11))
    geo("geometry_door", (1.96, 0.3, 2.58), (0, 0.1, 1.29))
    # насыпь: выпуклые куски по форме холма (по сетке 4 м), только из точек над землёй —
    # ни один кусок не перекрывает проход к двери
    xs = [-11, -7.5, -4, 0, 4, 7.5, 11]
    ys = [-9.5, -6.5, -3.5, -0.3, WING_L + 1.5]
    gi = 0
    for ix in range(len(xs) - 1):
        for iy in range(len(ys) - 1):
            pts = [c for c in MOUND_PTS if xs[ix] - 0.2 <= c[0] <= xs[ix + 1] + 0.2 and ys[iy] - 0.2 <= c[1] <= ys[iy + 1] + 0.2 and c[2] > 0.05]
            if len(pts) < 4:
                continue
            hp = pts + [(c[0], c[1], -1.0) for c in pts]
            g = hull(f"geometry_mound{gi}", hp, hz.tex_material("geometry", "geometry"))
            g.display_type = "WIRE"
            gi += 1
    save_fn(outdir, "bunker_entrance")


# ============================================================================ дверь изнутри (верх лестницы)

def build_inner_door(outdir, save_fn, reset_fn):
    reset_fn()
    m = mats()
    p = []
    # кусок стены 3.2 x 3.2, фасад на y=+0.15 (смотрит в +Y, внутрь шахты)
    p.append(box("wallpiece", (3.2, 0.3, 3.2), (0, 0, 1.6), m["wall"], round_edges=False))
    dw, dh = 1.2, 2.1
    p += door_frame("df", dw, dh, 0.3, m)
    p += blast_door("door", dw, dh, 0.3, m)
    sign = sign_plate("exit_sign", (0.7, 0.03, 0.35), (0, 0.31, 2.65), m["sign_out"])
    p.append(sign)
    p += pipes_along("pipe", 1.4, [2.9], 3.2, 0.2, m, [0.05])
    o = join(p, "bunker_inner_door")
    uv_box(o, 3.0)
    smooth(o)
    hz.selection(o, "bunker_inner_door")
    geo("geometry_wall", (3.2, 0.5, 3.2), (0, 0.1, 1.6))
    save_fn(outdir, "bunker_inner_door")


# ============================================================================ лестничная шахта

def build_stairs(outdir, save_fn, reset_fn):
    """Origin — пол шахты в центре. +Y — в сторону коридора/станции. Верхняя площадка у +Y на высоте 9.6."""
    reset_fn()
    m = mats()
    p = []
    t = WALL_T
    # стены шахты
    # снизу (3 м) — крашеная стена, выше — голый бетон в потёках
    for sx in (-1, 1):
        # кафель на нижних двух этажах (каждые 3 м — своя зелёная полоса), выше к выходу — штукатурка
        p.append(box(f"wall_x{sx}", (t, 2 * SH_Y + 2 * t, 3.0), (sx * (SH_X + t / 2), 0, 1.5), m["wall"], round_edges=False))
        p.append(box(f"wall_x2{sx}", (t, 2 * SH_Y + 2 * t, 3.0), (sx * (SH_X + t / 2), 0, 4.5), m["wall"], round_edges=False))
        p.append(box(f"wall_xc{sx}", (t, 2 * SH_Y + 2 * t, SH_H - 6.0), (sx * (SH_X + t / 2), 0, 6.0 + (SH_H - 6.0) / 2), m["plaster"], round_edges=False))
    p.append(box("wall_back", (2 * SH_X, t, 3.0), (0, -SH_Y - t / 2, 1.5), m["wall"], round_edges=False))
    p.append(box("wall_back2", (2 * SH_X, t, 3.0), (0, -SH_Y - t / 2, 4.5), m["wall"], round_edges=False))
    p.append(box("wall_backc", (2 * SH_X, t, SH_H - 6.0), (0, -SH_Y - t / 2, 6.0 + (SH_H - 6.0) / 2), m["plaster"], round_edges=False))
    front = box("wall_front", (2 * SH_X, t, SH_H), (0, SH_Y + t / 2, SH_H / 2), m["plaster"], round_edges=False)
    cutter = box("cut_front", (1.6, 1.0, 2.4), (0, SH_Y + t / 2, 1.2), m["wall"], round_edges=False)
    p.append(boolean_cut(front, cutter))
    p.append(box("floor", (2 * SH_X + 2 * t, 2 * SH_Y + 2 * t, 0.3), (0, 0, -0.15), m["concrete"], round_edges=False))
    p.append(box("ceiling", (2 * SH_X + 2 * t, 2 * SH_Y + 2 * t, 0.3), (0, 0, SH_H + 0.15), m["plaster"], round_edges=False))

    run = 2 * SH_Y - 2.0                      # 4 м марш между площадками
    steps = 16
    rise = LEVEL / steps
    tread = run / steps
    lane_w = SH_X - 0.1
    # площадки: у +Y — 9.6, 4.8 ; у -Y — 7.2, 2.4
    for z, yy in ((STAIR_TOP, SH_Y - 0.5), (LEVEL * 2, SH_Y - 0.5), (LEVEL * 3, -SH_Y + 0.5), (LEVEL, -SH_Y + 0.5)):
        p.append(box(f"landing{z}", (2 * SH_X, 1.0, 0.2), (0, yy, z - 0.1), m["concrete"]))
        p.append(box(f"landing_edge{z}", (2 * SH_X, 0.05, 0.03), (0, yy - math.copysign(0.48, yy), z + 0.01), m["hazard"]))
    # марши
    for f in range(FLIGHTS):
        z_top = STAIR_TOP - f * LEVEL
        lane_x = -(lane_w / 2 + 0.075) if f % 2 == 0 else (lane_w / 2 + 0.075)
        down_dir = -1 if f % 2 == 0 else 1            # нечётные идут к -Y, чётные к +Y
        y_start = (SH_Y - 1.0) * (-down_dir)          # от площадки
        for i in range(steps):
            top = z_top - (i + 1) * rise
            yc = y_start + down_dir * (i + 0.5) * tread
            p.append(box(f"st{f}_{i}", (lane_w, tread + 0.02, 0.06), (lane_x, yc, top + rise - 0.03), m["concrete"]))
            p.append(box(f"str{f}_{i}", (lane_w, 0.03, rise), (lane_x, yc - down_dir * tread / 2, top + rise / 2), m["concrete"]))
        # наклонная плита под ступенями
        ang = math.atan2(LEVEL, run) * (-down_dir)
        length = math.hypot(run, LEVEL)
        p.append(box(f"slab{f}", (lane_w, length, 0.18), (lane_x, 0, z_top - LEVEL / 2 - 0.12), m["concrete"], (ang, 0, 0), round_edges=False))
        # перила вдоль наружной стены
        rx = lane_x + math.copysign(lane_w / 2 - 0.06, lane_x)
        p.append(cyl(f"rail{f}", 0.022, length, (rx, 0, z_top - LEVEL / 2 + 0.9), m["rust"], (math.radians(90) + ang, 0, 0)))
        for k in (-1, 1):
            yk = k * run / 2 * 0.8
            zk = z_top - LEVEL / 2 - down_dir * yk * LEVEL / run
            p.append(cyl(f"post{f}{k}", 0.016, 0.9, (rx, yk, zk + 0.45), m["rust"]))
    # разделительная стена между маршами
    # разделительная стена между маршами — до уровня верхней площадки (не торчит перед дверью выхода),
    # над ней на верху — перила, чтобы не шагнуть в пролёт
    p.append(box("divider", (0.15, run, STAIR_TOP - LEVEL * 0.5), (0, 0, (STAIR_TOP - LEVEL * 0.5) / 2), m["concrete"], round_edges=False))
    p.append(cyl("top_rail", 0.022, run, (0.08, 0, STAIR_TOP + 1.0), m["rust"], (math.radians(90), 0, 0)))
    p.append(cyl("top_rail_mid", 0.016, run, (0.08, 0, STAIR_TOP + 0.5), m["rust"], (math.radians(90), 0, 0)))
    # стойки опираются на верх разделительной стены (раньше висели в воздухе от 9.6 до 10.6)
    div_top = STAIR_TOP - LEVEL * 0.5
    post_len = STAIR_TOP + 1.0 - div_top + 0.02
    for k in range(4):
        yk = -run / 2 + 0.05 + k * (run - 0.1) / 3
        p.append(cyl(f"top_rail_post{k}", 0.02, post_len, (0.08, yk, div_top + post_len / 2 - 0.02), m["rust"]))
        p.append(box(f"top_rail_foot{k}", (0.15, 0.12, 0.012), (0.04, yk, div_top + 0.006), m["steel"], round_edges=False))
        p.append(hz.bolt(f"top_rail_bolt{k}", (0.04, yk + 0.04, div_top + 0.012), "z", m["steel"], 0.012))
    p.append(cyl("top_rail_low", 0.016, run, (0.08, 0, div_top + 0.55), m["rust"], (math.radians(90), 0, 0)))
    # трубы и кабели в шахте, номера уровней
    p += pipes_along("vpipe", SH_X - 0.1, [SH_H - 0.4], 2 * SH_Y, 0, m, [0.06])
    p.append(cyl("riser", 0.08, SH_H, (SH_X - 0.15, -SH_Y + 0.15, SH_H / 2), m["rust"]))
    p.append(cyl("riser2", 0.05, SH_H, (SH_X - 0.35, -SH_Y + 0.12, SH_H / 2), m["paint"]))
    for k in range(5):
        p.append(box(f"riser_clamp{k}", (0.5, 0.06, 0.05), (SH_X - 0.25, -SH_Y + 0.08, 1.0 + k * 2.4), m["steel"]))
    o = join(p, "bunker_stairs")
    uv_box(o, 3.0)
    smooth(o)
    hz.selection(o, "bunker_stairs")

    # геометрия: стены, полы, пандусы вместо ступеней
    for sx in (-1, 1):
        geo(f"geometry_wall_x{sx}", (0.4, 2 * SH_Y + 0.8, SH_H), (sx * (SH_X + 0.2), 0, SH_H / 2))
    geo("geometry_back", (2 * SH_X, 0.4, SH_H), (0, -SH_Y - 0.2, SH_H / 2))
    geo("geometry_front_top", (2 * SH_X, 0.4, SH_H - 2.4), (0, SH_Y + 0.2, 2.4 + (SH_H - 2.4) / 2))
    for sx in (-1, 1):
        geo(f"geometry_front_side{sx}", (0.8, 0.4, 2.4), (sx * 1.2, SH_Y + 0.2, 1.2))
    geo("geometry_floor", (2 * SH_X, 2 * SH_Y, 0.3), (0, 0, -0.15))
    geo("geometry_divider", (0.15, run, STAIR_TOP - LEVEL * 0.5), (0, 0, (STAIR_TOP - LEVEL * 0.5) / 2))
    geo("geometry_top_rail", (0.12, run, STAIR_TOP + 1.05 - (STAIR_TOP - LEVEL * 0.5)), (0.08, 0, (STAIR_TOP + 1.05 + STAIR_TOP - LEVEL * 0.5) / 2))
    for z, yy in ((STAIR_TOP, SH_Y - 0.5), (LEVEL * 2, SH_Y - 0.5), (LEVEL * 3, -SH_Y + 0.5), (LEVEL, -SH_Y + 0.5)):
        geo(f"geometry_landing{z}", (2 * SH_X, 1.0, 0.2), (0, yy, z - 0.1))
    for f in range(FLIGHTS):
        z_top = STAIR_TOP - f * LEVEL
        lane_x = -(lane_w / 2 + 0.075) if f % 2 == 0 else (lane_w / 2 + 0.075)
        down_dir = -1 if f % 2 == 0 else 1
        ang = math.atan2(LEVEL, run) * (-down_dir)
        geo(f"geometry_ramp{f}", (lane_w, math.hypot(run, LEVEL), 0.15), (lane_x, 0, z_top - LEVEL / 2 - 0.075), (ang, 0, 0))
    save_fn(outdir, "bunker_stairs")


# ============================================================================ коридор

def build_corridor(outdir, save_fn, reset_fn):
    reset_fn()
    m = mats()
    p = []
    L = COR_LEN
    for sx in (-1, 1):
        p.append(box(f"wall{sx}", (WALL_T, L, COR_H), (sx * (COR_W / 2 + WALL_T / 2), 0, COR_H / 2), m["wall"], round_edges=False))
    p.append(box("floor", (COR_W + 2 * WALL_T, L, 0.3), (0, 0, -0.15), m["concrete"], round_edges=False))
    p.append(box("ceiling", (COR_W + 2 * WALL_T, L, 0.3), (0, 0, COR_H + 0.15), m["plaster"], round_edges=False))
    for i in range(5):
        y = -L / 2 + 0.2 + i * (L - 0.4) / 4
        p.append(box(f"beam{i}", (COR_W, 0.2, 0.22), (0, y, COR_H - 0.11), m["concrete"]))
    p += pipes_along("pipes", -COR_W / 2 + 0.15, [2.3, 2.5], L, 0, m, [0.07, 0.05])
    p += cables_along("cab", COR_W / 2 - 0.08, 2.45, L, 0, m, 4)
    # водосток
    p.append(box("drain", (0.2, L, 0.02), (-COR_W / 2 + 0.2, 0, 0.005), m["steel"]))
    o = finish(p, "bunker_corridor")
    for sx in (-1, 1):
        geo(f"geometry_wall{sx}", (0.4, L, COR_H), (sx * (COR_W / 2 + 0.2), 0, COR_H / 2))
    geo("geometry_floor", (COR_W, L, 0.3), (0, 0, -0.15))
    geo("geometry_ceiling", (COR_W, L, 0.3), (0, 0, COR_H + 0.15))
    save_fn(outdir, "bunker_corridor")


# ============================================================================ станция

def build_station(outdir, save_fn, reset_fn):
    reset_fn()
    m = mats()
    p = [box("floor", (ST_W + 2 * WALL_T, ST_LEN, 0.3), (0, 0, -0.15), m["concrete"], round_edges=False)]
    p += vault("st", ST_W, ST_WALL_H, ST_RISE, ST_LEN, 0, m["wall"], m["plaster"])      # кафель + штукатурка свода
    total_h = ST_WALL_H + ST_RISE + WALL_T
    # задний торец с проходом в коридор
    back = box("back", (ST_W + 2 * WALL_T, WALL_T, total_h), (0, -ST_LEN / 2 - WALL_T / 2, total_h / 2), m["wall"], round_edges=False)
    p.append(boolean_cut(back, box("cut_door", (1.6, 1.0, 2.4), (DOOR_X, -ST_LEN / 2 - WALL_T / 2, 1.2), m["wall"], round_edges=False)))
    # передний торец с порталом тоннеля
    front = box("front", (ST_W + 2 * WALL_T, WALL_T, total_h), (0, ST_LEN / 2 + WALL_T / 2, total_h / 2), m["concrete"], round_edges=False)
    p.append(boolean_cut(front, profile_prism("cut_tun", TUN_W, TUN_WALL_H, TUN_RISE, 1.0, ST_LEN / 2 + WALL_T / 2)))
    for sx in (-1, 1):   # жёлто-чёрные полосы по краям портала
        p.append(box(f"portal_hz{sx}", (0.3, 0.04, TUN_WALL_H), (sx * (TUN_W / 2 + 0.15), ST_LEN / 2 - 0.02, TUN_WALL_H / 2), m["hazard"]))
    # тюбинги
    for i in range(12):
        p += rib(f"rib{i}", ST_W, ST_WALL_H, ST_RISE, -ST_LEN / 2 + 1.0 + i * 2.0, m["tubing"])
    # трубы и кабели
    p += pipes_along("lp", -ST_W / 2 + 0.15, [2.3, 2.55, 2.8], ST_LEN, 0, m, [0.09, 0.06, 0.06])
    p += cables_along("rc", ST_W / 2 - 0.08, 2.6, ST_LEN, 0, m, 5)
    # «ВЫХОД» над проходом
    sign = sign_plate("exit_sign", (0.8, 0.03, 0.4), (DOOR_X, -ST_LEN / 2 + 0.02, 2.75), m["sign_out"])
    p.append(sign)
    p += station_details(m)
    o = finish(p, "metro_station")
    geo("geometry_floor", (ST_W + 1, ST_LEN, 0.4), (0, 0, -0.2))
    for sx in (-1, 1):
        geo(f"geometry_wall{sx}", (0.5, ST_LEN, total_h), (sx * (ST_W / 2 + 0.25), 0, total_h / 2))
        geo(f"geometry_front{sx}", ((ST_W - TUN_W) / 2, 0.5, total_h), (sx * (TUN_W / 2 + (ST_W - TUN_W) / 4), ST_LEN / 2 + 0.25, total_h / 2))
    # левая часть заднего торца — строго до проёма (раньше заходила в проход на 25 см)
    geo("geometry_back_l", (ST_W / 2 + DOOR_X - 0.8 + 0.5, 0.5, total_h), ((-ST_W / 2 - 0.5 + DOOR_X - 0.8) / 2, -ST_LEN / 2 - 0.25, total_h / 2))
    geo("geometry_back_r", (ST_W / 2 - DOOR_X - 0.8, 0.5, total_h), ((ST_W / 2 + DOOR_X + 0.8) / 2, -ST_LEN / 2 - 0.25, total_h / 2))
    geo("geometry_roof", (ST_W + 1, ST_LEN, 0.5), (0, 0, total_h))
    # коллизия: платформа, колонны, упор
    px0, px1 = -ST_W / 2, -1.9
    geo("geometry_platform", (px1 - px0, ST_LEN - 0.4, PLATFORM_H), ((px0 + px1) / 2, -0.2, PLATFORM_H / 2))
    for y in (-6.0, 0.0, 6.0):
        geo(f"geometry_col{y}", (0.45, 0.45, vault_z(px1 - 0.825) + 0.1), (px1 - 0.6, y, (vault_z(px1 - 0.825) + 0.1) / 2))
    ey = E_LOCAL_Y - 1.0
    geo("geometry_stop", (2.6, 1.0, 0.9), (0, ey - 0.3, 0.45))
    save_fn(outdir, "metro_station")


# ============================================================================ обстановка станции

PLATFORM_H = 0.3
E_LOCAL_Y = -(ST_LEN / 2 - 4.0)          # где на станции начало пути (точка конца тоннеля), y = -8


def bench(prefix, x, y, m, rot=0.0):
    p = []
    for k in range(3):
        p.append(box(f"{prefix}_slat{k}", (1.6, 0.09, 0.03), (x, y - 0.12 + k * 0.12, PLATFORM_H + 0.45), m["wood"], (0, 0, rot)))
    p.append(box(f"{prefix}_back", (1.6, 0.03, 0.25), (x, y + 0.2, PLATFORM_H + 0.68), m["wood"], (math.radians(-10), 0, rot)))
    for sx in (-0.7, 0.7):
        p.append(box(f"{prefix}_leg{sx}", (0.05, 0.45, 0.45), (x + sx, y, PLATFORM_H + 0.225), m["rust"], (0, 0, rot)))
    return p


def station_details(m):
    p = []
    # --- платформа слева (от стены до 1.9 м от оси пути), кромка с жёлтой полосой
    px0, px1 = -ST_W / 2, -1.9
    pw = px1 - px0
    p.append(box("platform", (pw, ST_LEN - 0.4, PLATFORM_H), ((px0 + px1) / 2, -0.2, PLATFORM_H / 2), m["concrete"]))
    p.append(box("platform_tile", (pw - 0.4, ST_LEN - 0.6, 0.02), ((px0 + px1) / 2 - 0.2, -0.2, PLATFORM_H + 0.01), m["tile"], round_edges=False))
    p.append(box("platform_edge", (0.35, ST_LEN - 0.4, 0.025), (px1 - 0.175, -0.2, PLATFORM_H + 0.012), m["hazard"], round_edges=False))
    # ступень к проходу в коридор
    p.append(box("door_step", (1.6, 0.6, PLATFORM_H / 2), (DOOR_X, -ST_LEN / 2 + 0.3, PLATFORM_H / 4), m["concrete"]))
    # колонны по краю платформы
    for y in (-6.0, 0.0, 6.0):
        # колонна до самого свода (по внутренней кромке, с запасом в бетон), с капителью и базой
        cxp = px1 - 0.6
        ch = vault_z(cxp - 0.225) + 0.1
        p.append(box(f"col{y}", (0.45, 0.45, ch), (cxp, y, ch / 2), m["plaster"]))
        p.append(box(f"col_cap{y}", (0.62, 0.62, 0.18), (cxp, y, vault_z(cxp + 0.31) - 0.12), m["concrete"]))
        p.append(box(f"col_base{y}", (0.55, 0.55, 0.15), (cxp, y, 0.075), m["concrete"]))
    # --- справа: зона выдачи дрезин
    # тупиковый упор за началом пути: шпальная клетка + щит с красно-белой полосой
    ey = E_LOCAL_Y - 1.0
    for k in range(3):
        p.append(box(f"stop_sleeper{k}", (2.6, 0.3, 0.2), (0, ey - 0.15 - k * 0.32, 0.1 + k * 0.2), m["wood"]))
    p.append(box("stop_beam", (2.2, 0.25, 0.3), (0, ey + 0.05, 0.75), m["hazard"]))
    for sx in (-0.8, 0.8):
        p.append(box(f"stop_post{sx}", (0.15, 0.15, 0.9), (sx, ey - 0.1, 0.45), m["rust"]))
    # бетонная площадка под генератор
    gx, gy = 4.5, E_LOCAL_Y - 2.0
    p.append(box("gen_pad", (1.6, 1.2, 0.12), (gx, gy, 0.06), m["concrete"]))
    return p


# ============================================================================ антураж «зоны» (этап 1: станция)

def painted_board(name, w, h, loc, mat, face="-y", lean=0.0):
    """Фанерный щит с надписью. face — куда смотрит лицевая сторона (-y, +y, -x, +x); lean — наклон верха к стене."""
    b = sign_plate(name, (w, 0.018, h), (0, 0, 0), mat)      # читается с +Y (см. uv_front)
    b.rotation_euler = (-lean, 0, math.radians({"+y": 0, "-y": 180, "+x": -90, "-x": 90}[face]))
    bpy.ops.object.select_all(action="DESELECT")
    b.select_set(True)
    bpy.context.view_layer.objects.active = b
    bpy.ops.object.transform_apply(location=False, rotation=True)
    b.location = loc
    return b


def sandbag(name, loc, rot, m):
    k = 1 + (sum(map(ord, name)) % 7 - 3) * 0.03          # мешки чуть разные
    o = sphere(name, 1, loc, m["canvas"], (0.3 * k, 0.19, 0.12 / k), (12, 8), (0, 0, rot))
    return o


def sag_cable(prefix, a, b, sag, m, r=0.014, segs=10):
    """Провисший кабель между точками a и b (цепная линия из отрезков)."""
    parts = []
    pts = []
    for i in range(segs + 1):
        t = i / segs
        p = [a[k] + (b[k] - a[k]) * t for k in range(3)]
        p[2] -= sag * 4 * t * (1 - t)
        pts.append(p)
    for i in range(segs):
        p0, p1 = pts[i], pts[i + 1]
        d = [p1[k] - p0[k] for k in range(3)]
        ln = math.sqrt(sum(c * c for c in d))
        mid = [(p0[k] + p1[k]) / 2 for k in range(3)]
        o = cyl(f"{prefix}_{i}", r, ln + 0.01, mid, m["tape"], (0, 0, 0), 8)
        o.rotation_mode = "QUATERNION"
        import mathutils
        o.rotation_quaternion = mathutils.Vector((0, 0, 1)).rotation_difference(mathutils.Vector(d).normalized())
        parts.append(o)
    return parts


def vault_z(x, w=ST_W, wall_h=ST_WALL_H, rise=ST_RISE):
    return wall_h + rise * math.sqrt(max(0.0, 1 - (x / (w / 2)) ** 2))


def stalker_station(m):
    """Заброшка: лагерь, баррикада у тоннеля, надписи краской, знак радиации, завал, лужи, кабели."""
    p, g = [], []          # g — коллизии (имя, размер, центр)
    P = PLATFORM_H
    # --- лагерь у кострища (-4.3, 7.8): второй матрас, спальник, ящик-стол с бутылками и рацией, рюкзак, тренога с котелком
    cx, cy = -4.3, 7.8
    p.append(box("camp_mattress2", (0.85, 1.85, 0.12), (-2.9, 9.7, P + 0.06), m["canvas"], (0, 0, math.radians(78))))
    p.append(cyl("camp_bedroll", 0.14, 0.75, (-5.4, 10.6, P + 0.14), m["paint"], (0, math.radians(90), 0), 16))
    for sx in (-0.39, 0.39):
        p.append(cyl(f"camp_bedroll_strap{sx}", 0.145, 0.03, (-5.4 + sx * 0.6, 10.6, P + 0.14), m["leather"], (0, math.radians(90), 0), 16))
    p.append(box("camp_table", (0.7, 0.5, 0.45), (-3.1, 7.0, P + 0.225), m["wood"], (0, 0, math.radians(8))))
    for k, (dx, dy, hgt) in enumerate(((-0.2, 0.1, 0.28), (-0.08, -0.05, 0.3), (0.05, 0.12, 0.22))):
        p.append(cyl(f"camp_bottle{k}", 0.035, hgt, (-3.1 + dx, 7.0 + dy, P + 0.45 + hgt / 2), m["paint"], (0, 0, 0), 12))
        p.append(cyl(f"camp_bottle_neck{k}", 0.013, 0.07, (-3.1 + dx, 7.0 + dy, P + 0.45 + hgt + 0.035), m["paint"], (0, 0, 0), 8))
    p.append(box("camp_radio", (0.22, 0.1, 0.14), (-2.95, 6.9, P + 0.52), m["paint2"], (0, 0, math.radians(-12))))
    p.append(cyl("camp_radio_ant", 0.004, 0.35, (-2.88, 6.88, P + 0.76), m["steel"], (math.radians(10), 0, 0), 6))
    p.append(cyl("camp_radio_knob", 0.015, 0.02, (-2.9, 6.84, P + 0.53), m["steel"], ROT_Y, 10))
    p.append(cyl("camp_candle", 0.02, 0.06, (-3.3, 6.9, P + 0.48), m["tile"], (0, 0, 0), 8))
    p.append(box("camp_pack", (0.38, 0.22, 0.5), (-5.5, 9.0, P + 0.24), m["canvas"], (math.radians(-12), 0, math.radians(20))))
    p.append(sphere("camp_pack_top", 0.17, (-5.5, 9.0, P + 0.5), m["canvas"], (1.1, 0.7, 0.5), (12, 8)))
    for k in range(3):
        a = k * 2 * math.pi / 3
        o = cyl(f"camp_tripod{k}", 0.012, 1.0, (cx + math.cos(a) * 0.22, cy + math.sin(a) * 0.22, P + 0.47), m["wood"], (0, 0, 0), 6)
        o.rotation_euler = (math.sin(a) * 0.45, -math.cos(a) * 0.45, 0)
        p.append(o)
    p.append(cyl("camp_pot", 0.12, 0.14, (cx, cy, P + 0.55), m["rust"], (0, 0, 0), 16))
    p.append(cyl("camp_pot_chain", 0.004, 0.22, (cx, cy, P + 0.73), m["steel"], (0, 0, 0), 6))
    g.append(("geometry_camp_table", (0.7, 0.5, 0.45), (-3.1, 7.0, P + 0.225)))
    # --- надписи краской на фанере
    p.append(painted_board("graf_board1", 1.4, 0.7, (ST_W / 2 - 0.12, 8.0, 0.38), m["board1"], face="-x", lean=math.radians(-12)))
    p.append(painted_board("graf_board2", 1.2, 0.6, (-ST_W / 2 + 0.03, 9.4, P + 1.35), m["board2"], face="+x"))
    p.append(painted_board("graf_board3", 1.0, 0.5, (DOOR_X + 1.5, -ST_LEN / 2 + 0.03, 1.4), m["board3"], face="+y"))
    for k, (x, y, z) in enumerate(((-ST_W / 2 + 0.035, 9.0, P + 1.62), (-ST_W / 2 + 0.035, 9.8, P + 1.62))):   # гвозди
        p.append(cyl(f"graf_nail{k}", 0.006, 0.03, (x + 0.01, y, z), m["steel"], ROT_Y, 6))
    # --- знак радиации у портала и рядом с ним, ржавый, на одном гвозде (перекошен)
    rad = sign_plate("rad_sign", (0.8, 0.012, 0.4), (TUN_W / 2 + 0.9, ST_LEN / 2 - 0.03, 2.1), m["sign_rad"])
    rad.rotation_euler = (0, math.radians(7), math.radians(180))     # лицом в зал (-Y), иначе зеркально
    p.append(rad)
    # --- баррикада из мешков у портала: слева и справа от пути, проход для дрезины свободен
    for side in (-1, 1):
        for row in range(3):
            n = 4 - (row == 2)
            for k in range(n):
                x = side * (1.65 + k * 0.52 + (0.26 if row % 2 else 0))
                if abs(x) > TUN_W / 2 - 0.1:
                    continue
                p.append(sandbag(f"bag{side}_{row}_{k}", (x, ST_LEN / 2 - 1.2 + rnd.uniform(-0.03, 0.03), 0.11 + row * 0.21),
                                 rnd.uniform(-0.15, 0.15), m))
        g.append((f"geometry_barricade{side}", (1.4, 0.4, 0.66), (side * 2.3, ST_LEN / 2 - 1.2, 0.33)))
    p.append(box("barricade_plank", (0.15, 0.025, 1.0), (1.6, ST_LEN / 2 - 1.42, 0.45), m["wood"], (math.radians(-15), 0, math.radians(4))))
    # --- бочка-печка у баррикады: прожжённая, с поленьями
    bx_, by_ = 3.6, ST_LEN / 2 - 2.6
    p.append(cyl("burn_barrel", 0.29, 0.86, (bx_, by_, 0.43), m["rust"], (0, 0, 0), 20))
    for z in (0.15, 0.7):
        p.append(torus(f"burn_hoop{z}", 0.295, 0.012, (bx_, by_, z), m["rust"], (0, 0, 0), (24, 6)))
    for k in range(4):
        p.append(cyl(f"burn_log{k}", 0.035, 0.45, (bx_ + rnd.uniform(-0.1, 0.1), by_ + rnd.uniform(-0.1, 0.1), 0.9), m["wood"],
                     (rnd.uniform(-0.6, 0.6), rnd.uniform(-0.6, 0.6), 0), 8))
    p.append(cyl("burn_ash", 0.26, 0.01, (bx_, by_, 0.84), m["tape"]))
    g.append(("geometry_burn_barrel", (0.6, 0.6, 0.86), (bx_, by_, 0.43)))
    # --- завал у правой стены: куски бетона, косо упавшая плита, гнутая арматура
    rx, ry = 5.0, 5.5
    for k in range(14):
        sz = rnd.uniform(0.18, 0.5)
        p.append(box(f"rubble{k}", (sz, sz * rnd.uniform(0.6, 1.1), sz * 0.55),
                     (rx + rnd.uniform(-0.8, 0.7), ry + rnd.uniform(-1.0, 1.0), sz * 0.25 + (0.15 if k > 9 else 0)), m["concrete"],
                     (rnd.uniform(-0.5, 0.5), rnd.uniform(-0.5, 0.5), rnd.uniform(0, 3))))
    p.append(box("rubble_slab", (1.4, 1.0, 0.16), (rx + 0.2, ry + 0.1, 0.55), m["concrete"], (math.radians(8), math.radians(-28), math.radians(12))))
    for k in range(5):
        o = cyl(f"rebar{k}", 0.008, rnd.uniform(0.6, 1.1), (rx + rnd.uniform(-0.3, 0.6), ry + rnd.uniform(-0.6, 0.6), 0.7), m["rust"],
                (rnd.uniform(-0.9, 0.9), rnd.uniform(-0.9, 0.9), 0), 6)
        p.append(o)
    # пятно сколотого свода над завалом
    p.append(box("vault_scar", (0.9, 1.6, 0.05), (ST_W / 2 - 0.55, ry, vault_z(ST_W / 2 - 0.55) - 0.12), m["dirt"],
                 (0, math.radians(-62), 0), round_edges=False))
    g.append(("geometry_rubble", (1.6, 2.0, 0.6), (rx, ry, 0.3)))
    # --- провисшие и оборванные кабели под сводом
    p += sag_cable("sag_a", (3.2, -6.0, vault_z(3.2) - 0.15), (3.4, 2.0, vault_z(3.4) - 0.15), 0.9, m)
    p += sag_cable("sag_b", (-2.0, 1.0, vault_z(-2.0) - 0.12), (-1.6, 9.0, vault_z(-1.6) - 0.12), 0.6, m)
    p += sag_cable("sag_c", (3.6, 2.0, vault_z(3.6) - 0.15), (3.0, 2.3, 2.3), 0.15, m, segs=5)     # оборванный, висит
    p.append(box("sag_c_end", (0.03, 0.03, 0.06), (3.0, 2.3, 2.27), m["steel"]))
    # --- лужи (тёмная вода с бликом) и мусор
    for k, (x, y, sx, sy) in enumerate(((2.6, -2.0, 1.2, 0.6), (3.6, 4.0, 0.8, 1.0), (1.8, 8.5, 0.6, 0.9), (-0.0, -4.5, 0.4, 1.4), (4.3, -6.0, 0.7, 0.5))):
        # лужа неправильной формы: несколько перекрывающихся пятен разного размера
        for j in range(4):
            a = rnd.uniform(0, 6.28)
            off = 0.0 if j == 0 else rnd.uniform(0.25, 0.55)
            sc = 1.0 if j == 0 else rnd.uniform(0.35, 0.6)
            p.append(sphere(f"puddle{k}_{j}", 1, (x + math.cos(a) * off * sx, y + math.sin(a) * off * sy, 0.003 + j * 0.0005), m["puddle"],
                            (sx * sc * rnd.uniform(0.6, 0.9), sy * sc * rnd.uniform(0.6, 0.9), 0.004), (16, 4), (0, 0, rnd.uniform(0, 3))))
    for k in range(12):
        p.append(box(f"paper{k}", (rnd.uniform(0.12, 0.25), rnd.uniform(0.1, 0.2), 0.003),
                     (rnd.uniform(1.5, 5.5), rnd.uniform(-10, 10), 0.003), m["canvas"] if k % 2 else m["tile"], (0, 0, rnd.uniform(0, 3))))
    for k in range(6):
        x, y = rnd.uniform(-5.5, -2.5), rnd.uniform(-8, 10)
        p.append(cyl(f"litter_can{k}", 0.035, 0.11, (x, y, P + 0.035), m["steel"], (math.radians(90), 0, rnd.uniform(0, 3)), 10))
    # --- стопка покрышек у ящиков
    for k in range(3):
        p.append(torus(f"tire{k}", 0.3, 0.1, (5.2, 3.0, 0.1 + k * 0.2), m["tape"], (0, 0, 0), (20, 8)))
    g.append(("geometry_tires", (0.8, 0.8, 0.6), (5.2, 3.0, 0.3)))
    return p, g


# ============================================================================ будка выдачи дрезин

def build_dispenser(outdir, save_fn, reset_fn, tex_dir):
    """Будка выдачи: железный шкаф-будка с окошком, рычаг выдачи, табличка, ящик с инструментом.
    Origin — земля по центру, лицо (+Y) к пути."""
    global TEX_DIR
    TEX_DIR = tex_dir
    reset_fn()
    m = mats()
    p = []
    p.append(box("pad", (1.8, 1.4, 0.1), (0, -0.2, 0.05), m["concrete"]))
    p.append(box("body", (1.2, 0.9, 2.1), (0, -0.4, 1.15), m["paint"]))
    p.append(box("roof", (1.4, 1.1, 0.08), (0, -0.4, 2.24), m["rust"], (math.radians(-6), 0, 0)))
    p.append(box("window", (0.6, 0.02, 0.4), (0, 0.06, 1.5), m["glass"], round_edges=False))
    p.append(box("window_frame", (0.66, 0.03, 0.04), (0, 0.07, 1.72), m["steel"]))
    p.append(box("window_sill", (0.7, 0.12, 0.04), (0, 0.11, 1.28), m["steel"]))
    p.append(sign_plate("sign", (1.1, 0.02, 0.4), (0, 0.06, 1.95), m["sign_depot"]))
    # рычаг выдачи на тумбе
    p.append(box("lever_base", (0.3, 0.3, 0.9), (0.85, 0.15, 0.45), m["paint2"]))
    p.append(box("lever_slot", (0.05, 0.22, 0.02), (0.85, 0.15, 0.91), m["tape"]))
    p.append(cyl("lever_rod", 0.02, 0.6, (0.85, 0.22, 1.2), m["steel"], (math.radians(-25), 0, 0)))
    p.append(sphere("lever_knob", 0.05, (0.85, 0.35, 1.47), m["sign_in"]))
    # мёртвая лампа-клетка и кабель
    p.append(cyl("lamp", 0.07, 0.12, (0, 0.12, 2.12), m["rust"], ROT_Y))
    p.append(cyl("cable", 0.015, 2.1, (-0.55, 0.05, 1.05), m["tape"], (0, 0, 0), 8))
    # ящик с инструментом и ключи на стенке
    p.append(box("toolbox", (0.5, 0.25, 0.25), (-0.85, 0.1, 0.22), m["rust"]))
    for k in range(3):
        p.append(box(f"wrench{k}", (0.03, 0.01, 0.28), (-0.35 + k * 0.08, 0.07, 1.05), m["steel"], (0, math.radians(8 * (k - 1)), 0)))
    o = join(p, "dispenser")
    uv_box(o, 3.0)
    smooth(o)
    hz.selection(o, "dispenser")
    geo("geometry_body", (1.2, 0.9, 2.1), (0, -0.4, 1.15))
    geo("geometry_lever", (0.3, 0.3, 0.9), (0.85, 0.15, 0.45))
    save_fn(outdir, "dispenser")


# ============================================================================ светильник

def build_lamp(outdir, save_fn, reset_fn, tex_dir):
    """Настенный светильник-«бочонок» (как на фото): массивный литой корпус, выпуклый рифлёный плафон,
    толстая решётка — обод и две поперечные дуги + продольная, проводка сверху. Origin — на стене,
    светильник выступает в +Y."""
    global TEX_DIR
    TEX_DIR = tex_dir
    reset_fn()
    m = mats()
    import mathutils
    W, H = 0.16, 0.25                     # полуоси овала (ширина 32 см, высота 50 см)
    p = []
    # литое основание: толстый овальный «таз» у стены
    base = cyl("base", 1, 0.06, (0, 0.03, 0), m["rust"], ROT_Y, 32)
    base.scale = (W + 0.03, H + 0.03, 1)      # локальные оси цилиндра: x, y -> радиусы, z -> толщина
    p.append(base)
    # выпуклый плафон
    glass = sphere("glass", 1, (0, 0.06, 0), m["glass"], (W, 0.11, H), (32, 18))
    hz.selection(glass, "glass")
    p.append(glass)

    def rod(name, a, b, r=0.014):
        d = mathutils.Vector(b) - mathutils.Vector(a)
        o = cyl(name, r, d.length + 0.01, tuple((mathutils.Vector(a) + mathutils.Vector(b)) / 2), m["rust"], (0, 0, 0), 8)
        o.rotation_mode = "QUATERNION"
        o.rotation_quaternion = mathutils.Vector((0, 0, 1)).rotation_difference(d.normalized())
        return o

    def chain(prefix, pts, r=0.014):
        for k in range(len(pts) - 1):
            p.append(rod(f"{prefix}{k}", pts[k], pts[k + 1], r))

    n = 28
    chain("rim", [((W + 0.02) * math.cos(t), 0.075, (H + 0.02) * math.sin(t)) for t in [2 * math.pi * k / n for k in range(n + 1)]], 0.02)
    for k, zz in enumerate((-0.09, 0.09)):
        q = math.sqrt(max(0.0, 1 - (zz / H) ** 2))
        chain(f"band{k}_", [((W + 0.012) * q * math.cos(t), 0.06 + 0.122 * q * math.sin(t), zz) for t in [math.pi * j / 14 for j in range(15)]])
    chain("band_v", [(0, 0.06 + 0.122 * math.sin(t), (H + 0.012) * math.cos(t)) for t in [math.pi * j / 14 for j in range(15)]])
    # болты на ободе, проводка и сальник сверху
    for k in range(6):
        t = 2 * math.pi * k / 6 + 0.3
        p.append(hz.bolt(f"bolt{k}", ((W + 0.02) * math.cos(t), 0.09, (H + 0.02) * math.sin(t)), "y", m["steel"], 0.012))
    p.append(cyl("gland", 0.03, 0.06, (0, 0.04, H + 0.06), m["rust"], (0, 0, 0), 12))
    p.append(cyl("conduit", 0.016, 0.6, (0, 0.03, H + 0.38), m["steel"], (0, 0, 0), 10))
    o = join(p, "tunnel_lamp")
    uv_box(o, 0.4)
    smooth(o)
    hz.selection(o, "tunnel_lamp")
    save_fn(outdir, "tunnel_lamp")


# ============================================================================ тоннель

# ============================================================================ антураж тоннеля (этап 2)
# Колея свободна: всё, что выше пола, стоит при |x| > 1.15 (дрезина ~1.6 м шириной). На пути — только плоское.

def tun_vault_z(x):
    return vault_z(x, TUN_W, TUN_WALL_H, TUN_RISE)


def mine_cart(prefix, x, y, rot, m, tilt=0.0):
    """Ржавая опрокидная вагонетка, сошедшая с рельсов."""
    p = []
    import mathutils
    M = mathutils.Matrix.Translation((x, y, 0)) @ mathutils.Matrix.Rotation(rot, 4, "Z") @ mathutils.Matrix.Rotation(tilt, 4, "Y")
    def put(o):
        o.matrix_world = M @ o.matrix_world
        p.append(o)
    put(box(f"{prefix}_bottom", (0.8, 1.3, 0.04), (0, 0, 0.45), m["rust"]))
    for sx in (-1, 1):
        put(box(f"{prefix}_side{sx}", (0.04, 1.3, 0.55), (sx * 0.5, 0, 0.72), m["rust"], (0, sx * math.radians(-14), 0)))
    for sy in (-1, 1):
        put(box(f"{prefix}_end{sy}", (1.0, 0.04, 0.55), (0, sy * 0.65, 0.72), m["rust"]))
    put(box(f"{prefix}_rim_l", (0.06, 1.34, 0.06), (-0.57, 0, 1.0), m["rust"]))
    put(box(f"{prefix}_rim_r", (0.06, 1.34, 0.06), (0.57, 0, 1.0), m["rust"]))
    put(box(f"{prefix}_frame", (0.6, 1.5, 0.1), (0, 0, 0.36), m["steel"]))
    for sx in (-0.38, 0.38):
        for sy in (-0.45, 0.45):
            put(cyl(f"{prefix}_wheel{sx}{sy}", 0.16, 0.06, (sx, sy, 0.16), m["rust"], ROT_Y, 16))
    for sy in (-0.45, 0.45):
        put(cyl(f"{prefix}_axle{sy}", 0.025, 0.82, (0, sy, 0.16), m["steel"], ROT_Y, 8))
    put(box(f"{prefix}_coupler", (0.08, 0.25, 0.06), (0, 0.85, 0.36), m["steel"]))
    # внутри — мусор и куски бетона
    for k in range(4):
        put(box(f"{prefix}_junk{k}", (0.25, 0.2, 0.15), (-0.2 + k * 0.13, -0.3 + k * 0.2, 0.55), m["concrete"], (k, k * 0.7, k * 1.3)))
    return p


def broken_lamp(prefix, x, y, m, hang=0.6):
    """Разбитый светильник: висит на проводе, без стекла, патрон и решётка погнуты."""
    p = []
    zt = tun_vault_z(x) - 0.05
    p.append(box(f"{prefix}_mount", (0.18, 0.18, 0.04), (x, y, zt), m["rust"]))
    p.append(cyl(f"{prefix}_wire", 0.006, hang, (x + 0.05, y, zt - hang / 2), m["tape"], (0, math.radians(6), 0), 6))
    zl = zt - hang
    p.append(cyl(f"{prefix}_housing", 0.09, 0.08, (x + 0.1, y, zl), m["paint"], (math.radians(25), 0, 0), 14))
    for k in range(3):
        a = k * 2.1
        p.append(box(f"{prefix}_cage{k}", (0.008, 0.008, 0.16), (x + 0.1 + math.cos(a) * 0.08, y + math.sin(a) * 0.08, zl - 0.1), m["steel"],
                     (0.4 * math.sin(a), 0.5 * math.cos(a), 0)))
    for k in range(5):     # осколки стекла на полу
        p.append(box(f"{prefix}_shard{k}", (0.05, 0.04, 0.004), (x + rnd.uniform(-0.4, 0.4), y + rnd.uniform(-0.4, 0.4), 0.003), m["glass"],
                     (0, 0, rnd.uniform(0, 3))))
    return p


def puddle_blob(prefix, x, y, sx, sy, m):
    p = []
    for j in range(4):
        a = rnd.uniform(0, 6.28)
        off = 0.0 if j == 0 else rnd.uniform(0.25, 0.55)
        sc = 1.0 if j == 0 else rnd.uniform(0.35, 0.6)
        p.append(sphere(f"{prefix}_{j}", 1, (x + math.cos(a) * off * sx, y + math.sin(a) * off * sy, 0.003 + j * 0.0005), m["puddle"],
                        (sx * sc * rnd.uniform(0.6, 0.9), sy * sc * rnd.uniform(0.6, 0.9), 0.004), (16, 4), (0, 0, rnd.uniform(0, 3))))
    return p


def tunnel_props(variant, m, walk_h):
    """Наполнение звена 10 м по варианту: a — базовое, b/c/d — с «событиями». Возвращает (детали, коллизии)."""
    global rnd
    rnd = random.Random(100 + ord(variant))
    p, g = [], []
    # общее для всех: бумаги, банки, пара мелких луж
    for k in range(5):
        p.append(box(f"paper{k}", (rnd.uniform(0.1, 0.2), rnd.uniform(0.08, 0.16), 0.003), (rnd.uniform(1.3, 2.5), rnd.uniform(-4.5, 4.5), 0.003),
                     m["canvas"] if k % 2 else m["tile"], (0, 0, rnd.uniform(0, 3))))
    p += puddle_blob("pud_a", rnd.uniform(-0.5, 0.5), rnd.uniform(-3, 3), 0.5, 1.1, m)
    if variant == "a":
        p += debris("deb", (2.2, rnd.uniform(-3, 3)), 4, 0.5, m)
        p.append(cyl("can", 0.035, 0.11, (-2.6, 1.0, walk_h + 0.035), m["steel"], (math.radians(90), 0, 0.7), 10))
    elif variant == "b":
        # обвал тюбинга: кусок свода упал справа, куча бетона, торчит арматура; разбитая лампа, провисший кабель
        p.append(box("fallen_segment", (0.25, 1.4, 1.1), (2.35, 1.2, 0.5), m["tubing"], (math.radians(10), math.radians(-24), math.radians(8))))
        for k in range(12):
            sz = rnd.uniform(0.15, 0.45)
            p.append(box(f"rubble{k}", (sz, sz * rnd.uniform(0.6, 1.1), sz * 0.55),
                         (rnd.uniform(1.5, 2.8), 1.2 + rnd.uniform(-1.2, 1.2), sz * 0.25), m["concrete"],
                         (rnd.uniform(-0.5, 0.5), rnd.uniform(-0.5, 0.5), rnd.uniform(0, 3))))
        for k in range(4):
            p.append(cyl(f"rebar{k}", 0.008, rnd.uniform(0.6, 1.0), (2.3 + rnd.uniform(-0.3, 0.3), 1.2 + rnd.uniform(-0.5, 0.5), 0.6), m["rust"],
                         (rnd.uniform(-0.9, 0.9), rnd.uniform(-0.9, 0.9), 0), 6))
        p.append(box("scar", (0.8, 1.4, 0.05), (2.55, 1.2, tun_vault_z(2.55) - 0.1), m["dirt"], (0, math.radians(-55), 0), round_edges=False))
        g.append(("geometry_rubble", (1.5, 2.6, 0.7), (2.25, 1.2, 0.35)))
        p += broken_lamp("blamp", -0.4, -2.5, m, 0.7)
        p += sag_cable("sag", (2.5, -4.8, tun_vault_z(2.5) - 0.1), (2.2, -0.6, tun_vault_z(2.2) - 0.1), 0.8, m)
        p += puddle_blob("pud_b", 1.8, -3.2, 0.8, 0.7, m)
    elif variant == "c":
        # брошенная вагонетка сбоку от пути, раскатившиеся бочки, сложенные шпалы, надпись
        p += mine_cart("cart", 1.95, -1.5, math.radians(4), m, math.radians(-6))
        g.append(("geometry_cart", (1.1, 1.7, 1.05), (1.95, -1.5, 0.52)))
        p.append(cyl("barrel_lying", 0.3, 0.88, (2.2, 2.4, 0.3), m["paint2"], (math.radians(90), 0, math.radians(70)), 18))
        p.append(cyl("barrel_up", 0.3, 0.88, (2.55, 3.4, 0.44), m["rust"], (0, 0, 0), 18))
        g.append(("geometry_barrels", (1.2, 1.8, 0.88), (2.35, 2.9, 0.44)))
        for k in range(4):
            p.append(box(f"sleeper{k}", (0.24, 2.4, 0.15), (-2.62 + (k % 2) * 0.05, -2.8, walk_h + 0.075 + k * 0.15), m["wood"],
                         (0, 0, math.radians(rnd.uniform(-4, 4)))))
        g.append(("geometry_sleepers", (0.5, 2.5, 0.6), (-2.6, -2.8, walk_h + 0.3)))
        p.append(painted_board("board4", 1.1, 0.55, (TUN_W / 2 - 0.03, 0.8, 1.55), m["board4"], face="-x"))
        p += puddle_blob("pud_c", -0.2, 3.0, 0.6, 1.3, m)
    elif variant == "d":
        # протечка: вода по своду, большая лужа через путь; заначка сталкера на проходе; указатель к станции
        p += puddle_blob("pud_d1", 0.3, 0.5, 1.6, 1.8, m)
        p += puddle_blob("pud_d2", -1.4, 2.0, 0.7, 0.9, m)
        for k in range(6):          # подтёки на своде и стене
            x = rnd.uniform(-1.5, 1.5)
            p.append(box(f"leak{k}", (0.12, 0.25, 0.01), (x, 0.5 + rnd.uniform(-1, 1), tun_vault_z(x) - 0.02), m["dirt"], round_edges=False))
        p.append(box("stash_crate", (0.6, 0.45, 0.4), (-2.62, 1.6, walk_h + 0.2), m["wood"], (0, 0, math.radians(6))))
        p.append(cyl("stash_bedroll", 0.13, 0.7, (-2.62, 0.7, walk_h + 0.13), m["paint"], (math.radians(90), 0, 0), 14))
        p.append(box("stash_tarp", (0.7, 0.6, 0.02), (-2.62, 2.4, walk_h + 0.01), m["canvas"], (0, 0, math.radians(-10))))
        p.append(cyl("stash_canteen", 0.06, 0.18, (-2.45, 1.95, walk_h + 0.09), m["paint2"], (0, 0, 0), 12))
        p.append(sphere("stash_helmet", 0.13, (-2.75, 1.6, walk_h + 0.45), m["paint"], (1, 1.1, 0.7), (12, 6)))
        g.append(("geometry_stash", (0.65, 0.5, 0.42), (-2.62, 1.6, walk_h + 0.21)))
        p.append(painted_board("board5", 1.0, 0.5, (-TUN_W / 2 + 0.03, -2.0, walk_h + 1.6), m["board5"], face="+x"))
        p += broken_lamp("blamp", 0.6, 3.6, m, 0.4)
    elif variant == "e":
        # служебная ниша: металлическая дверь в стене (закрыта), щитки, телефон, табличка ТП-4
        dx = -TUN_W / 2 + 0.06
        p.append(box("door_frame", (0.12, 1.2, 2.2), (dx, 1.0, walk_h + 1.1), m["steel"]))
        p.append(box("door_leaf", (0.06, 1.0, 2.0), (dx + 0.05, 1.0, walk_h + 1.0), m["door"]))
        p.append(cyl("door_handle", 0.015, 0.14, (dx + 0.1, 1.38, walk_h + 1.0), m["steel"], ROT_X, 8))
        for zh in (0.3, 1.7):
            p.append(cyl(f"door_hinge{zh}", 0.02, 0.12, (dx + 0.08, 0.52, walk_h + zh), m["rust"]))
        p.append(painted_board("tp_sign", 0.5, 0.25, (dx + 0.09, 1.0, walk_h + 2.35), m["sign_tp"], face="+x"))
        for k, yy in enumerate((-1.2, -2.0)):
            p.append(box(f"cab{k}", (0.25, 0.6, 0.8), (-TUN_W / 2 + 0.13, yy, walk_h + 1.3), m["paint"]))
            p.append(box(f"cab_door{k}", (0.02, 0.56, 0.76), (-TUN_W / 2 + 0.26, yy, walk_h + 1.3), m["paint2"]))
            p.append(box(f"cab_lock{k}", (0.02, 0.04, 0.08), (-TUN_W / 2 + 0.28, yy + 0.22, walk_h + 1.3), m["steel"]))
        p.append(box("phone_box", (0.15, 0.25, 0.35), (-TUN_W / 2 + 0.08, -3.4, walk_h + 1.4), m["hazard"]))
        p.append(torus("phone_cord", 0.05, 0.006, (-TUN_W / 2 + 0.17, -3.4, walk_h + 1.15), m["tape"], ROT_Y, (12, 6)))
        p += puddle_blob("pud_e", 1.7, -2.5, 0.7, 0.6, m)
    elif variant == "f":
        # брошенный блокпост: мешки у стены и на проходе, шлагбаум, ящики с патронами, бочка, щит «Стой! Пропуск»
        for row in range(3):
            for k in range(3 - (row == 2)):
                p.append(sandbag(f"bp_bag{row}{k}", (1.6 + k * 0.52 + (0.26 if row % 2 else 0), 2.6, 0.11 + row * 0.21), rnd.uniform(-0.15, 0.15), m))
        g.append(("geometry_bp_bags", (1.6, 0.45, 0.66), (2.25, 2.6, 0.33)))
        for k in range(2):
            p.append(sandbag(f"bp_wbag{k}", (-2.62, 2.2 + k * 0.6, walk_h + 0.11), 1.57, m))
        p.append(box("barrier_post", (0.12, 0.12, 1.0), (1.3, 1.6, 0.5), m["hazard"]))
        p.append(box("barrier_arm", (1.6, 0.08, 0.08), (2.1, 1.6, 0.95), m["hazard"]))     # поднят вдоль стены, путь свободен
        for k, (x, y) in enumerate(((2.4, -1.0), (2.4, -1.55), (2.35, -1.25))):
            z = 0.15 if k < 2 else 0.45
            p.append(box(f"ammo{k}", (0.55, 0.3, 0.3), (x, y, z), m["paint"] if k != 1 else m["wood"], (0, 0, math.radians(rnd.uniform(-8, 8)))))
        g.append(("geometry_ammo", (0.65, 0.9, 0.6), (2.4, -1.25, 0.3)))
        p.append(cyl("bp_barrel", 0.29, 0.86, (2.5, 0.6, 0.43), m["rust"], (0, 0, 0), 18))
        p.append(cyl("bp_barrel_ash", 0.26, 0.01, (2.5, 0.6, 0.84), m["tape"]))
        g.append(("geometry_bp_barrel", (0.6, 0.6, 0.86), (2.5, 0.6, 0.43)))
        p.append(painted_board("board10", 1.0, 0.5, (TUN_W / 2 - 0.03, 2.0, 1.45), m["board10"], face="-x"))
        p.append(cyl("bp_bedroll", 0.13, 0.7, (-2.62, -1.2, walk_h + 0.13), m["paint"], (math.radians(90), 0, 0), 14))
    elif variant == "g":
        # аварийная крепь: деревянные стойки и прогоны под треснувшим сводом, капёж, лужи, предупреждение
        for k, yy in enumerate((-2.5, 0.0, 2.5)):
            for sx in (-1, 1):
                x = sx * (TUN_W / 2 - 0.35)
                h = tun_vault_z(x) - 0.25
                p.append(box(f"prop{k}{sx}", (0.2, 0.2, h), (x, yy, h / 2), m["wood"]))
            p.append(box(f"cap{k}", (TUN_W - 0.5, 0.22, 0.22), (0, yy, tun_vault_z(TUN_W / 2 - 0.35) - 0.14), m["wood"]))
            p.append(box(f"wedge{k}", (0.3, 0.2, 0.08), (0, yy, tun_vault_z(0) - 0.05), m["wood"]))
        for k in range(3):
            p.append(box(f"lagging{k}", (0.25, 5.4, 0.04), (-1.0 + k * 1.0, 0, tun_vault_z(-1.0 + k * 1.0) - 0.04), m["wood"], (0, math.radians(-14 + k * 14), 0)))
        g.append(("geometry_props_l", (0.25, 5.3, 2.5), (-(TUN_W / 2 - 0.35), 0, 1.25)))
        g.append(("geometry_props_r", (0.25, 5.3, 2.5), (TUN_W / 2 - 0.35, 0, 1.25)))
        p.append(box("crack_scar", (1.6, 1.8, 0.05), (0.4, 1.2, tun_vault_z(0.4) - 0.03), m["dirt"], round_edges=False))
        p += puddle_blob("pud_g1", 0.2, 1.0, 1.3, 1.1, m)
        p += puddle_blob("pud_g2", -1.4, -2.2, 0.6, 0.7, m)
        for k in range(5):
            p.append(box(f"plank{k}", (0.2, 1.4, 0.03), (rnd.uniform(1.4, 2.6), rnd.uniform(-4, 4), 0.02 + k * 0.03), m["wood"], (0, 0, rnd.uniform(-0.4, 0.4))))
        p.append(painted_board("board11", 1.0, 0.5, (-TUN_W / 2 + 0.03, 3.6, walk_h + 1.6), m["board11"], face="+x"))
    return p, g


def build_tunnel(outdir, save_fn, reset_fn, L=10.0, name="tunnel_10m", variant="a"):
    reset_fn()
    m = mats()
    short = L < 5
    floor_len = 2.02 if short else L
    wall_len = 2.2 if short else L
    p = [box("floor", (TUN_W + 2 * WALL_T, floor_len, 0.3), (0, 0, -0.15), m["concrete"], round_edges=False)]
    # у станций (первые 10 м) — кафель, дальше — кирпичная кладка; свод — штукатурка
    wall_mat = m["wall"]                 # весь тоннель — в кафеле, как станция
    p += vault("t", TUN_W, TUN_WALL_H, TUN_RISE, wall_len, 0, wall_mat, m["plaster"])
    ribs = [0.0] if short else [-3.75, -1.25, 1.25, 3.75]
    for i, y in enumerate(ribs):
        p += rib(f"rib{i}", TUN_W, TUN_WALL_H, TUN_RISE, y, m["tubing"], depth=0.2)
    pipe_len = 2.0 if short else L
    p += pipes_along("lp", -TUN_W / 2 + 0.12, [1.5, 1.75], pipe_len, 0, m, [0.08, 0.05], brackets=2.5 if not short else 2.0)
    p += cables_along("rc", TUN_W / 2 - 0.07, 1.9, pipe_len, 0, m, 4)
    # служебный проход вдоль левой стены: бетонный бортик с жёлто-чёрной кромкой и поручнем на стене
    walk_w, walk_h = 0.75, 0.35
    wx = -TUN_W / 2 + walk_w / 2
    p.append(box("walkway", (walk_w, floor_len, walk_h), (wx, 0, walk_h / 2), m["concrete"], round_edges=False))
    p.append(box("walkway_edge", (0.12, floor_len, 0.02), (wx + walk_w / 2 - 0.06, 0, walk_h + 0.01), m["hazard"], round_edges=False))
    p.append(cyl("wall_handrail", 0.022, pipe_len, (-TUN_W / 2 + 0.08, 0, walk_h + 0.95), m["rust"], (math.radians(90), 0, 0)))
    # водоотводной лоток вдоль правой стены
    p.append(box("drain", (0.25, floor_len, 0.03), (TUN_W / 2 - 0.3, 0, 0.015), m["steel"], round_edges=False))
    for y in ((0.0,) if short else (-4.0, 0.0, 4.0)):      # кронштейны поручня (и на коротких кусках)
        p.append(box(f"handrail_bracket{y}", (0.1, 0.03, 0.03), (-TUN_W / 2 + 0.04, y, walk_h + 0.95), m["rust"]))
    amb_geo = []
    if not short:
        # кабельный лоток вдоль правой стены (над кабелями на крюках) и распределительная коробка
        tz = 2.15
        p.append(box("tray", (0.3, floor_len, 0.012), (TUN_W / 2 - 0.25, 0, tz), m["steel"], round_edges=False))
        for sx in (-1, 1):
            p.append(box(f"tray_lip{sx}", (0.012, floor_len, 0.06), (TUN_W / 2 - 0.25 + sx * 0.15, 0, tz + 0.03), m["steel"], round_edges=False))
        for k in range(4):
            p.append(cyl(f"tray_cable{k}", 0.02, floor_len, (TUN_W / 2 - 0.35 + k * 0.06, 0, tz + 0.03), m["tape"], ROT_Y, 8))
        for yy in (-3.75, -1.25, 1.25, 3.75):
            p.append(box(f"tray_bracket{yy}", (0.34, 0.04, 0.04), (TUN_W / 2 - 0.2, yy + 0.15, tz - 0.03), m["rust"]))
        pass
    finish(p, name)
    for gname, gsize, gloc in amb_geo:
        geo(gname, gsize, gloc)
    geo("geometry_walkway", (walk_w, floor_len, walk_h), (wx, 0, walk_h / 2))
    geo("geometry_floor", (TUN_W + 1, floor_len, 0.4), (0, 0, -0.2))
    for sx in (-1, 1):
        geo(f"geometry_wall{sx}", (0.5, wall_len, TUN_WALL_H + TUN_RISE), (sx * (TUN_W / 2 + 0.25), 0, (TUN_WALL_H + TUN_RISE) / 2))
    geo("geometry_roof", (TUN_W + 1, wall_len, 0.5), (0, 0, TUN_WALL_H + TUN_RISE + 0.25))
    save_fn(outdir, name)


# ============================================================================ зал развязки (пересечение линий)

JUNC_R = 24.0
JUNC_H = 6.5


def build_junction_hall(outdir, save_fn, reset_fn):
    """Круглый зал R=24 м: пол, плоский свод на радиальных балках и двух кольцевых, ступица в центре.
    Стены — отдельные панели (junction_wall) и порталы тоннелей (junction_portal): их ставит скрипт по кругу."""
    reset_fn()
    m = mats()
    p = []
    p.append(cyl("floor", JUNC_R + 0.6, 0.3, (0, 0, -0.15), m["concrete"], (0, 0, 0), 64))
    p.append(cyl("ceiling", JUNC_R + 0.6, 0.4, (0, 0, JUNC_H + 0.2), m["plaster"], (0, 0, 0), 64))
    for k in range(16):
        a = k * math.pi / 8
        L = JUNC_R - 1.0
        p.append(box(f"beam{k}", (0.4, L, 0.5), (math.sin(a) * L / 2, math.cos(a) * L / 2, JUNC_H - 0.25), m["concrete"], (0, 0, -a)))
    for r, w in ((12.0, 0.5), (JUNC_R - 0.6, 0.6)):
        n = 48
        for k in range(n):
            a0 = k * 2 * math.pi / n
            a1 = (k + 1) * 2 * math.pi / n
            mx, my = (math.sin(a0) + math.sin(a1)) / 2 * r, (math.cos(a0) + math.cos(a1)) / 2 * r
            ln = 2 * r * math.sin(math.pi / n) + 0.05
            p.append(box(f"ringbeam{r}_{k}", (ln, w, 0.55), (mx, my, JUNC_H - 0.28), m["tubing"], (0, 0, -(a0 + a1) / 2 + math.pi / 2)))
    p.append(cyl("hub", 1.2, 0.6, (0, 0, JUNC_H - 0.3), m["tubing"], (0, 0, 0), 32))
    # на полу: водоотводное кольцо у стен
    n = 64
    for k in range(n):
        a0 = k * 2 * math.pi / n
        a1 = (k + 1) * 2 * math.pi / n
        r = JUNC_R - 0.4
        mx, my = (math.sin(a0) + math.sin(a1)) / 2 * r, (math.cos(a0) + math.cos(a1)) / 2 * r
        ln = 2 * r * math.sin(math.pi / n) + 0.02
        p.append(box(f"drain{k}", (ln, 0.3, 0.02), (mx, my, 0.01), m["steel"], (0, 0, -(a0 + a1) / 2 + math.pi / 2), round_edges=False))
    finish(p, "junction_hall")
    geo("geometry_floor", (2 * JUNC_R + 1, 2 * JUNC_R + 1, 0.4), (0, 0, -0.2))
    geo("geometry_ceiling", (2 * JUNC_R + 1, 2 * JUNC_R + 1, 0.5), (0, 0, JUNC_H + 0.25))
    save_fn(outdir, "junction_hall")


JUNC_TEE_CUT = 6.5     # зал Т-развязки: пустая половина срезана прямой стеной в 6.5 м от оси главной линии


def build_junction_hall_tee(outdir, save_fn, reset_fn):
    """Зал Т-развязки: тот же круг R=24, но со стороны, где нет примыкающей линии, срезан прямой стеной
    в JUNC_TEE_CUT м от оси главной линии (ось — вдоль +Y, примыкающая линия — со стороны +X).
    Прямую стену из панелей ставит скрипт, как и круглые."""
    reset_fn()
    m = mats()
    C = JUNC_TEE_CUT
    p = []
    for name, z, h, mat in (("floor", -0.15, 0.3, m["concrete"]), ("ceiling", JUNC_H + 0.2, 0.4, m["plaster"])):
        o = cyl(name, JUNC_R + 0.6, h, (0, 0, z), mat, (0, 0, 0), 64)
        cutter = box(name + "_cut", (JUNC_R * 2, JUNC_R * 3, h + 1.0), (-C - 0.6 - JUNC_R, 0, z), mat, round_edges=False)
        p.append(boolean_cut(o, cutter))
    for k in range(16):
        a = k * math.pi / 8
        L = JUNC_R - 1.0
        sa = math.sin(a)
        if sa < -0.01:
            L = min(L, (C - 0.4) / -sa)
        p.append(box(f"beam{k}", (0.4, L, 0.5), (math.sin(a) * L / 2, math.cos(a) * L / 2, JUNC_H - 0.25), m["concrete"], (0, 0, -a)))
    for r, w in ((12.0, 0.5), (JUNC_R - 0.6, 0.6)):
        n = 48
        for k in range(n):
            a0 = k * 2 * math.pi / n
            a1 = (k + 1) * 2 * math.pi / n
            mx, my = (math.sin(a0) + math.sin(a1)) / 2 * r, (math.cos(a0) + math.cos(a1)) / 2 * r
            if mx < -C + 0.5:
                continue
            ln = 2 * r * math.sin(math.pi / n) + 0.05
            p.append(box(f"ringbeam{r}_{k}", (ln, w, 0.55), (mx, my, JUNC_H - 0.28), m["tubing"], (0, 0, -(a0 + a1) / 2 + math.pi / 2)))
    chord = math.sqrt(JUNC_R ** 2 - C ** 2)
    p.append(box("cut_beam", (0.6, 2 * chord, 0.55), (-C + 0.3, 0, JUNC_H - 0.28), m["tubing"]))
    p.append(cyl("hub", 1.2, 0.6, (0, 0, JUNC_H - 0.3), m["tubing"], (0, 0, 0), 32))
    n = 64
    for k in range(n):
        a0 = k * 2 * math.pi / n
        a1 = (k + 1) * 2 * math.pi / n
        r = JUNC_R - 0.4
        mx, my = (math.sin(a0) + math.sin(a1)) / 2 * r, (math.cos(a0) + math.cos(a1)) / 2 * r
        if mx < -C + 0.4:
            continue
        ln = 2 * r * math.sin(math.pi / n) + 0.02
        p.append(box(f"drain{k}", (ln, 0.3, 0.02), (mx, my, 0.01), m["steel"], (0, 0, -(a0 + a1) / 2 + math.pi / 2), round_edges=False))
    p.append(box("cut_drain", (0.3, 2 * chord, 0.02), (-C + 0.4, 0, 0.01), m["steel"], round_edges=False))
    finish(p, "junction_hall_tee")
    geo("geometry_floor", (JUNC_R + C + 1, 2 * JUNC_R + 1, 0.4), ((JUNC_R - C) / 2, 0, -0.2))
    geo("geometry_ceiling", (JUNC_R + C + 1, 2 * JUNC_R + 1, 0.5), ((JUNC_R - C) / 2, 0, JUNC_H + 0.25))
    save_fn(outdir, "junction_hall_tee")


def build_junction_slab(outdir, save_fn, reset_fn):
    """Плита зала развязки 3x3 м: пол и потолок с балкой — из них скрипт выкладывает пол зала только
    там, где внутри стен есть пути (без лишнего пола и потолка за стенами)."""
    reset_fn()
    m = mats()
    S = 3.0
    p = [box("floor", (S + 0.02, S + 0.02, 0.3), (0, 0, -0.15), m["concrete"], round_edges=False)]
    p.append(box("ceiling", (S + 0.02, S + 0.02, 0.4), (0, 0, JUNC_H + 0.2), m["plaster"], round_edges=False))
    p.append(box("beam", (0.4, S + 0.02, 0.45), (0, 0, JUNC_H - 0.22), m["concrete"], round_edges=False))
    p.append(box("beam_x", (S + 0.02, 0.3, 0.3), (0, 0, JUNC_H - 0.15), m["tubing"], round_edges=False))
    finish(p, "junction_slab")
    geo("geometry_floor", (S, S, 0.4), (0, 0, -0.2))
    geo("geometry_ceiling", (S, S, 0.5), (0, 0, JUNC_H + 0.25))
    save_fn(outdir, "junction_slab")


def build_junction_column(outdir, save_fn, reset_fn):
    """Колонна зала развязки под свод: бетонный ствол 0.8x0.8 с фаской, база, капитель-раструб под
    балки, плитка снизу и полосы «зебры» на уровне колен (чтобы видно было из дрезины)."""
    reset_fn()
    m = mats()
    H = JUNC_H
    p = [box("shaft", (0.8, 0.8, H), (0, 0, H / 2), m["concrete"])]
    p.append(box("base", (1.1, 1.1, 0.3), (0, 0, 0.15), m["concrete"]))
    p.append(box("base_step", (0.95, 0.95, 0.12), (0, 0, 0.36), m["concrete"]))
    p.append(box("wall_tiles", (0.84, 0.84, 1.6), (0, 0, 0.42 + 0.8), m["wall"], round_edges=False))
    for k, z in enumerate((0.55, 0.85)):
        p.append(box(f"hazard{k}", (0.86, 0.86, 0.12), (0, 0, z), m["hazard"], round_edges=False))
    p.append(box("capital", (1.3, 1.3, 0.35), (0, 0, H - 0.5 - 0.175), m["concrete"]))
    p.append(box("capital_top", (1.6, 1.6, 0.25), (0, 0, H - 0.5 + 0.125), m["tubing"]))
    for k in range(4):
        a = k * math.pi / 2
        p.append(box(f"brace{k}", (0.25, 0.9, 0.25), (math.sin(a) * 0.65, math.cos(a) * 0.65, H - 0.95), m["tubing"],
                     (math.radians(35), 0, -a)))
    finish(p, "junction_column")
    geo("geometry_column", (0.9, 0.9, H), (0, 0, H / 2))
    save_fn(outdir, "junction_column")


def build_junction_wall(outdir, save_fn, reset_fn):
    """Стеновая панель зала: 2.75 м, лицом в +Y (внутрь зала), с кабелями и трубой вдоль стены."""
    reset_fn()
    m = mats()
    p = [box("panel", (2.75, 0.5, JUNC_H + 0.5), (0, 0, (JUNC_H + 0.5) / 2), m["wall"], round_edges=False)]
    p.append(box("plinth", (2.75, 0.06, 0.3), (0, 0.27, 0.15), m["concrete"], round_edges=False))
    # (труб и кабелей на панели нет: на круглой стене их прямые концы торчали из соседних панелей)
    finish(p, "junction_wall")
    geo("geometry_panel", (2.75, 0.5, JUNC_H + 0.5), (0, 0, (JUNC_H + 0.5) / 2))
    save_fn(outdir, "junction_wall")


def build_junction_portal(outdir, save_fn, reset_fn):
    """Портал тоннеля в стене зала: стена 12 м с вырезом по профилю тоннеля, жёлто-чёрные полосы."""
    reset_fn()
    m = mats()
    w, h = 12.0, JUNC_H + 0.5          # шире выреза: крайние панели стены заходят за портал — без щелей
    wall = box("portal_wall", (w, 0.5, h), (0, 0, h / 2), m["concrete"], round_edges=False)
    p = [boolean_cut(wall, profile_prism("cut_tun", TUN_W, TUN_WALL_H, TUN_RISE, 1.0, 0))]
    for sx in (-1, 1):
        p.append(box(f"portal_hz{sx}", (0.3, 0.04, TUN_WALL_H), (sx * (TUN_W / 2 + 0.15), 0.27, TUN_WALL_H / 2), m["hazard"]))
    p.append(box("portal_lintel", (TUN_W + 0.6, 0.1, 0.3), (0, 0.3, TUN_WALL_H + TUN_RISE + 0.3), m["tubing"]))
    finish(p, "junction_portal")
    for sx in (-1, 1):
        geo(f"geometry_side{sx}", ((w - TUN_W) / 2, 0.5, h), (sx * (TUN_W / 2 + (w - TUN_W) / 4), 0, h / 2))
    geo("geometry_top", (TUN_W, 0.5, h - (TUN_WALL_H + TUN_RISE)), (0, 0, (h + TUN_WALL_H + TUN_RISE) / 2))
    save_fn(outdir, "junction_portal")


def build_alarm(outdir, save_fn, reset_fn, tex_dir):
    """Аварийный маячок на стене: кронштейн, корпус-цилиндр, красный светящийся плафон, решётка.
    Origin — на стене, маячок выступает в +Y."""
    global TEX_DIR
    TEX_DIR = tex_dir
    reset_fn()
    m = mats()
    red = hz.tex_material("drezina_redglass_e", "drezina_redglass", 0.2)
    red["dayz_rvmat"] = "Drezina\\data\\textures\\drezina_redglass_e.rvmat"
    p = []
    # монтажная пластина с болтами и кронштейн-уголок
    p.append(box("plate", (0.2, 0.025, 0.24), (0, 0.0125, 0), m["paint"]))
    for sx in (-1, 1):
        for sz in (-1, 1):
            p.append(cyl(f"plate_bolt{sx}{sz}", 0.011, 0.02, (sx * 0.075, 0.03, sz * 0.095), m["steel"], ROT_X, 6))
    p.append(box("arm", (0.07, 0.13, 0.025), (0, 0.085, -0.075), m["paint"]))
    p.append(box("arm_rib", (0.012, 0.11, 0.06), (0, 0.075, -0.05), m["paint"], (math.radians(-28), 0, 0)))
    # корпус с мотором: ступенчатый цилиндр, стык, кабельный ввод
    y0 = 0.17
    p.append(cyl("base", 0.09, 0.05, (0, y0, -0.06), m["paint"], (0, 0, 0), 28))
    p.append(cyl("base_ring", 0.094, 0.012, (0, y0, -0.032), m["steel"], (0, 0, 0), 28))
    p.append(cyl("base_top", 0.08, 0.02, (0, y0, -0.018), m["paint"], (0, 0, 0), 28))
    p.append(cyl("gland", 0.016, 0.04, (0, y0 - 0.085, -0.06), m["steel"], ROT_X, 10))
    # красный плафон: рифлёный цилиндр (вертикальные рёбра-линзы) и купол
    p.append(cyl("dome", 0.068, 0.12, (0, y0, 0.05), red, (0, 0, 0), 32))
    for k in range(12):
        a = k * math.pi / 6
        p.append(box(f"dome_rib{k}", (0.012, 0.01, 0.11), (math.cos(a) * 0.069, y0 + math.sin(a) * 0.069, 0.05), red, (0, 0, -a)))
    p.append(sphere("dome_top", 0.068, (0, y0, 0.11), red, (1, 1, 0.55), (28, 12)))
    p.append(cyl("cap", 0.02, 0.015, (0, y0, 0.15), m["steel"], (0, 0, 0), 12))
    # защитная решётка: шесть прутков, два кольца, крышка-пятак
    for k in range(6):
        a = k * math.pi / 3 + 0.26
        p.append(box(f"cage{k}", (0.008, 0.008, 0.17), (math.cos(a) * 0.082, y0 + math.sin(a) * 0.082, 0.065), m["steel"]))
    for z in (0.02, 0.11):
        p.append(torus(f"cage_ring{z}", 0.082, 0.005, (0, y0, z), m["steel"], (0, 0, 0), (28, 6)))
    for k in range(3):
        a = k * math.pi / 3 + 0.26
        p.append(box(f"cage_top{k}", (0.17, 0.008, 0.008), (0, y0, 0.15), m["steel"], (0, 0, a)))
    # кабель в гофре вверх по стене
    p.append(cyl("conduit", 0.011, 0.45, (0.05, 0.02, 0.34), m["steel"], (0, 0, 0), 8))
    p.append(box("conduit_clip", (0.04, 0.02, 0.015), (0.05, 0.02, 0.3), m["rust"]))
    o = join(p, "alarm_lamp")
    # крупнее исходного (на большой стене маленький плафон было не разглядеть), но поменьше прежнего
    o.scale = (1.25, 1.25, 1.25)
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    uv_box(o, 0.4)
    smooth(o)
    hz.selection(o, "alarm_lamp")
    save_fn(outdir, "alarm_lamp")


def build_all(outdir, tex_dir, save_fn, reset_fn):
    global TEX_DIR
    TEX_DIR = tex_dir
    build_entrance(outdir, save_fn, reset_fn)
    build_inner_door(outdir, save_fn, reset_fn)
    build_stairs(outdir, save_fn, reset_fn)
    build_corridor(outdir, save_fn, reset_fn)
    build_station(outdir, save_fn, reset_fn)
    build_tunnel(outdir, save_fn, reset_fn)
    build_tunnel(outdir, save_fn, reset_fn, 10.0, "tunnel_10m_tile", "tile")   # у станций, в кафеле
    build_tunnel(outdir, save_fn, reset_fn, 2.4, "tunnel_2m")
    build_junction_hall(outdir, save_fn, reset_fn)
    build_junction_hall_tee(outdir, save_fn, reset_fn)
    build_junction_column(outdir, save_fn, reset_fn)
    build_junction_slab(outdir, save_fn, reset_fn)
    build_junction_wall(outdir, save_fn, reset_fn)
    build_junction_portal(outdir, save_fn, reset_fn)
    build_dispenser(outdir, save_fn, reset_fn, tex_dir)
    build_lamp(outdir, save_fn, reset_fn, tex_dir)
    build_alarm(outdir, save_fn, reset_fn, tex_dir)
