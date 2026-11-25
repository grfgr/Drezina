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
    })
    return m


TEX_DIR = None
box, cyl, torus, sphere, smooth = hz.box, hz.cyl, hz.torus, hz.sphere, hz.smooth
ROT_X, ROT_Y = hz.ROT_X, hz.ROT_Y


# ============================================================================ утилиты

# размер тайла по материалу (м): мелкий рисунок — мельче тайл
TILE_BY_MATERIAL = {"metro_hazard": 0.7, "metro_door": 1.2, "drezina_steel": 1.0, "drezina_rust": 1.0,
                    "drezina_paint_green": 1.0, "drezina_paint_blue": 1.0, "drezina_wood": 1.2,
                    "drezina_canvas": 0.8, "drezina_tape": 0.5, "metro_tubing": 1.5}


def uv_box(obj, tile=3.0):
    """Плоская проекция по доминирующей оси в координатах объекта: v = высота / tile.
    Для стен это значит, что зелёная полоса краски всегда снизу (origin объекта на уровне пола)."""
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    uv = bm.loops.layers.uv.verify()
    slots = [ms.material.name if ms.material else "" for ms in obj.material_slots]
    for f in bm.faces:
        if f.material_index < len(slots) and slots[f.material_index].startswith(("metro_sign", "drezina_plate")):
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


def vault(prefix, w, wall_h, rise, length, y, wall_mat, vault_mat, t=WALL_T, segs=14):
    """Стены (двухцветная краска) + эллиптический свод из плит."""
    parts = []
    for sx in (-1, 1):
        parts.append(box(f"{prefix}_wall{sx}", (t, length, wall_h), (sx * (w / 2 + t / 2), y, wall_h / 2), wall_mat, round_edges=False))
    a, b = w / 2 + t / 2, rise + t / 2
    prev = (a, wall_h)
    for i in range(1, segs + 1):
        th = math.pi * i / segs
        p = (math.cos(th) * a, wall_h + math.sin(th) * b)
        mx, mz = (prev[0] + p[0]) / 2, (prev[1] + p[1]) / 2
        ln = math.dist(prev, p) + 0.03
        ang = math.atan2(p[1] - prev[1], p[0] - prev[0])
        parts.append(box(f"{prefix}_v{i}", (ln, length, t), (mx, y, mz), vault_mat, (0, -ang, 0), round_edges=False))
        prev = p
    return parts


def rib(prefix, w, wall_h, rise, y, mat, depth=0.22, t=0.14, segs=14):
    """Чугунный тюбинг-ребро по контуру свода (выступает внутрь)."""
    parts = []
    a, b = w / 2 - t / 2, rise - t / 2
    for sx in (-1, 1):
        parts.append(box(f"{prefix}_c{sx}", (t, depth, wall_h), (sx * a, y, wall_h / 2), mat))
    prev = (a, wall_h)
    for i in range(1, segs + 1):
        th = math.pi * i / segs
        p = (math.cos(th) * a, wall_h + math.sin(th) * b)
        ln = math.dist(prev, p) + 0.02
        ang = math.atan2(p[1] - prev[1], p[0] - prev[0])
        parts.append(box(f"{prefix}_a{i}", (ln, depth, t), ((prev[0] + p[0]) / 2, y, (prev[1] + p[1]) / 2), mat, (0, -ang, 0)))
        prev = p
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

def earth_mound(name, center, scale, cut_y, mat):
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
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, -0.05), plane_no=(0, 0, -1), clear_outer=True)
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
    p.append(box("block", (BW, BD, BH), (0, -BD / 2, BH / 2), m["concrete"]))
    # портал: толстая рамка вокруг ниши
    # (внутренние края портала вплотную к коробке двери: 1.6/2 + 0.18 = 0.98)
    p.append(box("portal_l", (0.9, 0.6, 3.5), (-1.43, 0.2, 1.75), m["concrete"]))
    p.append(box("portal_r", (0.9, 0.6, 3.5), (1.43, 0.2, 1.75), m["concrete"]))
    p.append(box("portal_top", (1.96, 0.6, 0.92), (0, 0.2, 3.04), m["concrete"]))   # строго между боковинами
    p.append(box("visor", (4.4, 1.1, 0.22), (0, 0.55, 3.55), m["concrete"], (math.radians(-5), 0, 0)))
    p.append(box("niche_floor", (2.2, 1.0, 0.1), (0, 0.0, 0.05), m["concrete"]))
    # откосные стенки, держат насыпь
    for sx in (-1, 1):
        p.append(box(f"wing{sx}", (0.4, 3.2, 3.4), (sx * 2.3, 1.4, 1.0), m["concrete"], (math.radians(-32), 0, 0)))
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
    mound = earth_mound("mound", (0, -2.9, 0), (6.0, 6.2, 4.4), -0.35, m["dirt"])
    uv_box(mound, 4.0)
    o = join([concrete, mound], "bunker_entrance")
    smooth(o, 40)
    hz.selection(o, "bunker_entrance")
    # геометрия
    geo("geometry_block", (BW + 0.4, BD + 0.7, 3.8), (0, -BD / 2 + 0.3, 1.9))
    for sx in (-1, 1):
        geo(f"geometry_wing{sx}", (0.4, 3.2, 3.4), (sx * 2.3, 1.4, 1.0), (math.radians(-32), 0, 0))
    geo("geometry_mound", (11, 8, 3.5), (0, -4.5, 1.75))
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
    p.append(box("divider", (0.15, run, STAIR_TOP + 1.0), (0, 0, (STAIR_TOP + 1.0) / 2), m["concrete"], round_edges=False))
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
    geo("geometry_divider", (0.15, run, STAIR_TOP + 1.0), (0, 0, (STAIR_TOP + 1.0) / 2))
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
    for i, (x, y) in enumerate(((4.9, -10.5), (4.9, -9.6), (4.7, -10.0))):
        p.append(box(f"crate{i}", (0.7, 0.6, 0.5), (x, y, 0.25 + (0.5 if i == 2 else 0)), m["wood"], (0, 0, math.radians(rnd.uniform(-10, 10)))))
    p.append(cyl("barrel", 0.3, 0.9, (-5.2, -6.5, 0.45), m["rust"]))
    for z in (0.15, 0.75):
        p.append(torus(f"barrel_hoop{z}", 0.305, 0.012, (-5.2, -6.5, z), m["rust"], (0, 0, 0), (32, 6)))
    o = finish(p, "metro_station")
    geo("geometry_floor", (ST_W + 1, ST_LEN, 0.4), (0, 0, -0.2))
    for sx in (-1, 1):
        geo(f"geometry_wall{sx}", (0.5, ST_LEN, total_h), (sx * (ST_W / 2 + 0.25), 0, total_h / 2))
        geo(f"geometry_front{sx}", ((ST_W - TUN_W) / 2, 0.5, total_h), (sx * (TUN_W / 2 + (ST_W - TUN_W) / 4), ST_LEN / 2 + 0.25, total_h / 2))
    geo("geometry_back_l", (ST_W / 2 + DOOR_X - 0.8 + 0.5, 0.5, total_h), ((-ST_W / 2 + DOOR_X - 0.8) / 2, -ST_LEN / 2 - 0.25, total_h / 2))
    geo("geometry_back_r", (ST_W / 2 - DOOR_X - 0.8, 0.5, total_h), ((ST_W / 2 + DOOR_X + 0.8) / 2, -ST_LEN / 2 - 0.25, total_h / 2))
    geo("geometry_roof", (ST_W + 1, ST_LEN, 0.5), (0, 0, total_h))
    save_fn(outdir, "metro_station")


# ============================================================================ тоннель

def build_tunnel(outdir, save_fn, reset_fn, L=10.0, name="tunnel_10m"):
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
    if not short:
        p += debris("deb", (2.2, rnd.uniform(-3, 3)), 3, 0.5, m)
    finish(p, name)
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
    build_tunnel(outdir, save_fn, reset_fn, 2.4, "tunnel_2m")
