"""
Дрезина «из зоны»: ручная дрезина 1890-х, пережившая полвека на заброшенной ветке.
Строится слоями:

  СЛОЙ 1 — силуэт и пропорции: рама, пол, колёса, оси (размеры совпадают со скриптом мода).
  СЛОЙ 2 — механизм: А-стойка, коромысло, шатун, шестерни с зубьями, буксы с рессорами, тормоз, сцепки.
  СЛОЙ 3 — износ и самодел: заплатки, ряды болтов, недостающая и заменённая доска, поручень из арматуры,
            керосиновый фонарь на штанге, ящик с инструментом, мешки с песком, моток проволоки,
            изолента на ручках, табличка с трафаретным номером.
  СЛОЙ 4 — материалы: процедурные текстуры (tools/textures/make_textures.py) + UV-развёртка кубом.
  СЛОЙ 5 — крепёж и сварка: сварные швы, шайбы под гайками, U-болты рессор, шплинты, пресс-маслёнки,
            гайки на концах осей.
  СЛОЙ 6 — быт путевого обходчика: маслёнка с носиком, ведро с песком, канистра, навесной замок на ящике,
            термос, моток верёвки на штанге фонаря, тряпка на поручне.
  СЛОЙ 7 — повреждения: вмятины на листовом металле, пулевые отверстия в кожухе и ящике, расщеп доски.
  СЛОЙ 8 — самодельный свет «от генератора»: велосипедная динамо-машина трётся о заднее левое колесо,
            провода на изоленте по раме к двум старым автомобильным фарам (вперёд и назад) и к голой
            лампочке в проволочной клетке под стойкой. Свет включается скриптом, когда дрезина едет.

Скругление: все бруски получают фаску (bevel), цилиндры — до 32 граней, всё сглаживается по углу
(Smooth by Angle 35°), поэтому граней не видно, а плоскости остаются плоскими.
Дополнительно сохраняются упрощённые handcar_lod1 / handcar_lod2 для дальних LOD.

Named selections / memory-точки (не менять — на них завязаны model.cfg и скрипт):
  lever, wheel_fl, wheel_fr, wheel_rl, wheel_rr, body;
  mem_lever_axis_1/2, mem_axle_front_1/2, mem_axle_rear_1/2, mem_seat_driver.
"""
import math
import os
import random

import bpy

GAUGE = 1.520
WHEEL_R = 0.36
DECK_TOP = 0.62
AXLE_Y = 0.62
HALF = GAUGE / 2
PIVOT_Z = DECK_TOP + 1.05
SILL_X = HALF - 0.16

rnd = random.Random(1890)
TEX_DIR = None  # задаётся из build()


# ============================================================================ материалы (слой 4)

def tex_material(name, tex, rough=0.85, metal=0.0, emission=None):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    path = os.path.join(TEX_DIR, tex + "_co.png") if TEX_DIR else None
    if path and os.path.exists(path):
        img = nt.nodes.new("ShaderNodeTexImage")
        img.image = bpy.data.images.load(path, check_existing=True)
        nt.links.new(img.outputs["Color"], bsdf.inputs["Base Color"])
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1)
        bsdf.inputs["Emission Strength"].default_value = 3.0
    # путь к игровой текстуре — для экспортёра в p3d
    mat["dayz_texture"] = "Drezina\\data\\textures\\%s_co.paa" % tex
    mat["dayz_rvmat"] = "Drezina\\data\\textures\\%s.rvmat" % tex
    return mat


def materials():
    return {
        "paint": tex_material("drezina_paint_green", "drezina_paint_green", 0.8, 0.3),
        "paint2": tex_material("drezina_paint_blue", "drezina_paint_blue", 0.8, 0.3),
        "rust": tex_material("drezina_rust", "drezina_rust", 0.95, 0.4),
        "wood": tex_material("drezina_wood", "drezina_wood", 0.9),
        "steel": tex_material("drezina_steel", "drezina_steel", 0.55, 0.85),
        "tape": tex_material("drezina_tape", "drezina_tape", 0.7),
        "canvas": tex_material("drezina_canvas", "drezina_canvas", 1.0),
        "plate": tex_material("drezina_plate", "drezina_plate", 0.8, 0.3),
        "glass": tex_material("drezina_glass", "drezina_glass", 0.2, 0.0, emission=(1.0, 0.7, 0.3)),
    }


# ============================================================================ примитивы

def _finish(o, name, mat):
    o.name = name
    o.data.materials.append(mat)
    return o


def bevel(o, width, segments):
    mod = o.modifiers.new("bevel", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = "ANGLE"
    mod.angle_limit = math.radians(40)
    mod.harden_normals = False
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier=mod.name)


def box(name, size, loc, mat, rot=(0, 0, 0), round_edges=True):
    """Брусок с фаской: на рёбрах ловится блик, граней не видно."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    smallest = min(size)
    if round_edges and smallest > 0.004:
        bevel(o, min(0.012, smallest * 0.3), 2 if smallest > 0.03 else 1)
    return _finish(o, name, mat)


def auto_verts(r):
    """Число граней цилиндра по радиусу: мелочь 12, крупное до 32."""
    return int(max(12, min(32, round(r * 160 / 4) * 4)))


def cyl(name, r, depth, loc, mat, rot=(0, 0, 0), verts=None):
    if verts is None or verts > 6:
        verts = max(verts or 0, auto_verts(r))
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    o = bpy.context.active_object
    if verts > 6 and depth > 0.02:
        bevel(o, min(r * 0.15, depth * 0.2, 0.006), 1)
    return _finish(o, name, mat)


def cone(name, r1, r2, depth, loc, mat, rot=(0, 0, 0), verts=12):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2, depth=depth, location=loc, rotation=rot)
    return _finish(bpy.context.active_object, name, mat)


def sphere(name, r, loc, mat, scale=(1, 1, 1), seg=(16, 10), rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg[0], ring_count=seg[1], radius=r, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return _finish(o, name, mat)


def smooth(obj, angle=35):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle))


def dent(obj, amount, cuts=4, seed=0):
    """Вмятины: подразбить лист и сдвинуть вершины гладким «шумом» из синусов."""
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.subdivide(number_cuts=cuts)
    bpy.ops.object.mode_set(mode="OBJECT")
    for v in obj.data.vertices:
        x, y, z = v.co
        n = (math.sin(x * 23 + seed) * math.sin(y * 19 + seed * 2) + math.sin(z * 17 + y * 7 + seed)) * 0.5
        v.co.x += n * amount
        v.co.y += math.sin(x * 13 + z * 11 + seed) * amount * 0.6


def torus(name, R, r, loc, mat, rot=(0, 0, 0), seg=(20, 6)):
    seg = (max(seg[0], 24), max(seg[1], 8))
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=seg[0], minor_segments=seg[1],
                                     location=loc, rotation=rot)
    return _finish(bpy.context.active_object, name, mat)


ROT_X = (0, math.radians(90), 0)   # ось цилиндра вдоль X
ROT_Y = (math.radians(90), 0, 0)   # ось цилиндра вдоль Y


def tube_x(name, r_out, r_in, width, loc, mat, segments=48):
    """Кольцо с осью X (бандаж/обод)."""
    import bmesh
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    rings = []
    for x in (-width / 2, width / 2):
        for r in (r_out, r_in):
            rings.append([bm.verts.new((x, math.cos(2 * math.pi * i / segments) * r,
                                        math.sin(2 * math.pi * i / segments) * r)) for i in range(segments)])
    oa, ia, ob, ib = rings
    for i in range(segments):
        j = (i + 1) % segments
        bm.faces.new((oa[i], oa[j], ob[j], ob[i]))
        bm.faces.new((ia[j], ia[i], ib[i], ib[j]))
        bm.faces.new((oa[j], oa[i], ia[i], ia[j]))
        bm.faces.new((ob[i], ob[j], ib[j], ib[i]))
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    o = bpy.data.objects.new(name, mesh)
    o.location = loc
    bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(mat)
    return o


def channel_y(name, length, loc, mat, h=0.16, w=0.07, t=0.012, open_sign=1):
    """Швеллер вдоль Y (полками в сторону open_sign по X)."""
    x, y, z = loc
    parts = [box(name + "_web", (t, length, h), (x, y, z), mat)]
    for sz in (-1, 1):
        parts.append(box(name + f"_fl{sz}", (w, length, t), (x + open_sign * w / 2, y, z + sz * (h / 2 - t / 2)), mat))
    return parts


def channel_x(name, length, loc, mat, h=0.16, w=0.07, t=0.012, open_sign=1):
    x, y, z = loc
    parts = [box(name + "_web", (length, t, h), (x, y, z), mat)]
    for sz in (-1, 1):
        parts.append(box(name + f"_fl{sz}", (length, w, t), (x, y + open_sign * w / 2, z + sz * (h / 2 - t / 2)), mat))
    return parts


def angle(name, length, loc, rot, mat, w=0.06, t=0.008):
    """Уголок (L-профиль) длиной length вдоль локальной Z, повёрнутый rot."""
    a = box(name + "_a", (w, t, length), (0, 0, 0), mat)
    b = box(name + "_b", (t, w, length), (0, 0, 0), mat)
    a.location = (w / 2 - t / 2, 0, 0)
    b.location = (0, w / 2 - t / 2, 0)
    for o in (a, b):
        bpy.ops.object.select_all(action="DESELECT")
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.transform_apply(location=True)
    j = join([a, b], name)
    j.rotation_euler = rot
    j.location = loc
    bpy.ops.object.select_all(action="DESELECT")
    j.select_set(True)
    bpy.context.view_layer.objects.active = j
    bpy.ops.object.transform_apply(location=True, rotation=True)
    return j


def bolt(name, loc, normal, mat, r=0.012):
    """Шестигранная головка болта, normal: 'x', 'y' или 'z' (+/-)."""
    axis = normal[-1]
    sign = -1 if normal.startswith("-") else 1
    rot = {"x": ROT_X, "y": ROT_Y, "z": (0, 0, 0)}[axis]
    off = [0, 0, 0]
    off["xyz".index(axis)] = sign * 0.006
    return cyl(name, r, 0.012, (loc[0] + off[0], loc[1] + off[1], loc[2] + off[2]), mat, rot, 6)


def bolt_row(prefix, start, end, count, normal, mat, out):
    for i in range(count):
        f = i / max(count - 1, 1)
        p = [start[k] + (end[k] - start[k]) * f for k in range(3)]
        out.append(bolt(f"{prefix}{i}", p, normal, mat))


def join(objs, name):
    objs = [o for o in objs if o]
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.active_object
    o.name = name
    o.data.name = name
    return o


def set_origin(obj, point):
    cur = bpy.context.scene.cursor.location.copy()
    bpy.context.scene.cursor.location = point
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
    bpy.context.scene.cursor.location = cur


def uv_cube(obj, size=1.0):
    """UV кубом: текстура ~1 м на тайл (слой 4)."""
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.cube_project(cube_size=size, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def uv_fit(obj):
    """UV на весь тайл (для таблички с номером)."""
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.cube_project(cube_size=1.0, scale_to_bounds=True)
    bpy.ops.object.mode_set(mode="OBJECT")


def selection(obj, name):
    vg = obj.vertex_groups.new(name=name)
    vg.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")


def mem_point(name, loc):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = "SPHERE"
    e.empty_display_size = 0.03
    e.location = loc
    bpy.context.scene.collection.objects.link(e)


# ============================================================================ СЛОЙ 1: силуэт

def layer1_frame(m, out):
    # продольные швеллеры рамы (крашеные, полками внутрь)
    for sx in (-1, 1):
        out += channel_y(f"sill{sx}", 2.24, (sx * SILL_X, 0, DECK_TOP - 0.12), m["paint"], open_sign=-sx)
    # торцевые швеллеры
    for sy in (-1, 1):
        out += channel_x(f"end{sy}", 1.34, (0, sy * 1.10, DECK_TOP - 0.12), m["paint"], open_sign=-sy)
    # поперечины под полом
    for y in (-0.35, 0.35):
        out.append(box(f"cross{y}", (1.20, 0.06, 0.06), (0, y, DECK_TOP - 0.07), m["rust"]))


def layer1_deck(m, out_wood, out_metal):
    """Пол: 9 досок, одна пропала, одна заменена рифлёным листом, остальные гуляют по высоте."""
    for i in range(9):
        y = -0.98 + i * 0.245
        if i == 6:
            continue                                # доски нет — видна рама
        if i == 2:
            out_metal.append(box("plank_sheet", (1.26, 0.235, 0.008), (0, y, DECK_TOP - 0.004), m["steel"]))
            for k in range(14):                      # рифление
                out_metal.append(box(f"rib{k}", (0.04, 0.012, 0.005),
                                     (-0.58 + k * 0.09, y + (0.05 if k % 2 else -0.05), DECK_TOP + 0.002), m["steel"],
                                     (0, 0, math.radians(45 if k % 2 else -45))))
            continue
        dz = rnd.uniform(-0.008, 0.006)
        rz = math.radians(rnd.uniform(-0.8, 0.8))
        length = 1.24 - (0.12 if i == 8 else 0)      # обломанная доска
        out_wood.append(box(f"plank{i}", (length, 0.215, 0.04), (0 + (0.06 if i == 8 else 0), y, DECK_TOP - 0.02 + dz),
                            m["wood"], (0, 0, rz)))


def wheel(name, x, y, m):
    """Литое колесо со спицами, стальной бандаж с ребордой (слой 1+2)."""
    parts = [
        tube_x(name + "_tire", WHEEL_R, WHEEL_R - 0.04, 0.10, (x, y, WHEEL_R), m["steel"]),
        tube_x(name + "_flange", WHEEL_R + 0.028, WHEEL_R - 0.04, 0.022, (x - math.copysign(0.055, x), y, WHEEL_R), m["steel"]),
        torus(name + "_rim", WHEEL_R - 0.055, 0.025, (x, y, WHEEL_R), m["rust"], ROT_X, (24, 6)),
        cyl(name + "_hub", 0.075, 0.15, (x, y, WHEEL_R), m["rust"], ROT_X, 12),
        cyl(name + "_hubcap", 0.045, 0.17, (x, y, WHEEL_R), m["steel"], ROT_X, 6),
    ]
    spokes = 10
    for i in range(spokes):
        a = 2 * math.pi * i / spokes
        r = (WHEEL_R - 0.06 + 0.075) / 2
        # спица — овальный конус: толще у ступицы
        sp = cone(f"{name}_spoke{i}", 0.017, 0.012, WHEEL_R - 0.10,
                  (x, y + math.sin(a) * r, WHEEL_R + math.cos(a) * r), m["rust"], (-a, 0, 0), 10)
        sp.scale = (0.8, 1.0, 1.0)
        parts.append(sp)
    # гайки ступицы
    for k in range(5):
        a = 2 * math.pi * k / 5
        parts.append(cyl(f"{name}_nut{k}", 0.009, 0.16, (x, y + math.sin(a) * 0.05, WHEEL_R + math.cos(a) * 0.05), m["steel"], ROT_X, 6))
    o = join(parts, name)
    set_origin(o, (x, y, WHEEL_R))
    uv_cube(o, 0.6)
    smooth(o)
    selection(o, name)
    return o


# ============================================================================ СЛОЙ 2: механизм

def layer2_running_gear(m, out):
    for y in (-AXLE_Y, AXLE_Y):
        out.append(cyl(f"axle{y}", 0.038, GAUGE + 0.12, (0, y, WHEEL_R), m["steel"], ROT_X, 10))
        for sx in (-1, 1):
            bx = sx * SILL_X
            # букса
            out.append(box(f"jbox{y}{sx}", (0.11, 0.17, 0.15), (bx, y, WHEEL_R), m["rust"]))
            out.append(box(f"jlid{y}{sx}", (0.012, 0.13, 0.11), (bx + sx * 0.06, y, WHEEL_R), m["paint"]))
            for dy in (-0.05, 0.05):
                for dz in (-0.04, 0.04):
                    out.append(bolt(f"jb{y}{sx}{dy}{dz}", (bx + sx * 0.066, y + dy, WHEEL_R + dz), "x" if sx > 0 else "-x", m["steel"]))
            # листовая рессора над буксой
            for k in range(3):
                ln = 0.42 - k * 0.1
                out.append(box(f"leaf{y}{sx}{k}", (0.06, ln, 0.012),
                               (bx, y, WHEEL_R + 0.085 + k * 0.013), m["steel"], (math.radians(0), 0, 0)))
            # серьги рессоры к раме
            for sy in (-1, 1):
                out.append(box(f"shackle{y}{sx}{sy}", (0.02, 0.02, DECK_TOP - 0.2 - WHEEL_R - 0.08),
                               (bx, y + sy * 0.2, (DECK_TOP - 0.2 + WHEEL_R + 0.08) / 2 + 0.005), m["rust"]))


def gear(name, r, width, teeth, loc, mat):
    parts = [cyl(name + "_disc", r * 0.92, width, loc, mat, ROT_X, max(16, teeth))]
    for i in range(teeth):
        a = 2 * math.pi * i / teeth
        parts.append(box(f"{name}_t{i}", (width, r * 0.16, r * 0.12),
                         (loc[0], loc[1] + math.sin(a) * r * 0.97, loc[2] + math.cos(a) * r * 0.97), mat, (-a, 0, 0)))
    parts.append(cyl(name + "_boss", r * 0.25, width * 1.6, loc, mat, ROT_X, 10))
    return parts


def layer2_drive(m, out):
    gx = 0.28
    # большая шестерня на передней оси + шестерня-вал с кривошипом
    out += gear("gear_big", 0.22, 0.04, 30, (gx, AXLE_Y, WHEEL_R), m["steel"])
    pin_y, pin_z = AXLE_Y - 0.31, WHEEL_R + 0.10
    out += gear("gear_small", 0.09, 0.045, 12, (gx, pin_y, pin_z), m["steel"])
    out.append(cyl("countershaft", 0.025, 0.7, (0.05, pin_y, pin_z), m["steel"], ROT_X, 8))
    for sx in (-0.25, 0.42):
        out.append(box(f"cs_bearing{sx}", (0.06, 0.08, 0.12), (sx, pin_y, pin_z + 0.02), m["rust"]))
        out.append(box(f"cs_hanger{sx}", (0.04, 0.04, DECK_TOP - 0.04 - pin_z), (sx, pin_y, (DECK_TOP - 0.04 + pin_z) / 2 + 0.03), m["rust"]))
    # кожух шестерни (полукруглый, ржавый, с вмятиной)
    out.append(box("gear_guard", (0.012, 0.52, 0.3), (gx + 0.05, AXLE_Y - 0.05, WHEEL_R + 0.12), m["rust"], (math.radians(4), 0, math.radians(3))))
    # кривошип и шатун до коромысла
    out.append(box("crank", (0.03, 0.06, 0.14), (gx + 0.06, pin_y, pin_z + 0.06), m["steel"]))
    rod_bot = (gx + 0.06, pin_y, pin_z + 0.12)
    rod_top = (gx + 0.06, -0.30, PIVOT_Z - 0.04)
    dy, dz = rod_top[1] - rod_bot[1], rod_top[2] - rod_bot[2]
    ln = math.hypot(dy, dz)
    ang = math.atan2(dy, dz)
    out.append(box("conrod", (0.03, 0.035, ln), ((rod_bot[0]), (rod_bot[1] + rod_top[1]) / 2, (rod_bot[2] + rod_top[2]) / 2),
                   m["paint2"], (-ang, 0, 0)))
    out.append(cyl("conrod_eye", 0.035, 0.04, rod_bot, m["steel"], ROT_X, 10))


def layer2_aframe(m, out):
    """А-стойка из уголка, перекрашенная в синий (стойку меняли), с распорками и косынками."""
    a = math.atan2(0.42, 1.05)
    for sx in (-0.17, 0.17):
        for sy in (-1, 1):
            out.append(angle(f"leg{sx}{sy}", 1.14, (sx, sy * 0.21, DECK_TOP + 0.52), (sy * a, 0, 0), m["paint2"]))
            out.append(box(f"foot{sx}{sy}", (0.1, 0.14, 0.01), (sx, sy * 0.42, DECK_TOP + 0.005), m["paint2"]))
            bolt_row(f"fb{sx}{sy}", (sx - 0.03, sy * 0.42, DECK_TOP + 0.012), (sx + 0.03, sy * 0.42, DECK_TOP + 0.012), 2, "z", m["steel"], out)
        out.append(box(f"brace{sx}", (0.012, 0.66, 0.05), (sx, 0, DECK_TOP + 0.32), m["paint2"]))
        out.append(box(f"brace_hi{sx}", (0.012, 0.36, 0.04), (sx, 0, DECK_TOP + 0.72), m["paint2"]))
    # диагональ из арматуры (самодельное усиление)
    out.append(cyl("rebar_diag", 0.009, 0.75, (0, 0.1, DECK_TOP + 0.55), m["rust"], (math.radians(30), math.radians(90 - 24), 0), 6))
    # подшипники оси качания
    for sx in (-0.17, 0.17):
        out.append(box(f"pillow{sx}", (0.06, 0.12, 0.1), (sx, 0, PIVOT_Z - 0.03), m["rust"]))
        out.append(bolt(f"pb{sx}", (sx, 0.04, PIVOT_Z + 0.025), "z", m["steel"]))
        out.append(bolt(f"pb2{sx}", (sx, -0.04, PIVOT_Z + 0.025), "z", m["steel"]))
    out.append(cyl("pivot_pin", 0.022, 0.46, (0, 0, PIVOT_Z), m["steel"], ROT_X, 10))


def layer2_brake(m, out):
    """Ручной тормоз: рычаг у заднего правого угла, тяга, колодки на задних колёсах."""
    bx, by = SILL_X - 0.05, -0.92
    tilt = math.radians(-12)
    half = 0.3
    out.append(box("brake_lever", (0.03, 0.03, half * 2), (bx, by, DECK_TOP + half), m["steel"], (tilt, 0, 0)))
    top = (bx, by - math.sin(tilt) * half * 2, DECK_TOP + math.cos(tilt) * half * 2)
    out.append(cyl("brake_grip", 0.02, 0.14, (top[0] - 0.06, top[1], top[2]), m["tape"], ROT_X, 8))
    out.append(box("brake_quadrant", (0.012, 0.18, 0.1), (bx + 0.03, by, DECK_TOP + 0.06), m["rust"]))
    out.append(box("brake_rod", (1.3, 0.016, 0.016), (0, -AXLE_Y + 0.42, WHEEL_R + 0.03), m["steel"]))
    for sx in (-1, 1):
        out.append(box(f"brake_shoe{sx}", (0.08, 0.06, 0.16), (sx * HALF, -AXLE_Y + WHEEL_R + 0.03, WHEEL_R), m["rust"], (math.radians(-10), 0, 0)))
        out.append(box(f"brake_arm{sx}", (0.02, 0.06, 0.25), (sx * (HALF - 0.08), -AXLE_Y + 0.4, WHEEL_R + 0.08), m["steel"]))


def layer2_couplers(m, out):
    for sy in (-1, 1):
        y = sy * 1.17
        out.append(box(f"buffer_plate{sy}", (0.2, 0.012, 0.14), (0, y, DECK_TOP - 0.12), m["steel"]))
        out.append(box(f"hook{sy}", (0.03, 0.12, 0.03), (0, y + sy * 0.06, DECK_TOP - 0.15), m["steel"]))
        out.append(box(f"hook_tip{sy}", (0.03, 0.03, 0.06), (0, y + sy * 0.11, DECK_TOP - 0.13), m["steel"]))
    # цепь, свисающая с переднего крюка
    for k in range(5):
        out.append(torus(f"chain{k}", 0.025, 0.006, (0.0, 1.30, DECK_TOP - 0.19 - k * 0.04), m["steel"],
                         (0, math.radians(90 * (k % 2)), 0), (8, 4)))


# ============================================================================ СЛОЙ 3: износ и самодел

def layer3_wear(m, out):
    # сварные заплатки на швеллерах и ряды заклёпок
    for sx in (-1, 1):
        x = sx * (SILL_X + 0.012)
        for (y, ln) in ((-0.55, 0.28), (0.8, 0.2)):
            out.append(box(f"patch{sx}{y}", (0.006, ln, 0.11), (x + sx * 0.003, y, DECK_TOP - 0.12 + rnd.uniform(-0.01, 0.01)),
                           m["rust"], (0, 0, 0)))
            bolt_row(f"pr{sx}{y}", (x + sx * 0.006, y - ln / 2 + 0.03, DECK_TOP - 0.08), (x + sx * 0.006, y + ln / 2 - 0.03, DECK_TOP - 0.08), 3, "x" if sx > 0 else "-x", m["steel"], out)
        bolt_row(f"rivet{sx}", (x, -1.0, DECK_TOP - 0.17), (x, 1.0, DECK_TOP - 0.17), 9, "x" if sx > 0 else "-x", m["steel"], out)
    # болты, которыми прибиты доски
    for i in range(9):
        if i in (2, 6):
            continue
        y = -0.98 + i * 0.245
        for sx in (-1, 1):
            out.append(bolt(f"deckbolt{i}{sx}", (sx * SILL_X, y, DECK_TOP + 0.002), "z", m["steel"], 0.011))


def layer3_props(m, out_props):
    p = out_props
    # поручень из гнутой арматуры по левому борту
    rx = -SILL_X - 0.02
    for y in (-0.9, 0.0, 0.9):
        p.append(cyl(f"rail_post{y}", 0.011, 0.55, (rx, y, DECK_TOP + 0.27), m["rust"], (0, math.radians(rnd.uniform(-3, 3)), 0), 6))
    p.append(cyl("rail_bar", 0.011, 1.86, (rx, 0, DECK_TOP + 0.54), m["rust"], ROT_Y, 6))
    p.append(cyl("rail_wire", 0.004, 1.8, (rx, 0, DECK_TOP + 0.3), m["steel"], ROT_Y, 4))

    # штанга с керосиновым фонарём на переднем левом углу
    lx, ly = -SILL_X - 0.05, 1.02          # штанга на боковине рамы, подальше от ручки рычага
    p.append(box("lamp_pole", (0.03, 0.03, 1.2), (lx, ly, DECK_TOP + 0.6), m["paint2"]))
    p.append(box("lamp_arm", (0.02, 0.22, 0.02), (lx, ly + 0.1, DECK_TOP + 1.18), m["steel"]))
    lz = DECK_TOP + 1.0
    lyy = ly + 0.2
    p.append(cyl("lamp_base", 0.07, 0.04, (lx, lyy, lz - 0.1), m["rust"], (0, 0, 0), 10))
    p.append(cyl("lamp_top", 0.06, 0.05, (lx, lyy, lz + 0.11), m["rust"], (0, 0, 0), 10))
    p.append(cyl("lamp_cap", 0.03, 0.04, (lx, lyy, lz + 0.155), m["rust"], (0, 0, 0), 8))
    for k in range(4):
        a = k * math.pi / 2
        p.append(box(f"lamp_cage{k}", (0.006, 0.006, 0.2), (lx + math.cos(a) * 0.062, lyy + math.sin(a) * 0.062, lz), m["steel"]))
    p.append(torus("lamp_ring", 0.025, 0.004, (lx, lyy, lz + 0.18), m["steel"], (math.radians(90), 0, 0), (8, 4)))
    glass = cyl("lamp_glass", 0.05, 0.19, (lx, lyy, lz), m["glass"], (0, 0, 0), 10)
    p.append(glass)

    # ящик с инструментом (задний правый угол)
    tx, ty = 0.42, -0.98
    p.append(box("toolbox", (0.42, 0.2, 0.2), (tx, ty, DECK_TOP + 0.1), m["paint"], (0, 0, math.radians(4))))
    p.append(box("toolbox_lid", (0.43, 0.21, 0.02), (tx, ty, DECK_TOP + 0.205), m["rust"], (0, 0, math.radians(4))))
    p.append(cyl("toolbox_handle", 0.008, 0.18, (tx, ty, DECK_TOP + 0.24), m["steel"], ROT_X, 6))
    p.append(box("crowbar", (0.025, 0.025, 0.9), (tx - 0.05, ty + 0.14, DECK_TOP + 0.02), m["rust"], (math.radians(90), 0, math.radians(84))))

    # мешки с песком спереди (вместо буфера)
    for i, x in enumerate((-0.35, 0.0, 0.35)):
        bag = sphere(f"sandbag{i}", 1, (x, 1.02, DECK_TOP + 0.07), m["canvas"], (0.2, 0.13, 0.075), (20, 12),
                     (0, 0, math.radians(rnd.uniform(-8, 8))))
        # прижать низ к полу и «завязать» угол
        for v in bag.data.vertices:          # координаты локальные, мешок от -0.075 до 0.075 по Z
            if v.co.z < -0.035:
                v.co.z = -0.035 - (-0.035 - v.co.z) * 0.25
        p.append(bag)
        p.append(sphere(f"sandbag_tie{i}", 0.025, (x + 0.2, 1.02, DECK_TOP + 0.08), m["canvas"], (1.4, 0.8, 0.8), (10, 6)))
    # брезент, скатанный у стойки
    p.append(cyl("tarp_roll", 0.07, 0.6, (-0.4, 0.55, DECK_TOP + 0.07), m["canvas"], ROT_X, 10))
    for k in (-0.2, 0.2):
        p.append(torus(f"tarp_strap{k}", 0.072, 0.006, (-0.4 + k, 0.55, DECK_TOP + 0.07), m["tape"], ROT_X, (12, 4)))
    # моток проволоки на поручне
    p.append(torus("wire_coil", 0.12, 0.012, (rx - 0.01, 0.45, DECK_TOP + 0.38), m["steel"], (0, math.radians(90), 0), (16, 5)))


def layer3_plate(m):
    """Табличка с номером на правом борту."""
    pl = box("number_plate", (0.008, 0.36, 0.13), (SILL_X + 0.075, 0.25, DECK_TOP - 0.12), m["plate"])
    uv_fit(pl)
    return pl


# ============================================================================ СЛОЙ 5: крепёж и сварка

def weld_seam(prefix, start, end, mat, out, r=0.006):
    """Сварной шов — цепочка сплюснутых капель."""
    n = max(3, int(math.dist(start, end) / 0.012))
    for i in range(n):
        f = i / (n - 1)
        p = [start[k] + (end[k] - start[k]) * f for k in range(3)]
        out.append(sphere(f"{prefix}{i}", r, p, mat, (1.3, 1.3, 0.7), (8, 5)))


def layer5_fasteners(m, out):
    # швы по краям заплаток на раме
    for sx in (-1, 1):
        x = sx * (SILL_X + 0.018)
        for (y, ln) in ((-0.55, 0.28), (0.8, 0.2)):
            z0, z1 = DECK_TOP - 0.175, DECK_TOP - 0.065
            weld_seam(f"weld{sx}{y}a", (x, y - ln / 2, z0), (x, y - ln / 2, z1), m["rust"], out)
            weld_seam(f"weld{sx}{y}b", (x, y + ln / 2, z0), (x, y + ln / 2, z1), m["rust"], out)
    # гайки + шайбы на концах осей, шплинты
    for y in (-AXLE_Y, AXLE_Y):
        for sx in (-1, 1):
            xe = sx * (GAUGE / 2 + 0.075)
            out.append(cyl(f"axnut{y}{sx}", 0.03, 0.03, (xe, y, WHEEL_R), m["steel"], ROT_X, 6))
            out.append(cyl(f"axwash{y}{sx}", 0.042, 0.006, (xe - sx * 0.018, y, WHEEL_R), m["steel"], ROT_X))
            out.append(torus(f"cotter{y}{sx}", 0.012, 0.0025, (xe + sx * 0.02, y, WHEEL_R + 0.02), m["steel"], (0, 0, 0), (12, 6)))
            # пресс-маслёнка на буксе
            out.append(cyl(f"grease{y}{sx}", 0.008, 0.03, (sx * SILL_X, y, WHEEL_R + 0.09), m["steel"]))
            out.append(sphere(f"greaseball{y}{sx}", 0.009, (sx * SILL_X, y, WHEEL_R + 0.108), m["steel"]))
            # U-болты рессоры
            for dy in (-0.04, 0.04):
                out.append(torus(f"ubolt{y}{sx}{dy}", 0.04, 0.006, (sx * SILL_X, y + dy, WHEEL_R + 0.1), m["steel"], ROT_Y, (16, 6)))
    # угловые косынки рамы (закрывают стык швеллеров)
    for sx in (-1, 1):
        for sy in (-1, 1):
            out.append(box(f"gusset{sx}{sy}", (0.012, 0.16, 0.17), (sx * (SILL_X + 0.008), sy * 1.06, DECK_TOP - 0.12), m["paint"]))
            out.append(box(f"gusset_end{sx}{sy}", (0.16, 0.012, 0.17), (sx * (SILL_X - 0.07), sy * (1.10 + 0.008), DECK_TOP - 0.12), m["paint"]))
            bolt_row(f"gb{sx}{sy}", (sx * (SILL_X + 0.016), sy * 1.02, DECK_TOP - 0.16), (sx * (SILL_X + 0.016), sy * 1.02, DECK_TOP - 0.08), 2, "x" if sx > 0 else "-x", m["steel"], out)
    # шайбы под болтами ног стойки
    for sx in (-0.17, 0.17):
        for sy in (-1, 1):
            for dx in (-0.03, 0.03):
                out.append(cyl(f"legwash{sx}{sy}{dx}", 0.018, 0.004, (sx + dx, sy * 0.42, DECK_TOP + 0.011), m["steel"]))


# ============================================================================ СЛОЙ 6: быт обходчика

def layer6_life(m, out):
    # маслёнка с длинным носиком на крышке ящика
    ox, oy, oz = 0.32, -0.97, DECK_TOP + 0.215
    out.append(cyl("oilcan_body", 0.045, 0.07, (ox, oy, oz + 0.035), m["steel"]))
    out.append(cone("oilcan_top", 0.045, 0.012, 0.04, (ox, oy, oz + 0.09), m["steel"], (0, 0, 0), 16))
    out.append(cyl("oilcan_spout", 0.004, 0.16, (ox + 0.06, oy, oz + 0.13), m["steel"], (0, math.radians(55), 0), 8))
    out.append(torus("oilcan_handle", 0.03, 0.005, (ox - 0.045, oy, oz + 0.05), m["steel"], ROT_Y, (16, 6)))
    # ведро с песком (задний левый угол)
    bx, by = -0.4, -0.78
    out.append(cone("bucket", 0.1, 0.13, 0.24, (bx, by, DECK_TOP + 0.12), m["paint2"], (0, 0, 0), 28))
    out.append(cyl("bucket_sand", 0.122, 0.01, (bx, by, DECK_TOP + 0.225), m["canvas"], (0, 0, 0), 28))
    out.append(torus("bucket_rim", 0.13, 0.006, (bx, by, DECK_TOP + 0.24), m["steel"], (0, 0, 0), (28, 6)))
    out.append(torus("bucket_handle", 0.13, 0.004, (bx, by, DECK_TOP + 0.24), m["steel"], (math.radians(70), 0, 0), (24, 6)))
    # канистра (передний правый угол), скруглённая
    cx, cy = 0.46, 0.66
    out.append(box("jerrycan", (0.17, 0.3, 0.4), (cx, cy, DECK_TOP + 0.2), m["paint"], (0, 0, math.radians(-6))))
    for k in (-1, 1):
        out.append(box(f"jerry_x{k}", (0.012, 0.26, 0.03), (cx + 0.086, cy, DECK_TOP + 0.2), m["paint"], (math.radians(35 * k), 0, math.radians(-6))))
    out.append(cyl("jerry_cap", 0.025, 0.04, (cx, cy + 0.1, DECK_TOP + 0.42), m["rust"]))
    for k in range(3):
        out.append(box(f"jerry_handle{k}", (0.03, 0.03, 0.06), (cx, cy - 0.1 + k * 0.08, DECK_TOP + 0.43), m["paint"]))
    # навесной замок на ящике
    out.append(box("hasp", (0.04, 0.008, 0.07), (0.42, -0.877, DECK_TOP + 0.17), m["steel"], (0, 0, math.radians(4))))
    out.append(box("padlock", (0.05, 0.022, 0.045), (0.42, -0.868, DECK_TOP + 0.12), m["steel"], (0, 0, math.radians(4))))
    out.append(torus("padlock_shackle", 0.016, 0.004, (0.42, -0.868, DECK_TOP + 0.15), m["steel"], ROT_Y, (16, 6)))
    # термос у брезента
    out.append(cyl("thermos", 0.04, 0.3, (-0.46, 0.2, DECK_TOP + 0.15), m["paint2"]))
    out.append(cyl("thermos_cup", 0.045, 0.06, (-0.46, 0.2, DECK_TOP + 0.33), m["steel"]))
    # моток верёвки на штанге фонаря
    out.append(torus("rope_coil", 0.1, 0.014, (-SILL_X - 0.05, 0.99, DECK_TOP + 0.75), m["canvas"], (0, math.radians(90), 0), (24, 8)))
    out.append(torus("rope_coil2", 0.095, 0.014, (-SILL_X - 0.05, 1.0, DECK_TOP + 0.74), m["canvas"], (0, math.radians(84), 0), (24, 8)))
    # тряпка, перекинутая через поручень
    rag = box("rag", (0.006, 0.18, 0.32), (-SILL_X - 0.025, -0.45, DECK_TOP + 0.4), m["canvas"], round_edges=False)
    dent(rag, 0.02, 5, 3)
    out.append(rag)


# ============================================================================ СЛОЙ 7: повреждения

def layer7_damage(m, body_parts):
    # вмятины на листовом металле
    for o in body_parts:
        if o and o.name in ("gear_guard", "toolbox", "toolbox_lid", "buffer_plate1", "buffer_plate-1", "plank_sheet"):
            dent(o, 0.006 if o.name != "toolbox" else 0.008, 3, hash(o.name) % 7)
    holes = []
    # пулевые отверстия: в кожухе шестерни и боковине ящика (тёмные кольца с вывороченным краем)
    for (x, y, z, rot) in ((0.343, 0.55, WHEEL_R + 0.15, ROT_X), (0.343, 0.66, WHEEL_R + 0.08, ROT_X),
                           (0.42, -0.877, DECK_TOP + 0.05, ROT_Y), (0.55, -0.9, DECK_TOP + 0.13, ROT_Y)):
        holes.append(cyl(f"hole{x}{y}{z}", 0.007, 0.004, (x, y, z), m["tape"], rot, 10))
        holes.append(torus(f"hole_lip{x}{y}{z}", 0.009, 0.0025, (x, y, z), m["rust"], rot, (12, 6)))
    # расщеп обломанной доски
    for k in range(4):
        holes.append(cone(f"splinter{k}", 0.012, 0.0, 0.08 + k * 0.02,
                          (-0.6 + 0.12 + k * 0.012, 0.98 - 0.08 + k * 0.05, DECK_TOP - 0.02),
                          m["wood"], (0, math.radians(-90), math.radians(rnd.uniform(-20, 20))), 6))
    return holes


# ============================================================================ СЛОЙ 8: самодельный свет

def headlamp(prefix, loc, facing, m, out):
    """Старая автомобильная фара: корпус-полусфера, хромированный (ржавый) обод, стекло, кронштейн."""
    x, y, z = loc
    rot = (math.radians(-90 * facing), 0, 0)         # ось фары вдоль ±Y
    out.append(sphere(f"{prefix}_body", 0.1, (x, y - facing * 0.03, z), m["paint"], (1, 0.75, 1), (24, 14)))
    out.append(torus(f"{prefix}_rim", 0.095, 0.012, (x, y + facing * 0.035, z), m["steel"], ROT_Y, (32, 8)))
    out.append(cyl(f"{prefix}_glass", 0.088, 0.012, (x, y + facing * 0.04, z), m["glass"], ROT_Y, 32))
    out.append(box(f"{prefix}_bracket", (0.04, 0.12, 0.012), (x, y - facing * 0.08, z - 0.09), m["steel"]))
    out.append(cyl(f"{prefix}_stem", 0.012, 0.09, (x, y - facing * 0.03, z - 0.06), m["steel"]))
    out.append(cyl(f"{prefix}_tape", 0.016, 0.03, (x, y - facing * 0.03, z - 0.07), m["tape"]))


def wire(prefix, pts, m, out, r=0.006):
    """Провод по точкам + обмотки изолентой на изгибах."""
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        mid = [(a[k] + b[k]) / 2 for k in range(3)]
        d = [b[k] - a[k] for k in range(3)]
        ln = math.sqrt(sum(c * c for c in d))
        if ln < 1e-4:
            continue
        o = cyl(f"{prefix}{i}", r, ln, mid, m["tape"], (0, 0, 0), 6)
        # повернуть ось Z цилиндра вдоль d
        import mathutils
        o.rotation_mode = "QUATERNION"
        o.rotation_quaternion = mathutils.Vector((0, 0, 1)).rotation_difference(mathutils.Vector(d).normalized())
        bpy.ops.object.select_all(action="DESELECT")
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
        out.append(o)
        out.append(cyl(f"{prefix}_wrap{i}", r * 2.2, 0.03, b, m["tape"], (0, 0, 0), 8))


def layer8_lights(m, out):
    # динамо-машина над протектором заднего левого колеса
    dx, dy = -HALF, -AXLE_Y + 0.12
    out.append(box("dyn_bracket", (0.22, 0.05, 0.012), (-SILL_X - 0.08, dy, DECK_TOP - 0.04), m["rust"]))
    out.append(box("dyn_arm", (0.012, 0.05, 0.14), (dx + 0.03, dy, DECK_TOP - 0.1), m["rust"]))
    out.append(cyl("dyn_body", 0.035, 0.11, (dx, dy, 2 * WHEEL_R + 0.09), m["paint2"]))
    out.append(cyl("dyn_cap", 0.028, 0.02, (dx, dy, 2 * WHEEL_R + 0.155), m["steel"]))
    out.append(cyl("dyn_roller", 0.016, 0.03, (dx, dy, 2 * WHEEL_R + 0.02), m["steel"], (0, 0, 0), 12))
    out.append(box("dyn_spring", (0.008, 0.008, 0.08), (dx + 0.04, dy, 2 * WHEEL_R + 0.07), m["steel"], (0, math.radians(20), 0)))
    # фары: передняя справа на торце, задняя слева
    fl = (0.45, 1.17 + 0.12, DECK_TOP - 0.02)
    bl = (-0.45, -1.17 - 0.12, DECK_TOP - 0.02)
    headlamp("hl_front", fl, 1, m, out)
    headlamp("hl_back", bl, -1, m, out)
    # лампочка в клетке под осью коромысла
    bz = PIVOT_Z - 0.3
    out.append(cyl("bulb_socket", 0.018, 0.04, (0, 0.0, bz + 0.05), m["tape"]))
    out.append(sphere("bulb_glass", 0.032, (0, 0.0, bz), m["glass"], (1, 1, 1.25), (16, 10)))
    for k in range(4):
        a = k * math.pi / 2
        out.append(box(f"bulb_cage{k}", (0.004, 0.004, 0.11), (math.cos(a) * 0.045, math.sin(a) * 0.045, bz + 0.0), m["steel"]))
    out.append(torus("bulb_cage_ring", 0.045, 0.003, (0, 0, bz - 0.05), m["steel"], (0, 0, 0), (16, 6)))
    out.append(cyl("bulb_cord", 0.004, 0.24, (0, 0, bz + 0.19), m["tape"], (0, 0, 0), 6))
    # провода от динамо по раме к фарам и вверх по стойке к лампочке
    z = DECK_TOP - 0.06
    wire("w_front", [(dx, dy, 2 * WHEEL_R + 0.1), (-SILL_X - 0.02, dy, z), (-SILL_X - 0.02, 1.12, z), (fl[0], 1.12, z), (fl[0], fl[1] - 0.1, fl[2])], m, out)
    wire("w_back", [(-SILL_X - 0.02, dy, z), (-SILL_X - 0.02, -1.12, z), (bl[0], -1.12, z), (bl[0], bl[1] + 0.1, bl[2])], m, out)
    wire("w_bulb", [(-SILL_X - 0.02, -0.42, z), (-0.17, -0.42, DECK_TOP + 0.02), (-0.17, -0.05, PIVOT_Z - 0.1), (0, 0, bz + 0.31)], m, out)


# ============================================================================ коромысло (слой 2+3)

def build_lever(m):
    lv = []
    # стальной двутавр
    lv.append(box("beam_web", (0.012, 2.0, 0.11), (0, 0, PIVOT_Z), m["paint2"]))
    for sz in (-1, 1):
        lv.append(box(f"beam_fl{sz}", (0.07, 2.0, 0.01), (0, 0, PIVOT_Z + sz * 0.05), m["paint2"]))
    lv.append(box("beam_hub", (0.09, 0.22, 0.14), (0, 0, PIVOT_Z), m["rust"]))
    bolt_row("hubbolt", (0.046, -0.08, PIVOT_Z + 0.04), (0.046, 0.08, PIVOT_Z + 0.04), 3, "x", m["steel"], lv)
    for sy in (-1, 1):
        y = sy * 1.0
        lv.append(cyl(f"handle{sy}", 0.02, 0.96, (0, y, PIVOT_Z), m["steel"], ROT_X, 10))
        lv.append(box(f"handle_mount{sy}", (0.08, 0.06, 0.12), (0, y, PIVOT_Z), m["rust"]))
        for sx in (-1, 1):
            # ручки обмотаны изолентой, одна обмотка размоталась
            lv.append(cyl(f"grip{sy}{sx}", 0.028, 0.22, (sx * 0.36, y, PIVOT_Z), m["tape"], ROT_X, 10))
        if sy > 0:  # размотавшийся хвост изоленты только на одной ручке
            lv.append(box("tape_tail", (0.002, 0.025, 0.07), (0.47, y, PIVOT_Z - 0.045), m["tape"], (0, math.radians(10), 0)))
    lever = join(lv, "lever")
    set_origin(lever, (0, 0, PIVOT_Z))
    uv_cube(lever, 0.6)
    smooth(lever)
    selection(lever, "lever")
    return lever


# ============================================================================ сборка

def build(outdir, tex_dir, save_fn, reset_fn):
    global TEX_DIR
    TEX_DIR = tex_dir
    reset_fn()
    m = materials()

    body_parts, wood, metal = [], [], []
    layer1_frame(m, body_parts)                 # СЛОЙ 1
    layer1_deck(m, wood, metal)
    layer2_running_gear(m, body_parts)          # СЛОЙ 2
    layer2_drive(m, body_parts)
    layer2_aframe(m, body_parts)
    layer2_brake(m, body_parts)
    layer2_couplers(m, body_parts)
    layer3_wear(m, body_parts)                  # СЛОЙ 3
    props = []
    layer3_props(m, props)
    layer5_fasteners(m, body_parts)             # СЛОЙ 5
    layer6_life(m, props)                       # СЛОЙ 6
    damage = layer7_damage(m, body_parts + props + metal)   # СЛОЙ 7
    layer8_lights(m, props)                     # СЛОЙ 8

    body = join(body_parts + wood + metal + props + damage, "body")
    uv_cube(body, 0.8)                          # СЛОЙ 4
    plate = layer3_plate(m)
    body = join([body, plate], "body")
    smooth(body)
    selection(body, "body")

    for name, x, y in (("wheel_fl", -HALF, AXLE_Y), ("wheel_fr", HALF, AXLE_Y),
                       ("wheel_rl", -HALF, -AXLE_Y), ("wheel_rr", HALF, -AXLE_Y)):
        wheel(name, x, y, m)
    build_lever(m)

    mem_point("mem_lever_axis_1", (-0.25, 0, PIVOT_Z))
    mem_point("mem_lever_axis_2", (0.25, 0, PIVOT_Z))
    mem_point("mem_axle_front_1", (-HALF, AXLE_Y, WHEEL_R))
    mem_point("mem_axle_front_2", (HALF, AXLE_Y, WHEEL_R))
    mem_point("mem_axle_rear_1", (-HALF, -AXLE_Y, WHEEL_R))
    mem_point("mem_axle_rear_2", (HALF, -AXLE_Y, WHEEL_R))
    mem_point("mem_seat_driver", (0, -0.80, DECK_TOP))
    # точки света (скрипт крепит к ним фары и лампочку)
    mem_point("mem_light_front", (0.45, 1.17 + 0.12 + 0.05, DECK_TOP - 0.02))
    mem_point("mem_light_front_dir", (0.45, 1.17 + 0.12 + 1.05, DECK_TOP - 0.06))
    mem_point("mem_light_back", (-0.45, -1.17 - 0.12 - 0.05, DECK_TOP - 0.02))
    mem_point("mem_light_back_dir", (-0.45, -1.17 - 0.12 - 1.05, DECK_TOP - 0.06))
    mem_point("mem_light_bulb", (0, 0, PIVOT_Z - 0.3))

    geo = box("geometry_deck", (1.34, 2.3, 0.30), (0, 0, DECK_TOP - 0.15), m["wood"])
    geo.display_type = "WIRE"

    meshes = [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("geometry")]
    print(f"[Drezina] handcar faces LOD0: {sum(len(o.data.polygons) for o in meshes)}")
    save_fn(outdir, "handcar")

    # упрощённые LOD (selections сохраняются)
    for lod, ratio in ((1, 0.4), (2, 0.15)):
        for o in meshes:
            mod = o.modifiers.new("decimate", "DECIMATE")
            mod.ratio = ratio
            bpy.context.view_layer.objects.active = o
            bpy.ops.object.modifier_apply(modifier=mod.name)
        print(f"[Drezina] handcar faces LOD{lod}: {sum(len(o.data.polygons) for o in meshes)}")
        save_fn(outdir, f"handcar_lod{lod}")
    bpy.ops.wm.open_mainfile(filepath=os.path.join(outdir, "handcar.blend"))
