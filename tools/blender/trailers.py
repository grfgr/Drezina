"""
Прицепы к мотодрезине (та же рама, настил и колёса, что у мотодрезины):

  trailer_passenger  две лавки вдоль, спинками друг к другу: 4 пассажира, по двое лицом в каждую сторону.
  trailer_cargo      4 бочки, по 2 с каждой стороны; каждая бочка — отдельное хранилище
                     (невидимые вложения DrezinaBarrel1..4, их видно в инвентаре прицепа).
  trailer_barrel     модель бочки-вложения (для картинки в инвентаре).

Оба — машины DayZ без водителя (CarScript): ступицы и прокси колёс Нивы — как у мотодрезины,
иначе машина не создаётся. Сзади красный фонарь (выделение light_brake_1_2): горит, когда водитель
ведущей мотодрезины тормозит. Ориентация как у мотодрезины: в конце всё разворачивается на 180°.
"""
import math
import os

import bpy

import handcar_zone as hz
import motor_handcar as mh
from handcar_zone import box, cyl, sphere, torus, join, uv_cube, smooth, selection, mem_point, ROT_X, ROT_Y

DECK = hz.DECK_TOP
SEAT_H = DECK + 0.44
P = "\\dz\\vehicles\\wheeled\\proxies\\"
W = "\\dz\\vehicles\\wheeled\\offroadhatchback\\proxy\\nivawheel"
# пассажиры: (x, y, взгляд по x)
SEATS = [(-0.3, 0.45, -1), (-0.3, -0.45, -1), (0.3, 0.45, 1), (0.3, -0.45, 1)]
# бочки грузового прицепа: (x, y)
BARRELS = [(-0.38, 0.5), (-0.38, -0.5), (0.38, 0.5), (0.38, -0.5)]


def chassis(m):
    """Рама, настил, ходовая, тормоза, сцепки, износ — как у мотодрезины."""
    body, wood, metal = [], [], []
    hz.layer1_frame(m, body)
    hz.layer1_deck(m, wood, metal)
    hz.layer2_running_gear(m, body)
    for sy in (-1, 1):
        yy = sy * 1.17
        body.append(box(f"buffer_plate{sy}", (0.2, 0.012, 0.14), (0, yy, DECK - 0.12), m["steel"]))
        body.append(box(f"hook{sy}", (0.03, 0.12, 0.03), (0, yy + sy * 0.06, DECK - 0.15), m["steel"]))
        body.append(box(f"hook_tip{sy}", (0.03, 0.03, 0.06), (0, yy + sy * 0.11, DECK - 0.13), m["steel"]))
    # передняя сцепка: дышло к мотодрезине
    body.append(box("drawbar", (0.06, 0.5, 0.05), (0, 1.4, DECK - 0.15), m["steel"]))
    body.append(torus("drawbar_eye", 0.04, 0.012, (0, 1.66, DECK - 0.15), m["steel"], (0, 0, 0), (16, 6)))
    hz.layer3_wear(m, body)
    mh.brakes_and_guards(m, body)
    return body + wood + metal


def rear_lamp(m, out, sel_parts):
    parts = []
    lz = DECK + 0.16
    hz.headlamp("tail", (0.0, -1.25, lz), -1, m, parts)
    for p in parts:
        out.append(p)
        if p.name.endswith("_glass"):
            sel_parts.append((p, "light_brake_1_2"))
    # фонарь на стойке, привинченной к торцевой балке (раньше висел в воздухе за рамой)
    out.append(box("tail_post", (0.06, 0.06, 0.3), (0.0, -1.17, DECK + 0.01), m["rust"]))
    out.append(box("tail_post_plate", (0.14, 0.012, 0.12), (0.0, -1.195, DECK - 0.08), m["steel"]))
    # катафоты на торцевой балке (раньше торчали над настилом)
    out.append(box("tail_reflector_l", (0.08, 0.012, 0.06), (-0.55, -1.205, DECK - 0.08), m["glass"]))
    out.append(box("tail_reflector_r", (0.08, 0.012, 0.06), (0.55, -1.205, DECK - 0.08), m["glass"]))


def passenger_benches(m, out):
    """Две лавки вдоль прицепа спинками друг к другу; ноги пассажиров — наружу, на подножку."""
    L = 1.9
    for sx in (-1, 1):
        x = sx * 0.3
        out.append(box(f"bench_seat{sx}", (0.42, L, 0.05), (x, 0, SEAT_H - 0.025), m["wood"]))
        for sy in (-0.45, 0.45):
            out.append(box(f"bench_cushion{sx}{sy}", (0.38, 0.55, 0.04), (x + sx * 0.01, sy, SEAT_H + 0.015), m["canvas"]))
        for dy in (-0.85, 0.0, 0.85):
            for dx in (-0.17, 0.17):
                out.append(box(f"bench_leg{sx}{dy}{dx}", (0.05, 0.05, SEAT_H - DECK - 0.05), (x + dx, dy, (SEAT_H + DECK) / 2 - 0.025), m["rust"]))
        # подножка вдоль борта — снаружи колёс и крыльев (раньше проходила сквозь колёса)
        out.append(box(f"footboard{sx}", (0.2, L + 0.3, 0.03), (sx * 1.0, 0, DECK - 0.12), m["wood"]))
        for dy in (-1.1, 0.0, 1.1):          # кронштейны там, где нет колёс: посередине и на концах
            out.append(box(f"footboard_bracket{sx}{dy}", (0.36, 0.05, 0.04), (sx * 0.84, dy, DECK - 0.1), m["rust"]))
            out.append(box(f"footboard_strut{sx}{dy}", (0.04, 0.05, 0.12), (sx * 0.68, dy, DECK - 0.06), m["rust"]))
    # общая спинка посередине: доски на стойках
    for k, z in enumerate((0.2, 0.4)):
        out.append(box(f"backrest{k}", (0.05, L, 0.13), (0, 0, SEAT_H + z), m["wood"]))
    for dy in (-0.9, 0.0, 0.9):
        out.append(box(f"backrest_post{dy}", (0.06, 0.06, 0.55), (0, dy, SEAT_H + 0.25), m["rust"]))
    # козырёк-перила на торцах
    for sy in (-1, 1):
        out.append(cyl(f"end_rail{sy}", 0.018, 1.2, (0, sy * 1.02, SEAT_H + 0.3), m["rust"], ROT_Y))
        for dx in (-0.6, 0.6):
            out.append(cyl(f"end_post{sy}{dx}", 0.016, 0.75, (dx, sy * 1.02, DECK + 0.37), m["rust"]))
    # мелочь: ящик под лавкой, брезент
    out.append(box("under_box", (0.3, 0.5, 0.25), (0.0, 0.6, DECK + 0.13), m["wood"]))
    out.append(box("tarp", (0.35, 0.4, 0.06), (-0.3, -0.8, SEAT_H + 0.05), m["canvas"], (0, 0, math.radians(8))))


def barrel(prefix, x, y, m, out, z0=None):
    z0 = DECK if z0 is None else z0
    out.append(cyl(f"{prefix}_body", 0.29, 0.86, (x, y, z0 + 0.43), m["paint2"], (0, 0, 0), 24))
    for k, z in enumerate((0.12, 0.43, 0.74)):
        out.append(torus(f"{prefix}_hoop{k}", 0.293, 0.013, (x, y, z0 + z), m["rust"], (0, 0, 0), (28, 6)))
    out.append(cyl(f"{prefix}_lid", 0.27, 0.02, (x, y, z0 + 0.865), m["rust"], (0, 0, 0), 24))
    out.append(cyl(f"{prefix}_bung", 0.03, 0.025, (x + 0.15, y, z0 + 0.88), m["steel"], (0, 0, 0), 10))


def cargo_barrels(m, out):
    for i, (x, y) in enumerate(BARRELS):
        barrel(f"barrel{i + 1}", x, y, m, out)
    # стойки и обвязка: бочки стоят в гнёздах, стянуты ремнями
    for sx in (-1, 1):
        out.append(cyl(f"strap_rail{sx}", 0.015, 2.0, (sx * 0.7, 0, DECK + 0.55), m["rust"], (math.radians(90), 0, 0)))
        for dy in (-0.95, 0.0, 0.95):
            out.append(cyl(f"strap_post{sx}{dy}", 0.018, 0.6, (sx * 0.7, dy, DECK + 0.3), m["rust"]))
        for y in (-0.5, 0.5):
            out.append(torus(f"strap{sx}{y}", 0.3, 0.01, (sx * 0.38, y, DECK + 0.6), m["leather"], (0, 0, 0), (28, 4)))
    out.append(box("divider", (0.05, 2.0, 0.5), (0, 0, DECK + 0.25), m["wood"]))
    for y in (-0.5, 0.5):
        out.append(box(f"chock{y}", (1.4, 0.05, 0.08), (0, y + 0.31, DECK + 0.04), m["wood"]))


def common_points():
    for name, x, y in (("wheel_1_1", -hz.HALF, hz.AXLE_Y), ("wheel_2_1", hz.HALF, hz.AXLE_Y),
                       ("wheel_1_2", -hz.HALF, -hz.AXLE_Y), ("wheel_2_2", hz.HALF, -hz.AXLE_Y)):
        mem_point(f"mem_{name}_damper_land", (x, y, hz.WHEEL_R))
        mem_point(f"mem_{name}_axis", (x, y, hz.WHEEL_R))
    mem_point("mem_axle_front_1", (-hz.HALF, hz.AXLE_Y, hz.WHEEL_R))
    mem_point("mem_axle_front_2", (hz.HALF, hz.AXLE_Y, hz.WHEEL_R))
    mem_point("mem_axle_rear_1", (-hz.HALF, -hz.AXLE_Y, hz.WHEEL_R))
    mem_point("mem_axle_rear_2", (hz.HALF, -hz.AXLE_Y, hz.WHEEL_R))
    mem_point("mem_light_reverse", (0.0, -1.36, DECK + 0.16))
    mem_point("mem_camera", (0, 0, 1.6))


def common_proxies_geo(m):
    mh.proxy("proxy_wheel_1", W, "wheel_1_1_proxy", (-hz.HALF, hz.AXLE_Y, hz.WHEEL_R), (0, 1, 0))
    mh.proxy("proxy_wheel_2", W, "wheel_1_2_proxy", (-hz.HALF, -hz.AXLE_Y, hz.WHEEL_R), (0, 1, 0))
    mh.proxy("proxy_wheel_3", W, "wheel_2_1_proxy", (hz.HALF, hz.AXLE_Y, hz.WHEEL_R), (0, 1, 0))
    mh.proxy("proxy_wheel_4", W, "wheel_2_2_proxy", (hz.HALF, -hz.AXLE_Y, hz.WHEEL_R), (0, 1, 0))
    mh.geo("geometry_chassis", (1.36, 2.4, 0.22), (0, 0, DECK - 0.11), "dmgZone_chassis", m)
    for name, x, y in (("1_1", -hz.HALF, hz.AXLE_Y), ("2_1", hz.HALF, hz.AXLE_Y),
                       ("1_2", -hz.HALF, -hz.AXLE_Y), ("2_2", hz.HALF, -hz.AXLE_Y)):
        mh.geo(f"geometry_hub_{name}", (0.1, 0.5, 0.5), (x, y, hz.WHEEL_R + 0.02), f"dmgZone_wheel_{name},wheel_{name}_damper_land", m)


def finish_model(outdir, name, save_fn, props, body, m):
    sel_parts = []
    rear_lamp(m, props, sel_parts)
    for g, sel in sel_parts:
        props.remove(g)
        uv_cube(g, 0.3)
        selection(g, sel)
    main = join(body + props, "body")
    uv_cube(main, 0.8)
    smooth(main)
    selection(main, "body")
    for wname, x, y in (("wheel_1_1", -hz.HALF, hz.AXLE_Y), ("wheel_2_1", hz.HALF, hz.AXLE_Y),
                        ("wheel_1_2", -hz.HALF, -hz.AXLE_Y), ("wheel_2_2", hz.HALF, -hz.AXLE_Y)):
        mh.rail_wheel(wname, x, y, m)
    import mathutils
    rot = mathutils.Matrix.Rotation(math.pi, 4, "Z")
    for o in bpy.data.objects:
        if o.parent is None:
            o.matrix_world = rot @ o.matrix_world
        if "proxy_fwd" in o:
            fx, fy, fz = o["proxy_fwd"]
            o["proxy_fwd"] = (-fx, -fy, fz)
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("geometry")]
    for o in meshes:
        ratio = 0.6 if o.name == "body" else (0.75 if o.name.startswith("wheel") else 1.0)
        if ratio < 1.0:
            mod = o.modifiers.new("decimate0", "DECIMATE")
            mod.ratio = ratio
            bpy.context.view_layer.objects.active = o
            bpy.ops.object.modifier_apply(modifier=mod.name)
    print(f"[Drezina] {name} faces LOD0: {sum(len(o.data.polygons) for o in meshes)}")
    save_fn(outdir, name)
    for lod, ratio in ((1, 0.4), (2, 0.15)):
        for o in meshes:
            mod = o.modifiers.new("decimate", "DECIMATE")
            mod.ratio = ratio
            bpy.context.view_layer.objects.active = o
            bpy.ops.object.modifier_apply(modifier=mod.name)
        save_fn(outdir, f"{name}_lod{lod}")


def build_passenger(outdir, save_fn, reset_fn):
    reset_fn()
    m = hz.materials()
    body = chassis(m)
    props = []
    passenger_benches(m, props)
    # экипаж: 4 пассажира лицом наружу
    for i, (x, y, fx) in enumerate(SEATS):
        n = i + 1
        mh.proxy(f"proxy_cargo{n}", P + "crew_cargo", f"crewCargo{n}", (x + fx * 0.02, y, SEAT_H + 0.03), (fx, 0, 0))
        mem_point(f"mem_pos_cargo{n}", (fx * 1.15, y, 0.05))
        mem_point(f"mem_pos_cargo{n}_dir", (fx * 0.5, y, 0.05))
        mh.geo(f"geometry_seat_cargo{n}", (0.42, 0.5, 0.45), (x, y, DECK + 0.22), f"seat_cargo{n}", m)
    common_points()
    common_proxies_geo(m)
    finish_model(outdir, "trailer_passenger", save_fn, props, body, m)


def build_cargo(outdir, save_fn, reset_fn):
    reset_fn()
    m = hz.materials()
    body = chassis(m)
    props = []
    cargo_barrels(m, props)
    for i, (x, y) in enumerate(BARRELS):
        mh.geo(f"geometry_barrel{i + 1}", (0.58, 0.58, 0.86), (x, y, DECK + 0.43), f"dmgZone_barrel{i + 1}", m)
    common_points()
    common_proxies_geo(m)
    finish_model(outdir, "trailer_cargo", save_fn, props, body, m)


def build_barrel_item(outdir, save_fn, reset_fn):
    reset_fn()
    m = hz.materials()
    parts = []
    barrel("b", 0, 0, m, parts, 0.0)
    o = join(parts, "trailer_barrel")
    uv_cube(o, 0.8)
    smooth(o)
    save_fn(outdir, "trailer_barrel")


def build(outdir, tex_dir, save_fn, reset_fn):
    hz.TEX_DIR = tex_dir
    build_passenger(outdir, save_fn, reset_fn)
    build_cargo(outdir, save_fn, reset_fn)
    build_barrel_item(outdir, save_fn, reset_fn)
