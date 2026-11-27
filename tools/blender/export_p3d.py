"""
Экспорт моделей Drezina из .blend (результат make_models.py) прямо в .p3d (MLOD — формат,
который сохраняет Object Builder). Object Builder больше не нужен: Addon Builder сам бинаризует
эти файлы при упаковке PBO.

Формат и оси — как у проверенного в игре экспортёра мода КПК (grfgr/KPK, source/models/write_p3d5.py):
  Blender (x, y, z), Z вверх  ->  P3D (x, z, y), Y вверх; порядок вершин граней сохраняется.

Что попадает в .p3d:
  Resolution LOD 0..3   видимая модель (+ файлы <имя>_lod1/2/3.blend, если есть)
                        named selections = vertex groups (lever, wheel_fl, ...)
                        текстуры/материалы = свойства материала dayz_texture / dayz_rvmat
  Geometry (1e13)       объекты geometry_* — каждый бокс отдельная компонента, масса, autocenter = 0
  View / Fire Geometry  те же боксы
  Roadway (3e15)        верхние грани боксов геометрии (по ним ходят)
  Memory (1e15)         пустышки mem_*  ->  точки; mem_axle_front_1 и _2 — одна selection "axle_front"
  Shadow (10000)        только у дрезины: коробка по габаритам

Запуск (внутри Blender):
  blender --background --python tools/blender/export_p3d.py -- build_models Drezina/data
"""
import math
import os
import re
import struct
import sys

import bpy

# модель -> (масса, есть ли тень)
# только картинка (без геометрии) -> из какого .blend
VIS_MODELS = {"trailer_passenger_vis": "trailer_passenger", "trailer_cargo_vis": "trailer_cargo"}

MODELS = {
    "handcar": (227.0, True),
    "motor_handcar": (380.0, True),
    "trailer_passenger": (300.0, True),
    "trailer_cargo": (320.0, True),
    "trailer_barrel": (30.0, False),
    "drezina_module_bench": (25.0, False),
    "drezina_module_barrels": (45.0, False),
    "rail_10m": (2000.0, False),
    "rail_2m": (400.0, False),
    "rail_1m": (200.0, False),
    "dispenser": (500.0, False),
    "tunnel_lamp": (2.0, False),
    "alarm_lamp": (2.0, False),
    "tunnel_10m": (20000.0, False),
    "tunnel_10m_tile": (20000.0, False),
    "tunnel_10m_b": (20000.0, False),
    "tunnel_10m_c": (20000.0, False),
    "tunnel_10m_d": (20000.0, False),
    "tunnel_10m_e": (20000.0, False),
    "tunnel_10m_f": (20000.0, False),
    "tunnel_10m_g": (20000.0, False),
    "tunnel_2m": (4000.0, False),
    "junction_hall": (90000.0, False),
    "junction_hall_tee": (90000.0, False),
    "junction_wall": (3000.0, False),
    "junction_portal": (8000.0, False),
    "metro_station": (50000.0, False),
    "bunker_entrance": (30000.0, False),
    "bunker_inner_door": (3000.0, False),
    "bunker_stairs": (30000.0, False),
    "bunker_corridor": (8000.0, False),
}
LOD_RES = [1.0, 4.0, 10.0, 25.0]

# Материал граней в Geometry / Fire Geometry / Roadway: по нему игра выбирает звук шагов,
# следы попаданий и пробиваемость (ванильные penetration-rvmat ссылаются на свой .bisurf).
# ванильный материал пола бункера Ливонии: по нему в бункере звучат шаги по бетону
# текстура граней Roadway — тоже ванильная из бункера (поверхность для шагов может браться по текстуре)
# Звук шагов: игра выбирает поверхность из CfgSurfaces (DZ_Surfaces) по началу ИМЕНИ ФАЙЛА текстуры
# граней Roadway LOD (files="concrete_int*" и т.п.), без материала на этих гранях.
ROADWAY_DIR = "Drezina\\data\\textures\\"
ROADWAY_TEX = ROADWAY_DIR + "concrete_int_drezina_co.paa"
ROADWAY_BY_MODEL = {
    "bunker_stairs": ROADWAY_DIR + "concrete_stairs_int_drezina_co.paa",
    "handcar": ROADWAY_DIR + "wood_planks_int_drezina_co.paa",
    "motor_handcar": ROADWAY_DIR + "metal_thick_int_drezina_co.paa",
    "trailer_passenger": ROADWAY_DIR + "metal_thick_int_drezina_co.paa",
    "trailer_cargo": ROADWAY_DIR + "metal_thick_int_drezina_co.paa",
    "trailer_barrel": ROADWAY_DIR + "metal_thick_int_drezina_co.paa",
    "drezina_module_bench": ROADWAY_DIR + "wood_planks_int_drezina_co.paa",
    "drezina_module_barrels": ROADWAY_DIR + "metal_thick_int_drezina_co.paa",
}
SURF_CONCRETE = "dz\\structures_bliss\\underground\\storage\\data\\underground_storage_big_floor.rvmat"
SURF_METAL = "dz\\data\\data\\penetration\\metal_plate.rvmat"
SURF_WOOD = "dz\\data\\data\\penetration\\wood.rvmat"
SURFACE = {
    "handcar": SURF_WOOD, "motor_handcar": SURF_METAL, "trailer_passenger": SURF_METAL, "trailer_cargo": SURF_METAL, "trailer_barrel": SURF_METAL, "drezina_module_bench": SURF_WOOD, "drezina_module_barrels": SURF_METAL, "dispenser": SURF_CONCRETE, "tunnel_lamp": SURF_CONCRETE, "alarm_lamp": SURF_CONCRETE,
    "rail_10m": SURF_CONCRETE, "rail_2m": SURF_CONCRETE, "rail_1m": SURF_CONCRETE,
}


# ============================================================================ запись MLOD

def asciiz(s):
    return s.encode("ascii", "replace") + b"\0"


def tag(name, data):
    return b"\1" + asciiz(name) + struct.pack("<I", len(data)) + data


def prop(name, value):
    return tag("#Property#", name.encode().ljust(64, b"\0") + value.encode().ljust(64, b"\0"))


def selection_tag(name, n_points, n_faces, points, faces):
    pw = bytearray(n_points)
    fw = bytearray(n_faces)
    for i in points:
        pw[i] = 1
    for i in faces:
        fw[i] = 1
    return tag(name, bytes(pw) + bytes(fw))


def lod_bytes(points, normals, faces, resolution, taggs=b""):
    """faces: [([(point, normal, u, v) x3..4], texture, material)]"""
    b = bytearray()
    b += b"P3DM" + struct.pack("<IIIIII", 28, 256, len(points), len(normals), len(faces), 0)
    for p in points:
        b += struct.pack("<fffI", p[0], p[1], p[2], 0)
    for n in normals:
        b += struct.pack("<fff", n[0], n[1], n[2])
    for verts, tex, mat in faces:
        b += struct.pack("<I", len(verts))
        for i in range(4):
            pi, ni, u, v = verts[i] if i < len(verts) else (0, 0, 0.0, 0.0)
            b += struct.pack("<IIff", pi, ni, u, v)
        b += struct.pack("<I", 0)
        b += asciiz(tex) + asciiz(mat)
    b += b"TAGG" + taggs + tag("#EndOfFile#", b"")
    b += struct.pack("<f", resolution)
    return bytes(b)


def to_p3d(v):
    return (v[0], v[2], v[1])


# ============================================================================ чтение сцены

def scene_parts():
    visual, geometry, memory = [], [], []
    for o in bpy.data.objects:
        if o.type == "MESH":
            (geometry if o.name.startswith("geometry") else visual).append(o)
        elif o.type == "EMPTY" and o.name.startswith("mem_"):
            memory.append(o)
    return visual, geometry, memory


def scene_proxies():
    return [o for o in bpy.data.objects if o.type == "EMPTY" and "proxy_path" in o]


def proxy_triangles(proxies):
    """Треугольник прокси: вершина в точке прокси, длинный катет (1 м) — вперёд, короткий (0.5 м) — вверх.
    Возвращает [(name_proxy, sel, (p0, p1, p2))] в осях P3D; номера прокси одного файла идут .001, .002 ..."""
    out = []
    counters = {}
    for e in sorted(proxies, key=lambda o: o.name):
        path = e["proxy_path"]
        counters[path] = counters.get(path, 0) + 1
        loc = e.matrix_world.translation
        fx, fy, fz = e["proxy_fwd"]
        p0 = (loc.x, loc.y, loc.z)
        # Треугольник прокси (проверено в игре на мотодрезине): длинный катет (1 м) — вверх,
        # короткий (0.5 м) — НАЗАД от направления «вперёд». С другим вариантом персонаж крутился при посадке.
        p1 = (loc.x, loc.y, loc.z + 1.0)
        p2 = (loc.x - fx * 0.5, loc.y - fy * 0.5, loc.z - fz * 0.5)
        name = "proxy:%s.%03d" % (path, counters[path])
        out.append((name, e["proxy_sel"], tuple(to_p3d(p) for p in (p0, p1, p2)), bool(e.get("proxy_visual", 0))))
    return out


def visual_lod(objs, resolution):
    points, normals, faces = [], [], []
    sel_points, sel_faces = {}, {}
    for o in objs:
        me = o.data
        mw = o.matrix_world
        nm = mw.to_3x3().inverted().transposed()
        base = len(points)
        for v in me.vertices:
            points.append(to_p3d(mw @ v.co))
        try:
            corner_n = [c.vector for c in me.corner_normals]          # Blender 4.1+
        except AttributeError:
            me.calc_normals_split()
            corner_n = [l.normal for l in me.loops]
        uv = me.uv_layers.active.data if me.uv_layers.active else None
        me.calc_loop_triangles()
        mats = []
        for slot in o.material_slots:
            m = slot.material
            mats.append((m.get("dayz_texture", "") if m else "", m.get("dayz_rvmat", "") if m else ""))
        groups = {g.index: g.name for g in o.vertex_groups}
        vgroups = {}
        for v in me.vertices:
            for ge in v.groups:
                if ge.weight > 0.5 and ge.group in groups:
                    vgroups.setdefault(groups[ge.group], set()).add(v.index)
        for name, vs in vgroups.items():
            sel_points.setdefault(name, set()).update(base + i for i in vs)
        for tri in me.loop_triangles:
            verts = []
            for li, vi in zip(tri.loops, tri.vertices):
                n = (nm @ corner_n[li]).normalized()
                # в MLOD P3D нормали хранятся инвертированными (как пишет Object Builder);
                # без минуса стороны, повёрнутые к фонарю, были чёрными, а освещалась изнанка
                normals.append(to_p3d(-n))
                u, v = (uv[li].uv if uv else (0.0, 0.0))
                verts.append((base + vi, len(normals) - 1, u, 1.0 - v))
            tex, mat = mats[tri.material_index] if tri.material_index < len(mats) else ("", "")
            fi = len(faces)
            faces.append((verts, tex, mat))
            for name, vs in vgroups.items():
                if all(vi in vs for vi in tri.vertices):
                    sel_faces.setdefault(name, set()).add(fi)
    taggs = b""
    for name in sel_points:
        taggs += selection_tag(name, len(points), len(faces), sel_points[name], sel_faces.get(name, ()))
    return lod_bytes(points, normals, faces, resolution, taggs), points


def box_faces(o, top_only=False):
    """Грани бокса геометрии в P3D (четырёхугольники)."""
    me = o.data
    mw = o.matrix_world
    pts = [to_p3d(mw @ v.co) for v in me.vertices]
    quads = []
    for poly in me.polygons:
        n = (mw.to_3x3() @ poly.normal)
        if top_only and n.z < 0.5:
            continue
        idx = list(poly.vertices)
        if len(idx) > 4:
            continue
        quads.append(idx)
    return pts, quads


def components_lod(geoms, resolution, mass=None, roadway=False, proxies=(), surface=SURF_CONCRETE, roadtex=None):
    points, faces = [], []
    taggs = b""
    comp = []
    extra = {}
    for o in geoms:
        pts, quads = box_faces(o, top_only=roadway)
        base = len(points)
        points += pts
        f0 = len(faces)
        for q in quads:
            faces.append(([(base + i, 0, 0.0, 0.0) for i in q], (roadtex or ROADWAY_TEX) if roadway else "", "" if roadway else surface))
        comp.append((range(base, base + len(pts)), range(f0, len(faces))))
        if not roadway and "sel" in o:
            for sname in str(o["sel"]).split(","):
                ps, fs = extra.setdefault(sname, (set(), set()))
                ps.update(range(base, base + len(pts)))
                fs.update(range(f0, len(faces)))
    geo_points = len(points)
    # прокси (экипаж) — только в View / Fire Geometry, без массы и вне компонент
    for pname, psel, tri, _vis in proxies:
        base = len(points)
        points += list(tri)
        fi = len(faces)
        faces.append(([(base, 0, 0.0, 0.0), (base + 1, 0, 0.0, 0.0), (base + 2, 0, 0.0, 0.0)], "", ""))
        for sname in (pname, psel):
            ps, fs = extra.setdefault(sname, (set(), set()))
            ps.update(range(base, base + 3))
            fs.add(fi)
    if not roadway:
        for k, (ps, fs) in enumerate(comp):
            taggs += selection_tag("Component%02d" % (k + 1), len(points), len(faces), ps, fs)
        for sname, (ps, fs) in extra.items():
            taggs += selection_tag(sname, len(points), len(faces), ps, fs)
    if mass is not None and points:
        taggs += tag("#Mass#", struct.pack("<%df" % len(points), *([mass / geo_points] * geo_points + [0.0] * (len(points) - geo_points))))
    if resolution == 1e13:
        taggs += prop("autocenter", "0")
    return lod_bytes(points, [(0.0, 1.0, 0.0)], faces, resolution, taggs)


def memory_lod(empties):
    points, groups = [], {}
    for e in empties:
        name = e.name[len("mem_"):]
        # пары точек оси: mem_axle_front_1 / _2 -> одна selection "axle_front"
        if re.match(r"^(lever_axis|axle_front|axle_rear|axle_third)_\d$", name):
            name = re.sub(r"_\d$", "", name)
        groups.setdefault(name, []).append(len(points))
        points.append(to_p3d(e.matrix_world.translation))
    taggs = b""
    for name, idx in groups.items():
        taggs += selection_tag(name, len(points), 0, idx, ())
    return lod_bytes(points, [(0.0, 1.0, 0.0)], [], 1e15, taggs)


def shadow_lod(points):
    xs, ys, zs = zip(*points)
    x0, y0, z0, x1, y1, z1 = min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)
    pts = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    quads = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (1, 2, 6, 5), (0, 4, 7, 3)]
    faces = []
    for q in quads:
        for tri in ((q[0], q[1], q[2]), (q[0], q[2], q[3])):
            faces.append(([(i, 0, 0.0, 0.0) for i in tri], "", ""))
    return lod_bytes(pts, [(0.0, 1.0, 0.0)], faces, 10000.0)


# ============================================================================ сборка одной модели

def export_model(src_dir, out_dir, name, mass, shadow, src_name=None, visonly=False):
    """visonly — только видимые LOD и точки (без Geometry/View/Fire/Roadway): «картинка», сквозь которую
    проходит взгляд игрока (видимый прицеп мотодрезины — места выбираются по самой дрезине)."""
    out_name = name
    name = src_name or name
    path = os.path.join(src_dir, name + ".blend")
    if not os.path.exists(path):
        print(f"[Drezina] пропуск {name}: нет {path}")
        return False
    lods = []
    bpy.ops.wm.open_mainfile(filepath=path)
    visual, geometry, memory = scene_parts()
    lod0, pts0 = visual_lod(visual, LOD_RES[0])
    lods.append(lod0)

    # LOD1..3 из соседних файлов
    for k in (1, 2, 3):
        lp = os.path.join(src_dir, f"{name}_lod{k}.blend")
        if os.path.exists(lp):
            bpy.ops.wm.open_mainfile(filepath=lp)
            v, _, _ = scene_parts()
            lods.append(visual_lod(v, LOD_RES[k])[0])

    # геометрия, память — из основного файла (открываем заново: объекты прошлого файла выгружены)
    bpy.ops.wm.open_mainfile(filepath=path)
    _, geometry, memory = scene_parts()
    prx = proxy_triangles(scene_proxies())
    if visonly:
        # крошечная «геометрия» внутри рамы: без неё движок центрирует модель по габаритам (прицеп уходил
        # под землю); такая не мешает ни взгляду, ни ходьбе
        bpy.ops.mesh.primitive_cube_add(size=0.02, location=(0, 0, 0.62))
        tiny = bpy.context.active_object
        tiny.name = "geometry_tiny"
        lods.append(components_lod([tiny], 1e13, 1.0))
    elif geometry:
        surf = SURFACE.get(name, SURF_CONCRETE)
        # viewonly (места прицепа): в Geometry есть (игра выбирает место по ней), но не в Roadway
        solid = [g for g in geometry if not g.get("viewonly")]
        lods.append(components_lod(geometry, 1e13, mass, surface=surf))
        lods.append(components_lod(geometry, 6e15, proxies=prx, surface=surf))
        lods.append(components_lod(geometry, 7e15, proxies=prx, surface=surf))
        lods.append(components_lod(solid, 3e15, roadway=True, surface=surf, roadtex=ROADWAY_BY_MODEL.get(name)))
    else:
        xs, ys, zs = zip(*pts0)
        bpy.ops.mesh.primitive_cube_add(size=1)
        c = bpy.context.active_object
        c.name = "geometry_auto"
        # обратно в оси Blender: P3D (x, y, z) = Blender (x, z, y)
        c.scale = (max(xs) - min(xs) or 0.05, max(zs) - min(zs) or 0.05, max(ys) - min(ys) or 0.05)
        c.location = ((max(xs) + min(xs)) / 2, (max(zs) + min(zs)) / 2, (max(ys) + min(ys)) / 2)
        bpy.ops.object.transform_apply(location=True, scale=True)
        lods.append(components_lod([c], 1e13, mass))
        lods.append(components_lod([c], 6e15))
        lods.append(components_lod([c], 7e15))
    if memory:
        lods.append(memory_lod(memory))
    if shadow:
        lods.append(shadow_lod(pts0))

    out = os.path.join(out_dir, out_name + ".p3d")
    with open(out, "wb") as f:
        f.write(b"MLOD" + struct.pack("<II", 257, len(lods)))
        for l in lods:
            f.write(l)
    print(f"[Drezina] {out}: LOD {len(lods)}")
    return True


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    src = os.path.abspath(argv[0] if argv else "build_models")
    out = os.path.abspath(argv[1] if len(argv) > 1 else "Drezina/data")
    os.makedirs(out, exist_ok=True)
    done = 0
    for name, (mass, shadow) in MODELS.items():
        if export_model(src, out, name, mass, shadow):
            done += 1
    for name, srcn in VIS_MODELS.items():
        if export_model(src, out, name, 1.0, False, srcn, True):
            done += 1
    print(f"[Drezina] готово: {done} из {len(MODELS)} моделей в {out}")


if __name__ == "__main__":
    main()
