"""
Генерирует low-poly модели для мода Drezina:
  handcar   - ручная дрезина Sheffield (~1890): деревянная платформа, 4 колеса со спицами
              и стальным бандажом, А-образная стойка, коромысло с Т-образными ручками.
  rail_2m   - звено пути 2 м: два рельса (колея 1520 мм) и шпалы.
  dispenser - стойка выдачи дрезин: столб, навес, табличка.

Запуск:
  blender --background --python tools/blender/make_models.py -- <выходная папка>
  или (pip install bpy):  python tools/blender/make_models.py <выходная папка>

Результат: handcar.blend/.fbx, rail_2m.blend/.fbx, dispenser.blend/.fbx.
Названия объектов (lever, wheel_fl ... ) = named selections из data/model.cfg.
Пустышки (Empty) с префиксом "mem_" — точки Memory LOD (оси вращения, место водителя).
Оси координат: Blender Z-вверх, Y-вперёд (по ходу дрезины) -> в Object Builder это Y-вверх, Z-вперёд.
"""
import math
import os
import sys

import bpy

GAUGE = 1.520          # колея, м (метро/РЖД)
RAIL_TOP = 0.172       # высота головки рельса над низом шпалы
WHEEL_R = 0.36
DECK_TOP = 0.62        # верх пола дрезины над головкой рельса (совпадает с DECK_HEIGHT в скрипте)


# ----------------------------------------------------------------------------- утилиты

def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def material(name, rgb, rough=0.8, metal=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = metal
    return mat


def box(name, size, loc, mat, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(mat)
    return o


def cyl(name, r, depth, loc, mat, rot=(0, 0, 0), verts=16):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(mat)
    return o


def tube(name, r_out, r_in, width, loc, mat, segments=24):
    """Кольцо (труба) с осью X: стальной бандаж колеса / реборда."""
    import bmesh
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    rings = []
    for x in (-width / 2, width / 2):
        for r in (r_out, r_in):
            rings.append([bm.verts.new((x, math.cos(2 * math.pi * i / segments) * r,
                                        math.sin(2 * math.pi * i / segments) * r)) for i in range(segments)])
    o_a, i_a, o_b, i_b = rings
    for i in range(segments):
        j = (i + 1) % segments
        bm.faces.new((o_a[i], o_a[j], o_b[j], o_b[i]))  # наружная
        bm.faces.new((i_a[j], i_a[i], i_b[i], i_b[j]))  # внутренняя
        bm.faces.new((o_a[j], o_a[i], i_a[i], i_a[j]))  # торец A
        bm.faces.new((o_b[i], o_b[j], i_b[j], i_b[i]))  # торец B
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    o = bpy.data.objects.new(name, mesh)
    o.location = loc
    bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(mat)
    return o


def join(objs, name):
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
    """Перенос origin объекта в точку (для корректного вращения в Blender-превью)."""
    cur = bpy.context.scene.cursor.location.copy()
    bpy.context.scene.cursor.location = point
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
    bpy.context.scene.cursor.location = cur


def mem_point(name, loc):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = "SPHERE"
    e.empty_display_size = 0.03
    e.location = loc
    bpy.context.scene.collection.objects.link(e)
    return e


def add_selection_group(obj, name):
    """Vertex group = named selection (для Arma/DayZ-экспортёров)."""
    vg = obj.vertex_groups.new(name=name)
    vg.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")


def save(outdir, name):
    os.makedirs(outdir, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(outdir, name + ".blend"))
    bpy.ops.export_scene.fbx(filepath=os.path.join(outdir, name + ".fbx"), apply_unit_scale=True,
                             object_types={"MESH", "EMPTY"}, add_leaf_bones=False)


# ----------------------------------------------------------------------------- материалы

def mats():
    return {
        "wood": material("drezina_wood", (0.42, 0.27, 0.15)),
        "wood_dark": material("drezina_wood_dark", (0.25, 0.16, 0.09)),
        "steel": material("drezina_steel", (0.35, 0.35, 0.36), rough=0.45, metal=1.0),
        "iron": material("drezina_iron", (0.12, 0.12, 0.12), rough=0.6, metal=0.8),
        "rust": material("drezina_rust", (0.36, 0.2, 0.12), rough=0.9, metal=0.3),
        "sign": material("drezina_sign", (0.75, 0.62, 0.15)),
    }


# ----------------------------------------------------------------------------- дрезина

def wheel(name, x, y, m):
    """Колесо: деревянный центр со спицами + стальной бандаж с ребордой. Ось колеса = X."""
    rot = (0, math.radians(90), 0)
    parts = []
    parts.append(tube(name + "_tire", WHEEL_R, WHEEL_R - 0.035, 0.10, (x, y, WHEEL_R), m["steel"]))
    flange_x = x - math.copysign(0.055, x)  # реборда с внутренней стороны
    parts.append(tube(name + "_flange", WHEEL_R + 0.025, WHEEL_R - 0.035, 0.02, (flange_x, y, WHEEL_R), m["steel"]))
    # деревянный обод — кольцо, чтобы спицы было видно
    bpy.ops.mesh.primitive_torus_add(major_radius=WHEEL_R - 0.045, minor_radius=0.035, major_segments=24,
                                     minor_segments=6, location=(x, y, WHEEL_R), rotation=rot)
    felloe = bpy.context.active_object
    felloe.name = name + "_felloe"
    felloe.data.materials.append(m["wood"])
    parts.append(felloe)
    parts.append(cyl(name + "_hub", 0.07, 0.16, (x, y, WHEEL_R), m["iron"], rot, 12))
    spokes = 14
    for i in range(spokes):
        a = 2 * math.pi * i / spokes
        r = (WHEEL_R - 0.05) / 2 + 0.03
        parts.append(box(name + f"_spoke{i}", (0.03, 0.035, WHEEL_R - 0.08),
                         (x, y + math.sin(a) * r, WHEEL_R + math.cos(a) * r), m["wood_dark"], (-a, 0, 0)))
    o = join(parts, name)
    set_origin(o, (x, y, WHEEL_R))
    add_selection_group(o, name)
    return o


def build_handcar(outdir):
    reset_scene()
    m = mats()
    half = GAUGE / 2
    axle_y = 0.62
    static = []

    # рама и пол
    for sx in (-1, 1):
        static.append(box(f"sill_{sx}", (0.10, 2.10, 0.16), (sx * (half - 0.16), 0, DECK_TOP - 0.12), m["wood_dark"]))
    for i in range(9):
        y = -0.98 + i * 0.245
        static.append(box(f"plank_{i}", (1.24, 0.22, 0.04), (0, y, DECK_TOP - 0.02), m["wood"]))
    for sy in (-1, 1):
        static.append(box(f"endbeam_{sy}", (1.30, 0.12, 0.16), (0, sy * 1.05, DECK_TOP - 0.12), m["wood_dark"]))

    # оси и буксы
    for y in (-axle_y, axle_y):
        static.append(cyl(f"axle_{y}", 0.035, GAUGE + 0.1, (0, y, WHEEL_R), m["iron"], (0, math.radians(90), 0), 10))
        for sx in (-1, 1):
            static.append(box(f"box_{y}_{sx}", (0.10, 0.16, DECK_TOP - 0.2 - WHEEL_R + 0.07), (sx * (half - 0.16), y, (DECK_TOP - 0.2 + WHEEL_R - 0.07) / 2), m["iron"]))

    # шестерня на передней оси и кривошип (как на фото)
    static.append(cyl("gear_big", 0.20, 0.04, (0.25, axle_y, WHEEL_R), m["iron"], (0, math.radians(90), 0), 28))
    static.append(cyl("gear_small", 0.08, 0.05, (0.25, axle_y - 0.26, WHEEL_R + 0.12), m["iron"], (0, math.radians(90), 0), 12))

    # А-образная стойка
    pivot_z = DECK_TOP + 1.05
    for sx in (-0.18, 0.18):
        for sy in (-1, 1):
            a = math.atan2(0.42, 1.05)
            static.append(box(f"frame_{sx}_{sy}", (0.07, 0.07, 1.14), (sx, sy * 0.21, DECK_TOP + 0.52),
                              m["wood_dark"], (sy * a, 0, 0)))
        static.append(box(f"brace_{sx}", (0.05, 0.62, 0.05), (sx, 0, DECK_TOP + 0.35), m["wood_dark"]))
    static.append(cyl("pivot_pin", 0.03, 0.50, (0, 0, pivot_z), m["iron"], (0, math.radians(90), 0), 10))
    # тяга от коромысла к шестерне
    static.append(box("conrod", (0.03, 0.03, 0.85), (0.25, 0.28, DECK_TOP + 0.45), m["iron"], (math.radians(-18), 0, 0)))

    body = join(static, "body")
    add_selection_group(body, "body")

    # колёса (отдельные selections)
    wheels = []
    for name, x, y in (("wheel_fl", -half, axle_y), ("wheel_fr", half, axle_y),
                       ("wheel_rl", -half, -axle_y), ("wheel_rr", half, -axle_y)):
        wheels.append(wheel(name, x, y, m))

    # коромысло (качается вокруг поперечной оси на вершине стойки)
    lv = []
    lv.append(box("beam", (0.08, 2.0, 0.10), (0, 0, pivot_z), m["wood"]))
    lv.append(box("beam_strap", (0.10, 0.5, 0.12), (0, 0, pivot_z), m["iron"]))
    for sy in (-1, 1):
        lv.append(cyl(f"handle_{sy}", 0.022, 0.95, (0, sy * 1.0, pivot_z), m["iron"], (0, math.radians(90), 0), 10))
        for sx in (-1, 1):
            lv.append(cyl(f"grip_{sy}_{sx}", 0.032, 0.20, (sx * 0.38, sy * 1.0, pivot_z), m["wood_dark"],
                          (0, math.radians(90), 0), 10))
    lever = join(lv, "lever")
    set_origin(lever, (0, 0, pivot_z))
    add_selection_group(lever, "lever")

    # memory LOD
    mem_point("mem_lever_axis_1", (-0.25, 0, pivot_z))
    mem_point("mem_lever_axis_2", (0.25, 0, pivot_z))
    mem_point("mem_axle_front_1", (-half, axle_y, WHEEL_R))
    mem_point("mem_axle_front_2", (half, axle_y, WHEEL_R))
    mem_point("mem_axle_rear_1", (-half, -axle_y, WHEEL_R))
    mem_point("mem_axle_rear_2", (half, -axle_y, WHEEL_R))
    mem_point("mem_seat_driver", (0, -0.80, DECK_TOP))

    # простая геометрия для Geometry LOD (коробка платформы)
    geo = box("geometry_deck", (1.30, 2.2, 0.30), (0, 0, DECK_TOP - 0.15), m["wood"])
    geo.display_type = "WIRE"

    save(outdir, "handcar")
    return body, wheels, lever


# ----------------------------------------------------------------------------- рельсы

def build_rail(outdir):
    reset_scene()
    m = mats()
    parts = []
    length = 2.0
    half = GAUGE / 2
    for i in range(3):
        y = -0.66 + i * 0.66
        parts.append(box(f"sleeper_{i}", (2.6, 0.24, 0.15), (0, y, 0.075), m["wood_dark"]))
    for sx in (-1, 1):
        x = sx * (half + 0.036)
        parts.append(box(f"foot_{sx}", (0.13, length, 0.012), (x, 0, 0.156), m["rust"]))
        parts.append(box(f"web_{sx}", (0.02, length, 0.11), (x, 0, 0.21), m["rust"]))
        parts.append(box(f"head_{sx}", (0.072, length, 0.035), (x, 0, RAIL_TOP + 0.08), m["steel"]))
    rail = join(parts, "rail")
    # origin = на уровне головки рельса по центру колеи: туда сервер ставит точку трассы
    set_origin(rail, (0, 0, RAIL_TOP + 0.0975))
    rail.location = (0, 0, 0)
    add_selection_group(rail, "rail")
    save(outdir, "rail_2m")
    return rail


# ----------------------------------------------------------------------------- станция выдачи

def build_dispenser(outdir):
    reset_scene()
    m = mats()
    parts = []
    parts.append(box("base", (1.2, 1.2, 0.15), (0, 0, 0.075), m["wood_dark"]))
    for sx in (-0.5, 0.5):
        parts.append(box(f"post_{sx}", (0.12, 0.12, 2.4), (sx, 0, 1.2), m["wood_dark"]))
    parts.append(box("roof", (1.5, 0.9, 0.06), (0, 0, 2.45), m["wood"], (math.radians(8), 0, 0)))
    parts.append(box("sign", (1.0, 0.05, 0.35), (0, -0.08, 2.05), m["sign"]))
    parts.append(box("lever_box", (0.35, 0.25, 0.9), (0, -0.05, 0.6), m["iron"]))
    parts.append(cyl("lever_handle", 0.025, 0.45, (0.12, -0.18, 1.2), m["steel"], (math.radians(20), 0, 0), 8))
    disp = join(parts, "dispenser")
    add_selection_group(disp, "dispenser")
    save(outdir, "dispenser")
    return disp


def main():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = argv[1:]
    outdir = os.path.abspath(argv[0] if argv else "build_models")
    build_handcar(outdir)
    build_rail(outdir)
    build_dispenser(outdir)
    print("[Drezina] models written to", outdir)


if __name__ == "__main__":
    main()
