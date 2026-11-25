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


def build_entrance(outdir, save_fn, reset_fn):
    """Origin — земля перед фасадом по центру двери. Фасад смотрит в +Y."""
    reset_fn()
    m = mats()
    p = []
    BW, BD, BH = 4.6, 4.0, 3.2
    # бетонная коробка, почти полностью в насыпи
    p.append(box("block", (BW, BD, BH + 3.0), (0, -BD / 2, (BH - 3.0) / 2), m["concrete"]))      # фундамент на 3 м в землю
    # портал: толстая рамка вокруг ниши
    # (внутренние края портала вплотную к коробке двери: 1.6/2 + 0.18 = 0.98)
    p.append(box("portal_l", (0.9, 0.6, 3.5), (-1.43, 0.2, 1.75), m["concrete"]))
    p.append(box("portal_r", (0.9, 0.6, 3.5), (1.43, 0.2, 1.75), m["concrete"]))
    p.append(box("portal_top", (1.96, 0.6, 0.92), (0, 0.2, 3.04), m["concrete"]))   # строго между боковинами
    p.append(box("visor", (4.4, 1.1, 0.22), (0, 0.55, 3.55), m["concrete"], (math.radians(-5), 0, 0)))
    p.append(box("niche_floor", (2.2, 1.0, 0.1), (0, 0.0, 0.05), m["concrete"]))
    # бетонная отмостка перед входом, уходит в землю (на склоне не видно щели под порогом)
    p.append(box("apron", (4.2, 2.6, 2.0), (0, 1.3, -0.97), m["concrete"]))
    for sx in (-1, 1):
        p.append(box(f"portal_foot{sx}", (0.9, 0.6, 2.0), (sx * 1.43, 0.2, -1.0), m["concrete"]))
    # откосные стенки, держат насыпь
    for sx in (-1, 1):
        p.append(box(f"wing{sx}", (0.4, 3.2, 3.4), (sx * 2.3, 1.4, 1.0), m["concrete"], (math.radians(-32), 0, 0)))
        p.append(box(f"wing_foot{sx}", (0.4, 3.0, 2.2), (sx * 2.3, 1.1, -0.9), m["concrete"]))
        p.append(box(f"wing_cap{sx}", (0.5, 3.4, 0.15), (sx * 2.3, 1.4, 2.45), m["concrete"], (math.radians(-32), 0, 0)))
    # дверь (крупнее, как у армейских бункеров) в жёлто-чёрной коробке
    dw, dh = 1.6, 2.4
    # дверь в нише портала: перед фасадом блока (y=0), на 0.25 м глубже лица портала (y=0.5)
    p += door_frame("df", dw, dh, 0.25, m)
    p += blast_door("door", dw, dh, 0.25, m)
    p += control_panel("panel", (1.43, 0.5, 1.35), m)
    # табличка на левой части портала
    sign = sign_plate("sign", (0.8, 0.03, 0.4), (-1.43, 0.515, 1.9), m["sign_in"])
    p.append(sign)
    # мёртвый светильник-клетка над дверью
    p.append(cyl("lamp_dead", 0.09, 0.15, (0, 0.55, 2.95), m["rust"], ROT_Y))
    for k in range(4):
        p.append(box(f"lamp_cage{k}", (0.012, 0.16, 0.012), (math.cos(k * 1.57) * 0.08, 0.62, 2.95 + math.sin(k * 1.57) * 0.08), m["steel"]))
    # вентиляционный грибок над насыпью, кабель, мешки
    p.append(cyl("vent", 0.15, 2.2, (1.6, -3.2, 3.6), m["rust"]))
    p.append(hz.cone("vent_cap", 0.34, 0.05, 0.26, (1.6, -3.2, 4.8), m["rust"], (0, 0, 0), 24))
    for i, x in enumerate((-1.75, -1.35)):
        p.append(sphere(f"bag{i}", 1, (x, 1.1, 0.1), m["canvas"], (0.25, 0.16, 0.1), (16, 10)))
    concrete = join(p, "bunker_entrance")
    uv_box(concrete, 3.0)
    # срез насыпи — за фасадом блока (y = -0.35): заглушка не закрывает дверь, по бокам её прячут откосы
    mound = earth_mound("mound", (0, -2.9, 0), (6.0, 6.2, 4.4), -0.35, m["dirt"], bottom=-3.0)
    uv_box(mound, 4.0)
    o = join([concrete, mound], "bunker_entrance")
    smooth(o, 40)
    hz.selection(o, "bunker_entrance")
    # геометрия
    # коллизия блока заканчивается на фасаде (y = 0), портал и дверь — отдельными боксами, ниша свободна
    geo("geometry_block", (BW, BD, 6.6), (0, -BD / 2, 0.3))
    geo("geometry_apron", (4.2, 2.6, 2.0), (0, 1.3, -0.97))
    for sx in (-1, 1):
        geo(f"geometry_portal{sx}", (0.9, 0.6, 3.5), (sx * 1.43, 0.2, 1.75))
    geo("geometry_portal_top", (1.96, 0.6, 0.92), (0, 0.2, 3.04))
    geo("geometry_door", (1.96, 0.3, 2.58), (0, 0.1, 1.29))     # закрытая дверь: к ней можно подойти вплотную
    for sx in (-1, 1):
        geo(f"geometry_wing{sx}", (0.4, 3.2, 3.4), (sx * 2.3, 1.4, 1.0), (math.radians(-32), 0, 0))
    geo("geometry_mound", (11, 8, 6.5), (0, -4.5, 0.25))
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
        p.append(box(f"wall_x{sx}", (t, 2 * SH_Y + 2 * t, 3.0), (sx * (SH_X + t / 2), 0, 1.5), m["wall"], round_edges=False))
        p.append(box(f"wall_xc{sx}", (t, 2 * SH_Y + 2 * t, SH_H - 3.0), (sx * (SH_X + t / 2), 0, 3.0 + (SH_H - 3.0) / 2), m["concrete"], round_edges=False))
    p.append(box("wall_back", (2 * SH_X, t, 3.0), (0, -SH_Y - t / 2, 1.5), m["wall"], round_edges=False))
    p.append(box("wall_backc", (2 * SH_X, t, SH_H - 3.0), (0, -SH_Y - t / 2, 3.0 + (SH_H - 3.0) / 2), m["concrete"], round_edges=False))
    front = box("wall_front", (2 * SH_X, t, SH_H), (0, SH_Y + t / 2, SH_H / 2), m["concrete"], round_edges=False)
    cutter = box("cut_front", (1.6, 1.0, 2.4), (0, SH_Y + t / 2, 1.2), m["wall"], round_edges=False)
    p.append(boolean_cut(front, cutter))
    p.append(box("floor", (2 * SH_X + 2 * t, 2 * SH_Y + 2 * t, 0.3), (0, 0, -0.15), m["concrete"], round_edges=False))
    p.append(box("ceiling", (2 * SH_X + 2 * t, 2 * SH_Y + 2 * t, 0.3), (0, 0, SH_H + 0.15), m["concrete"], round_edges=False))

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
    p += debris("deb", (-0.8, 2.0), 5, 0.5, m)

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
    p.append(box("ceiling", (COR_W + 2 * WALL_T, L, 0.3), (0, 0, COR_H + 0.15), m["concrete"], round_edges=False))
    for i in range(5):
        y = -L / 2 + 0.2 + i * (L - 0.4) / 4
        p.append(box(f"beam{i}", (COR_W, 0.2, 0.22), (0, y, COR_H - 0.11), m["concrete"]))
    p += pipes_along("pipes", -COR_W / 2 + 0.15, [2.3, 2.5], L, 0, m, [0.07, 0.05])
    p += cables_along("cab", COR_W / 2 - 0.08, 2.45, L, 0, m, 4)
    # электрощиток с распахнутой дверцей
    p.append(box("panel", (0.1, 0.5, 0.7), (COR_W / 2 - 0.05, 1.5, 1.5), m["paint"]))
    p.append(box("panel_door", (0.5, 0.02, 0.7), (COR_W / 2 - 0.35, 1.78, 1.5), m["paint"], (0, 0, math.radians(30))))
    # водосток
    p.append(box("drain", (0.2, L, 0.02), (-COR_W / 2 + 0.2, 0, 0.005), m["steel"]))
    p += debris("deb", (0.6, -2.5), 4, 0.4, m)
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
    p += vault("st", ST_W, ST_WALL_H, ST_RISE, ST_LEN, 0, m["wall"], m["concrete"])
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
    # мусор, ящики, бочка
    p += debris("deb_a", (4.5, -8.0), 8, 0.9, m)
    p += debris("deb_b", (-5.0, 6.0), 6, 0.7, m)
    for i, (x, y) in enumerate(((4.9, 0.6), (4.9, 1.5), (4.7, 1.05))):   # не на площадке генератора
        p.append(box(f"crate{i}", (0.7, 0.6, 0.5), (x, y, 0.25 + (0.5 if i == 2 else 0)), m["wood"], (0, 0, math.radians(rnd.uniform(-10, 10)))))
    p.append(cyl("barrel", 0.3, 0.9, (-5.2, -6.5, 0.45), m["rust"]))
    for z in (0.15, 0.75):
        p.append(torus(f"barrel_hoop{z}", 0.305, 0.012, (-5.2, -6.5, z), m["rust"], (0, 0, 0), (32, 6)))
    p += station_details(m)
    amb, amb_geo = stalker_station(m)
    p += amb
    o = finish(p, "metro_station")
    for gname, gsize, gloc in amb_geo:
        geo(gname, gsize, gloc)
    geo("geometry_floor", (ST_W + 1, ST_LEN, 0.4), (0, 0, -0.2))
    for sx in (-1, 1):
        geo(f"geometry_wall{sx}", (0.5, ST_LEN, total_h), (sx * (ST_W / 2 + 0.25), 0, total_h / 2))
        geo(f"geometry_front{sx}", ((ST_W - TUN_W) / 2, 0.5, total_h), (sx * (TUN_W / 2 + (ST_W - TUN_W) / 4), ST_LEN / 2 + 0.25, total_h / 2))
    # левая часть заднего торца — строго до проёма (раньше заходила в проход на 25 см)
    geo("geometry_back_l", (ST_W / 2 + DOOR_X - 0.8 + 0.5, 0.5, total_h), ((-ST_W / 2 - 0.5 + DOOR_X - 0.8) / 2, -ST_LEN / 2 - 0.25, total_h / 2))
    geo("geometry_back_r", (ST_W / 2 - DOOR_X - 0.8, 0.5, total_h), ((ST_W / 2 + DOOR_X + 0.8) / 2, -ST_LEN / 2 - 0.25, total_h / 2))
    geo("geometry_roof", (ST_W + 1, ST_LEN, 0.5), (0, 0, total_h))
    # коллизия обстановки: по платформе ходят, в колонны, будку, лавки и ящики упираются
    px0, px1 = -ST_W / 2, -1.9
    geo("geometry_platform", (px1 - px0, ST_LEN - 0.4, PLATFORM_H), ((px0 + px1) / 2, -0.2, PLATFORM_H / 2))
    for y in (-6.0, 0.0, 6.0):
        geo(f"geometry_col{y}", (0.45, 0.45, ST_WALL_H + 0.6), (px1 - 0.6, y, (ST_WALL_H + 0.6) / 2))
    bx, by = -4.6, -9.6
    geo("geometry_booth_back", (2.4, 0.1, 2.4), (bx, by - 0.9, PLATFORM_H + 1.2))
    d0, d1 = by - 0.75, by + 0.05
    geo("geometry_booth_side_a", (0.1, d0 - (by - 0.9), 2.4), (bx + 1.2, (by - 0.9 + d0) / 2, PLATFORM_H + 1.2))
    geo("geometry_booth_side_b", (0.1, by + 0.9 - d1, 2.4), (bx + 1.2, (d1 + by + 0.9) / 2, PLATFORM_H + 1.2))
    geo("geometry_booth_lintel", (0.1, d1 - d0, 0.4), (bx + 1.2, (d0 + d1) / 2, PLATFORM_H + 2.2))
    geo("geometry_booth_locker", (0.5, 0.45, 1.8), (bx - 0.85, by - 0.62, PLATFORM_H + 0.9))
    geo("geometry_booth_drawers", (0.4, 0.45, 0.85), (bx + 0.55, by + 0.55, PLATFORM_H + 0.425))
    geo("geometry_booth_front", (2.4, 0.1, 1.0), (bx, by + 0.9, PLATFORM_H + 0.5))
    geo("geometry_booth_roof", (2.6, 2.0, 0.1), (bx, by, PLATFORM_H + 2.44))
    for yb in (-3.0, 3.0):
        geo(f"geometry_bench{yb}", (1.6, 0.5, 0.5), (-4.8, yb, PLATFORM_H + 0.25))
    geo("geometry_crates", (0.9, 1.6, 1.0), (4.85, 1.05, 0.5))
    geo("geometry_barrel", (0.6, 0.6, 0.9), (-5.2, -6.5, 0.45))
    ey = E_LOCAL_Y - 1.0
    geo("geometry_stop", (2.6, 1.0, 0.9), (0, ey - 0.3, 0.45))
    gy = E_LOCAL_Y - 2.0
    geo("geometry_shelf", (0.5, 1.6, 1.6), (ST_W / 2 - 0.3, gy + 2.5, 0.8))
    geo("geometry_oil", (0.6, 1.3, 0.9), (ST_W / 2 - 0.5, gy + 5.7, 0.45))
    geo("geometry_mattress", (0.9, 1.9, 0.14), (-5.3, 9.2, PLATFORM_H + 0.07))
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
        p.append(box(f"col{y}", (0.45, 0.45, ST_WALL_H + 0.6), (px1 - 0.6, y, (ST_WALL_H + 0.6) / 2), m["wall"]))
    # скамейки
    p += bench("bench_a", -4.8, -3.0, m)
    p += bench("bench_b", -4.8, 3.0, m)
    # будка дежурного: стенки, разбитое окно, крыша, дверь
    bx, by = -4.6, -9.6
    p.append(box("booth_w1", (2.4, 0.08, 2.4), (bx, by - 0.9, PLATFORM_H + 1.2), m["paint"]))
    # боковая стенка с дверным проёмом 0.8 x 2.0 (раньше была глухой — в будку было не попасть)
    d0, d1 = by - 0.75, by + 0.05
    p.append(box("booth_w2a", (0.08, d0 - (by - 0.9), 2.4), (bx + 1.2, (by - 0.9 + d0) / 2, PLATFORM_H + 1.2), m["paint"]))
    p.append(box("booth_w2b", (0.08, by + 0.9 - d1, 2.4), (bx + 1.2, (d1 + by + 0.9) / 2, PLATFORM_H + 1.2), m["paint"]))
    p.append(box("booth_lintel", (0.08, d1 - d0, 0.4), (bx + 1.2, (d0 + d1) / 2, PLATFORM_H + 2.2), m["paint"]))
    for yy in (d0, d1):
        p.append(box(f"booth_jamb{yy:.2f}", (0.1, 0.05, 2.0), (bx + 1.2, yy, PLATFORM_H + 1.0), m["steel"]))
    # дверь приоткрыта наружу на петлях у d0
    a = math.radians(75)
    p.append(box("booth_door", (0.04, 0.78, 1.98), (bx + 1.2 + 0.39 * math.sin(a), d0 + 0.39 * math.cos(a), PLATFORM_H + 1.0), m["paint"], (0, 0, -a)))
    p.append(cyl("booth_door_handle", 0.012, 0.12, (bx + 1.2 + 0.72 * math.sin(a) + 0.04 * math.cos(a), d0 + 0.72 * math.cos(a) - 0.04 * math.sin(a), PLATFORM_H + 1.0), m["steel"], ROT_X))
    for zh in (0.3, 1.7):
        p.append(cyl(f"booth_hinge{zh}", 0.018, 0.12, (bx + 1.2, d0, PLATFORM_H + zh), m["rust"]))
    # обстановка внутри: стул, шкафчик, тумба, бумаги, лампа, урна, календарь, полка
    p.append(box("booth_chair_seat", (0.42, 0.42, 0.04), (bx - 0.1, by + 0.05, PLATFORM_H + 0.45), m["wood"], (0, 0, math.radians(12))))
    for cx_, cy_ in ((-0.18, -0.18), (0.18, -0.18), (-0.18, 0.18), (0.18, 0.18)):
        p.append(cyl(f"booth_chair_leg{cx_}{cy_}", 0.014, 0.45, (bx - 0.1 + cx_, by + 0.05 + cy_, PLATFORM_H + 0.225), m["steel"]))
    p.append(box("booth_chair_back", (0.42, 0.03, 0.4), (bx - 0.1 + 0.04, by + 0.05 - 0.2, PLATFORM_H + 0.78), m["wood"], (math.radians(-8), 0, math.radians(12))))
    p.append(box("booth_locker", (0.5, 0.42, 1.8), (bx - 0.85, by - 0.62, PLATFORM_H + 0.9), m["paint2"]))
    p.append(box("booth_locker_door", (0.46, 0.02, 1.7), (bx - 0.85, by - 0.4, PLATFORM_H + 0.9), m["paint2"]))
    for k in range(3):
        p.append(box(f"booth_locker_vent{k}", (0.3, 0.025, 0.015), (bx - 0.85, by - 0.39, PLATFORM_H + 1.55 + k * 0.05), m["tape"]))
    p.append(box("booth_drawers", (0.4, 0.45, 0.85), (bx + 0.55, by + 0.55, PLATFORM_H + 0.425), m["paint"]))
    for k in range(3):
        p.append(box(f"booth_drawer_handle{k}", (0.12, 0.02, 0.02), (bx + 0.55, by + 0.32, PLATFORM_H + 0.2 + k * 0.27), m["steel"]))
    p.append(box("booth_desk_leg", (0.05, 0.45, 0.88), (bx - 0.75, by + 0.55, PLATFORM_H + 0.44), m["steel"]))
    p.append(box("booth_papers", (0.3, 0.22, 0.01), (bx - 0.3, by + 0.5, PLATFORM_H + 0.93), m["canvas"], (0, 0, math.radians(15))))
    p.append(box("booth_papers2", (0.25, 0.32, 0.006), (bx - 0.05, by + 0.6, PLATFORM_H + 0.93), m["tile"], (0, 0, math.radians(-25))))
    p.append(box("booth_logbook", (0.22, 0.3, 0.04), (bx + 0.1, by + 0.48, PLATFORM_H + 0.945), m["leather"] if "leather" in m else m["wood"], (0, 0, math.radians(5))))
    p.append(cyl("booth_lamp_base", 0.07, 0.03, (bx - 0.65, by + 0.6, PLATFORM_H + 0.94), m["paint"]))
    p.append(cyl("booth_lamp_arm", 0.01, 0.35, (bx - 0.65, by + 0.6, PLATFORM_H + 1.12), m["steel"], (math.radians(-15), 0, 0)))
    p.append(cyl("booth_lamp_shade", 0.08, 0.12, (bx - 0.65, by + 0.5, PLATFORM_H + 1.28), m["paint"], (math.radians(-60), 0, 0)))
    p.append(cyl("booth_mug", 0.04, 0.09, (bx + 0.35, by + 0.42, PLATFORM_H + 0.97), m["steel"]))
    p.append(cyl("booth_bin", 0.15, 0.35, (bx + 0.85, by - 0.6, PLATFORM_H + 0.175), m["rust"]))
    p.append(box("booth_calendar", (0.3, 0.01, 0.42), (bx - 0.2, by - 0.85, PLATFORM_H + 1.5), m["tile"]))
    p.append(box("booth_shelf", (1.0, 0.25, 0.03), (bx + 0.2, by - 0.75, PLATFORM_H + 1.85), m["wood"]))
    for k in range(4):
        p.append(box(f"booth_binder{k}", (0.06, 0.22, 0.3), (bx - 0.15 + k * 0.08, by - 0.75, PLATFORM_H + 2.02), m["paint2"] if k % 2 else m["paint"], (0, math.radians(6 if k == 3 else 0), 0)))
    for k, (dx, dy) in enumerate(((0.2, -0.2), (0.45, 0.1), (-0.4, -0.3))):
        p.append(box(f"booth_scrap{k}", (0.2, 0.15, 0.004), (bx + dx, by + dy, PLATFORM_H + 0.004), m["canvas"], (0, 0, k * 0.9)))
    p.append(box("booth_front_low", (2.4, 0.08, 1.0), (bx, by + 0.9, PLATFORM_H + 0.5), m["paint"]))
    p.append(box("booth_front_top", (2.4, 0.08, 0.3), (bx, by + 0.9, PLATFORM_H + 2.25), m["paint"]))
    for k in (-0.6, 0.6):
        p.append(box(f"booth_mullion{k}", (0.05, 0.06, 1.1), (bx + k, by + 0.9, PLATFORM_H + 1.55), m["steel"]))
    p.append(box("booth_glass_shard", (0.4, 0.01, 0.35), (bx - 0.85, by + 0.9, PLATFORM_H + 1.25), m["glass"], (0, 0, math.radians(8))))
    p.append(box("booth_roof", (2.6, 2.0, 0.08), (bx, by, PLATFORM_H + 2.44), m["rust"]))
    p.append(box("booth_desk", (1.6, 0.5, 0.05), (bx, by + 0.55, PLATFORM_H + 0.9), m["wood"]))
    p.append(box("booth_phone", (0.18, 0.14, 0.1), (bx + 0.4, by + 0.55, PLATFORM_H + 0.97), m["tape"]))
    # название станции, часы, табло
    p.append(sign_plate("station_sign", (2.6, 0.03, 0.65), (-ST_W / 2 + 0.2, 0.0, 2.3), m["sign_station"]))
    # повернуть табличку лицом в зал (+X): строим её как плоскость вдоль Y
    p[-1].rotation_euler = (0, 0, math.radians(-90))
    p[-1].location = (-ST_W / 2 + 0.03, 0, 2.3)
    bpy.context.view_layer.objects.active = p[-1]
    bpy.ops.object.select_all(action="DESELECT")
    p[-1].select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True)
    p.append(cyl("clock", 0.3, 0.06, (-ST_W / 2 + 0.06, 6.0, 2.6), m["paint"], ROT_X))
    p.append(cyl("clock_face", 0.26, 0.065, (-ST_W / 2 + 0.065, 6.0, 2.6), m["tile"], ROT_X))
    p.append(box("clock_hand1", (0.01, 0.015, 0.2), (-ST_W / 2 + 0.1, 6.0, 2.66), m["tape"], (math.radians(35), 0, 0)))
    p.append(box("clock_hand2", (0.01, 0.015, 0.14), (-ST_W / 2 + 0.1, 6.04, 2.58), m["tape"], (math.radians(110), 0, 0)))
    # пожарный шкаф и телефон на стене
    p.append(box("fire_cab", (0.25, 0.7, 0.9), (-ST_W / 2 + 0.12, -6.5, PLATFORM_H + 1.3), m["hazard"]))
    p.append(cyl("fire_hose", 0.2, 0.08, (-ST_W / 2 + 0.28, -6.5, PLATFORM_H + 1.3), m["paint"], ROT_X))
    p.append(box("wall_phone", (0.15, 0.25, 0.35), (-ST_W / 2 + 0.08, 8.5, PLATFORM_H + 1.4), m["paint"]))
    p.append(torus("wall_phone_cord", 0.05, 0.006, (-ST_W / 2 + 0.17, 8.5, PLATFORM_H + 1.15), m["tape"], ROT_Y, (12, 6)))
    # стоянка сталкеров: кострище из камней, матрас, банки
    cx, cy = -4.3, 7.8
    for k in range(9):
        a = k * 2 * math.pi / 9
        p.append(box(f"fire_stone{k}", (0.16, 0.13, 0.1), (cx + math.cos(a) * 0.38, cy + math.sin(a) * 0.38, PLATFORM_H + 0.05), m["concrete"], (0, 0, a)))
    p.append(cyl("ashes", 0.3, 0.02, (cx, cy, PLATFORM_H + 0.01), m["tape"]))
    for k in range(3):
        p.append(cyl(f"log{k}", 0.04, 0.5, (cx, cy, PLATFORM_H + 0.05), m["wood"], (math.radians(90), 0, k * 1.05), 10))
    p.append(box("mattress", (0.9, 1.9, 0.14), (-5.3, 9.2, PLATFORM_H + 0.07), m["canvas"]))
    for k in range(3):
        p.append(cyl(f"can{k}", 0.035, 0.11, (cx + 0.7 + k * 0.1, cy - 0.5 + k * 0.07, PLATFORM_H + 0.055), m["steel"]))
    # --- справа: зона выдачи дрезин
    # тупиковый упор за началом пути: шпальная клетка + щит с красно-белой полосой
    ey = E_LOCAL_Y - 1.0
    for k in range(3):
        p.append(box(f"stop_sleeper{k}", (2.6, 0.3, 0.2), (0, ey - 0.15 - k * 0.32, 0.1 + k * 0.2), m["wood"]))
    p.append(box("stop_beam", (2.2, 0.25, 0.3), (0, ey + 0.05, 0.75), m["hazard"]))
    for sx in (-0.8, 0.8):
        p.append(box(f"stop_post{sx}", (0.15, 0.15, 0.9), (sx, ey - 0.1, 0.45), m["rust"]))
    # бетонная площадка под генератор, распределительный щит и кабель к нему
    gx, gy = 4.5, E_LOCAL_Y - 2.0
    p.append(box("gen_pad", (1.6, 1.2, 0.12), (gx, gy, 0.06), m["concrete"]))
    p.append(box("gen_panel", (0.15, 0.7, 1.0), (ST_W / 2 - 0.1, gy, 1.5), m["paint"]))
    p.append(box("gen_panel_door", (0.03, 0.6, 0.9), (ST_W / 2 - 0.19, gy, 1.5), m["paint"]))
    p.append(box("gen_switch", (0.08, 0.06, 0.18), (ST_W / 2 - 0.22, gy + 0.18, 1.6), m["steel"], (0, math.radians(20), 0)))
    p.append(cyl("gen_cable", 0.02, ST_W / 2 - gx - 0.5, (gx + (ST_W / 2 - gx) / 2, gy + 0.3, 0.03), m["tape"], (0, math.radians(90), 0), 8))
    p.append(cyl("gen_cable_up", 0.02, 1.0, (ST_W / 2 - 0.12, gy + 0.3, 0.5), m["tape"], (0, 0, 0), 8))
    p.append(sign_plate("gen_sign", (0.5, 0.02, 0.18), (ST_W / 2 - 0.2, gy, 2.15), m["sign_in"]))
    # стеллаж с запчастями и запасное колесо у стены
    for k in range(3):
        p.append(box(f"shelf{k}", (0.5, 1.6, 0.04), (ST_W / 2 - 0.3, gy + 2.5, 0.4 + k * 0.6), m["rust"]))
    for sy in (-0.75, 0.75):
        p.append(box(f"shelf_post{sy}", (0.04, 0.04, 1.6), (ST_W / 2 - 0.3, gy + 2.5 + sy, 0.8), m["rust"]))
    p.append(torus("spare_wheel", 0.33, 0.04, (ST_W / 2 - 0.25, gy + 4.4, 0.4), m["steel"], ROT_X, (24, 8)))
    for k in range(2):
        p.append(cyl(f"oil_barrel{k}", 0.3, 0.9, (ST_W / 2 - 0.5, gy + 5.4 + k * 0.65, 0.45), m["paint2"]))
    return p


# ============================================================================ антураж «зоны» (этап 1: станция)

def painted_board(name, w, h, loc, mat, face="-y", lean=0.0):
    """Фанерный щит с надписью. face — куда смотрит лицевая сторона (-y, +y, -x, +x); lean — наклон верха к стене."""
    b = sign_plate(name, (w, 0.018, h), (0, 0, 0), mat)      # читается с -Y
    b.rotation_euler = (lean, 0, math.radians({"-y": 0, "+y": 180, "-x": -90, "+x": 90}[face]))
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
    p.append(painted_board("graf_board1", 1.4, 0.7, (ST_W / 2 - 0.12, 9.0, 0.38), m["board1"], face="-x", lean=math.radians(-12)))
    p.append(painted_board("graf_board2", 1.2, 0.6, (-ST_W / 2 + 0.03, 9.4, P + 1.35), m["board2"], face="+x"))
    p.append(painted_board("graf_board3", 1.0, 0.5, (DOOR_X + 1.5, -ST_LEN / 2 + 0.03, 1.4), m["board3"], face="+y"))
    for k, (x, y, z) in enumerate(((-ST_W / 2 + 0.035, 9.0, P + 1.62), (-ST_W / 2 + 0.035, 9.8, P + 1.62))):   # гвозди
        p.append(cyl(f"graf_nail{k}", 0.006, 0.03, (x + 0.01, y, z), m["steel"], ROT_Y, 6))
    # --- знак радиации у портала и рядом с ним, ржавый, на одном гвозде (перекошен)
    rad = sign_plate("rad_sign", (0.8, 0.012, 0.4), (TUN_W / 2 + 0.9, ST_LEN / 2 - 0.03, 2.1), m["sign_rad"])
    rad.rotation_euler = (0, math.radians(7), 0)
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
    """Шахтный светильник в решётке на кронштейне. Origin — точка крепления к своду, лампа ниже."""
    global TEX_DIR
    TEX_DIR = tex_dir
    reset_fn()
    m = mats()
    p = [box("mount", (0.2, 0.2, 0.04), (0, 0, -0.02), m["rust"]),
         cyl("stem", 0.015, 0.25, (0, 0, -0.15), m["steel"]),
         cyl("housing", 0.09, 0.08, (0, 0, -0.3), m["paint"]),
         sphere("glass", 0.075, (0, 0, -0.38), m["glass"], (1, 1, 1.2), (16, 10))]
    hz.selection(p[-1], "glass")          # hiddenSelection: скрипт включает светящийся материал
    for k in range(4):
        a = k * math.pi / 2
        p.append(box(f"cage{k}", (0.008, 0.008, 0.17), (math.cos(a) * 0.085, math.sin(a) * 0.085, -0.41), m["steel"]))
    p.append(torus("cage_ring", 0.085, 0.005, (0, 0, -0.49), m["steel"], (0, 0, 0), (16, 6)))
    o = join(p, "tunnel_lamp")
    uv_box(o, 1.0)
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
    return p, g


def build_tunnel(outdir, save_fn, reset_fn, L=10.0, name="tunnel_10m", variant="a"):
    reset_fn()
    m = mats()
    short = L < 5
    floor_len = 2.02 if short else L
    wall_len = 2.2 if short else L
    p = [box("floor", (TUN_W + 2 * WALL_T, floor_len, 0.3), (0, 0, -0.15), m["concrete"], round_edges=False)]
    p += vault("t", TUN_W, TUN_WALL_H, TUN_RISE, wall_len, 0, m["wall"], m["concrete"])
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
        # отметка пикета на стене
        p.append(box("picket", (0.02, 0.3, 0.2), (-TUN_W / 2 + 0.01, 2.5, walk_h + 1.5), m["sign_in"]))
        amb, amb_geo = tunnel_props(variant, m, walk_h)
        p += amb
    finish(p, name)
    for gname, gsize, gloc in amb_geo:
        geo(gname, gsize, gloc)
    geo("geometry_walkway", (walk_w, floor_len, walk_h), (wx, 0, walk_h / 2))
    geo("geometry_floor", (TUN_W + 1, floor_len, 0.4), (0, 0, -0.2))
    for sx in (-1, 1):
        geo(f"geometry_wall{sx}", (0.5, wall_len, TUN_WALL_H + TUN_RISE), (sx * (TUN_W / 2 + 0.25), 0, (TUN_WALL_H + TUN_RISE) / 2))
    geo("geometry_roof", (TUN_W + 1, wall_len, 0.5), (0, 0, TUN_WALL_H + TUN_RISE + 0.25))
    save_fn(outdir, name)


def build_all(outdir, tex_dir, save_fn, reset_fn):
    global TEX_DIR
    TEX_DIR = tex_dir
    build_entrance(outdir, save_fn, reset_fn)
    build_inner_door(outdir, save_fn, reset_fn)
    build_stairs(outdir, save_fn, reset_fn)
    build_corridor(outdir, save_fn, reset_fn)
    build_station(outdir, save_fn, reset_fn)
    build_tunnel(outdir, save_fn, reset_fn)
    for v in "bcd":                                  # варианты звена с антуражем
        build_tunnel(outdir, save_fn, reset_fn, 10.0, "tunnel_10m_" + v, v)
    build_tunnel(outdir, save_fn, reset_fn, 2.4, "tunnel_2m")
    build_dispenser(outdir, save_fn, reset_fn, tex_dir)
    build_lamp(outdir, save_fn, reset_fn, tex_dir)
