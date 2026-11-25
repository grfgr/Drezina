"""
Мотодрезина: та же рама и колёса, что у ручной дрезины (handcar_zone.py), но вместо коромысла —
одноцилиндровый мотор с цепью на переднюю ось, бак, сиденье водителя с рулём-рычагом, две лавки
для пассажиров сзади (сидят боком, ногами наружу, лицом к стенам тоннеля) и брезентовая сумка
напротив водителя (это багажник машины).

Модель собрана как машина DayZ (CarScript):
  - View/Fire Geometry: прокси экипажа (\\dz\\vehicles\\wheeled\\proxies\\crew_driver / crew_cargo) в
    именованных выделениях crewDriver / crewCargo1 / crewCargo2 (кости в model.cfg с теми же именами);
    выделения seat_driver / seat_cargo1 / seat_cargo2 — куда смотрит игрок, чтобы сесть;
  - Geometry: компоненты рамы, мотора, бака и ступиц (dmgZone_*), масса 380 кг;
  - Memory: pos_* (откуда садятся), seat_con_* (проверка дистанции), wheel_X_Y_damper_land (ступицы),
    light_left/right(_dir) (фары), drown_engine, ptcExhaust_start/end, ptcEnginePos;
  - Resolution LOD: выделения light_left / light_right / light_dashboard ... для материалов фар.
"""
import math
import os

import bpy

import handcar_zone as hz
from handcar_zone import box, cyl, sphere, torus, join, set_origin, uv_cube, smooth, selection, mem_point, ROT_X, ROT_Y

DECK = hz.DECK_TOP
SEAT_H = DECK + 0.46          # верх подушки сиденья водителя
BENCH_H = DECK + 0.42         # верх лавок пассажиров
BENCH_Y = -0.98               # лавки у заднего торца (за задними колёсами ноги не цепляют)
DRIVER_Y = -0.12
# анимации мотоцикла: начало прокси — у земли под седлом, седло примерно на 0.8 м выше
RIDER_DROP = 0.8


def proxy(name, path, sel, loc, forward, visual=False, swap=False):
    """Пустышка-прокси: экспортёр рисует из неё треугольник прокси (вершина в loc, длинный катет вперёд,
    короткий вверх) и кладёт его в выделения 'proxy:<path>.NNN' и sel."""
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = "SINGLE_ARROW"
    e.location = loc
    e["proxy_path"] = path
    e["proxy_sel"] = sel
    e["proxy_fwd"] = forward
    e["proxy_visual"] = 1 if visual else 0
    e["proxy_swap"] = 1 if swap else 0
    bpy.context.scene.collection.objects.link(e)
    return e


def geo(name, size, loc, sel, m):
    o = box(name, size, loc, m["wood"], round_edges=False)
    o["sel"] = sel
    o.display_type = "WIRE"
    return o


def engine(m, out):
    """Одноцилиндровый мотор от мотоцикла на подрамнике, справа впереди."""
    ex, ey, ez = 0.22, 0.72, DECK + 0.20
    out.append(box("eng_frame_l", (0.04, 0.5, 0.04), (ex - 0.17, ey, DECK + 0.02), m["rust"]))
    out.append(box("eng_frame_r", (0.04, 0.5, 0.04), (ex + 0.17, ey, DECK + 0.02), m["rust"]))
    out.append(box("crankcase", (0.26, 0.32, 0.2), (ex, ey, ez - 0.04), m["paint2"]))
    out.append(cyl("crank_cover", 0.11, 0.03, (ex + 0.14, ey, ez - 0.04), m["steel"], ROT_X))
    out.append(cyl("crank_cover_l", 0.09, 0.03, (ex - 0.14, ey + 0.03, ez - 0.05), m["steel"], ROT_X))
    # цилиндр с рёбрами охлаждения, слегка наклонён вперёд
    tilt = (math.radians(-18), 0, 0)
    for k in range(9):
        z = ez + 0.1 + k * 0.026
        out.append(box(f"fin{k}", (0.2 - k * 0.004, 0.17 - k * 0.003, 0.008), (ex, ey + 0.03 + k * 0.008, z), m["rust"], tilt))
    out.append(cyl("cylinder", 0.06, 0.26, (ex, ey + 0.05, ez + 0.2), m["steel"], tilt))
    out.append(box("head", (0.16, 0.14, 0.06), (ex, ey + 0.1, ez + 0.36), m["paint2"], tilt))
    out.append(cyl("plug", 0.012, 0.05, (ex, ey + 0.14, ez + 0.41), m["steel"], tilt, 6))
    out.append(cyl("plug_cap", 0.016, 0.03, (ex, ey + 0.15, ez + 0.44), m["tape"], tilt, 8))
    # карбюратор и воздушный фильтр (жестянка)
    out.append(cyl("carb", 0.03, 0.08, (ex - 0.11, ey + 0.02, ez + 0.2), m["steel"], ROT_X))
    out.append(cyl("airfilter", 0.06, 0.07, (ex - 0.19, ey + 0.02, ez + 0.2), m["rust"], ROT_X))
    # выхлопная труба назад по правому борту, глушитель у заднего торца
    out.append(cyl("exh_down", 0.022, 0.24, (ex + 0.06, ey + 0.16, ez + 0.12), m["rust"], (math.radians(30), 0, 0)))
    out.append(cyl("exh_pipe", 0.022, 1.45, (0.5, 0.02, DECK + 0.06), m["rust"], ROT_Y))
    out.append(cyl("muffler", 0.05, 0.4, (0.5, -0.82, DECK + 0.08), m["rust"], ROT_Y))
    out.append(cyl("muffler_tip", 0.025, 0.08, (0.5, -1.06, DECK + 0.08), m["steel"], ROT_Y))
    # цепь на переднюю ось: звёздочки и кожух
    out.append(cyl("sprocket_eng", 0.05, 0.012, (ex + 0.17, ey, ez - 0.06), m["steel"], ROT_X, 16))
    out.append(cyl("sprocket_axle", 0.11, 0.012, (ex + 0.17, hz.AXLE_Y, hz.WHEEL_R), m["steel"], ROT_X, 24))
    out.append(box("chain_guard", (0.02, 0.3, 0.2), (ex + 0.19, (ey + hz.AXLE_Y) / 2, (ez - 0.06 + hz.WHEEL_R) / 2), m["paint"]))
    # бак над мотором на двух стойках
    out.append(box("tank_post_f", (0.03, 0.03, 0.42), (ex, ey + 0.2, DECK + 0.32), m["rust"]))
    out.append(box("tank_post_b", (0.03, 0.03, 0.42), (ex, ey - 0.2, DECK + 0.32), m["rust"]))
    tank = sphere("tank", 1, (ex, ey, DECK + 0.6), m["paint"], (0.13, 0.26, 0.1), (24, 14))
    out.append(tank)
    out.append(cyl("tank_cap", 0.03, 0.03, (ex, ey + 0.08, DECK + 0.7), m["steel"]))
    out.append(cyl("fuel_line", 0.005, 0.3, (ex - 0.07, ey - 0.05, DECK + 0.42), m["tape"], (0, 0, 0), 6))


def driver_place(m, out):
    """Тракторное сиденье на стойке, перед ним рулевая колонка с рычагами газа/тормоза."""
    out.append(cyl("seat_post", 0.03, SEAT_H - DECK - 0.06, (0, DRIVER_Y - 0.05, (SEAT_H + DECK) / 2 - 0.03), m["rust"]))
    out.append(box("seat_spring", (0.05, 0.3, 0.012), (0, DRIVER_Y, SEAT_H - 0.07), m["steel"], (math.radians(-8), 0, 0)))
    pan = sphere("seat_pan", 1, (0, DRIVER_Y, SEAT_H - 0.03), m["paint2"], (0.22, 0.2, 0.04), (24, 12))
    out.append(pan)
    out.append(box("seat_back", (0.36, 0.04, 0.22), (0, DRIVER_Y - 0.19, SEAT_H + 0.12), m["paint2"], (math.radians(-12), 0, 0)))
    # два рычага управления (газ слева, тормоз справа) — рукоятки там, где руки водителя
    # в анимации машины (руль Нивы): ~0.4 м перед сиденьем, ~0.4 м над подушкой, ±0.17 м от оси
    for sx, name in ((-1, "lever_throttle"), (1, "lever_brake")):
        grip = (sx * 0.17, DRIVER_Y + 0.40, SEAT_H + 0.40)
        pivot = (sx * 0.17, DRIVER_Y + 0.66, DECK + 0.08)
        rod(name, pivot, grip, 0.014, m["steel"], out)
        # рукоятка: обмотана изолентой, с шариком на конце
        top = (grip[0], grip[1] - 0.02, grip[2] + 0.05)
        rod(name + "_grip", grip, top, 0.022, m["tape"], out)
        out.append(sphere(name + "_knob", 0.026, top, m["steel"], (1, 1, 1), (16, 10)))
        # кронштейн-шарнир на полу
        out.append(box(name + "_pivot", (0.06, 0.08, 0.06), pivot, m["rust"]))
        out.append(cyl(name + "_axle", 0.012, 0.12, pivot, m["steel"], ROT_X, 12))
        # тяга к мотору
        rod(name + "_link", (sx * 0.17, DRIVER_Y + 0.6, DECK + 0.2), (0.22 * (1 if sx > 0 else 0.6), 0.55, DECK + 0.12), 0.006, m["steel"], out)
    # сектор-гребёнка рычага газа (фиксирует положение)
    sector_c = (-0.24, DRIVER_Y + 0.6, DECK + 0.3)
    out.append(box("throttle_sector", (0.008, 0.22, 0.07), sector_c, m["rust"], (math.radians(-35), 0, 0)))
    for k in range(6):
        out.append(box(f"sector_tooth{k}", (0.012, 0.01, 0.014), (-0.24, DRIVER_Y + 0.52 + k * 0.03, DECK + 0.26 + k * 0.02), m["steel"]))
    # педальная площадка под ноги
    out.append(box("footrest", (0.5, 0.2, 0.02), (0, DRIVER_Y + 0.42, DECK + 0.04), m["steel"], (math.radians(12), 0, 0)))
    for k in range(5):
        out.append(box(f"footrest_rib{k}", (0.46, 0.01, 0.008), (0, DRIVER_Y + 0.35 + k * 0.035, DECK + 0.045 + k * 0.007), m["steel"]))


def rod(name, a, b, r, mat, out):
    """Цилиндр между точками a и b."""
    import mathutils
    d = mathutils.Vector(b) - mathutils.Vector(a)
    mid = [(a[k] + b[k]) / 2 for k in range(3)]
    o = cyl(name, r, d.length, mid, mat, (0, 0, 0), 12)
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = mathutils.Vector((0, 0, 1)).rotation_difference(d.normalized())
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    out.append(o)
    return o


def passenger_benches(m, out):
    """Задний диван на двоих, как сиденье в машине: широкая лавка со спинкой и подлокотниками.
    Пассажиры сидят лицом вперёд, ноги — на полу перед лавкой."""
    w = 1.3
    out.append(box("bench_seat", (w, 0.42, 0.05), (0, BENCH_Y, BENCH_H - 0.025), m["wood"]))
    out.append(box("bench_cushion_l", (0.55, 0.38, 0.04), (-0.32, BENCH_Y + 0.01, BENCH_H + 0.015), m["canvas"]))
    out.append(box("bench_cushion_r", (0.55, 0.38, 0.04), (0.32, BENCH_Y + 0.01, BENCH_H + 0.015), m["canvas"]))
    for dx in (-0.6, 0.0, 0.6):
        for dy in (-0.17, 0.17):
            out.append(box(f"bench_leg{dx}{dy}", (0.05, 0.05, BENCH_H - DECK - 0.05), (dx, BENCH_Y + dy, (BENCH_H + DECK) / 2 - 0.025), m["rust"]))
    # спинка из досок на стойках
    for k, z in enumerate((0.18, 0.36)):
        out.append(box(f"bench_back{k}", (w, 0.035, 0.12), (0, BENCH_Y - 0.2, BENCH_H + z), m["wood"], (math.radians(-8), 0, 0)))
    for dx in (-0.62, 0.62):
        out.append(box(f"bench_back_post{dx}", (0.04, 0.04, 0.5), (dx, BENCH_Y - 0.21, BENCH_H + 0.23), m["rust"]))
        # подлокотник — труба
        out.append(cyl(f"bench_arm{dx}", 0.016, 0.4, (dx, BENCH_Y, BENCH_H + 0.2), m["rust"], ROT_Y))
        out.append(cyl(f"bench_arm_post{dx}", 0.014, 0.2, (dx, BENCH_Y + 0.18, BENCH_H + 0.1), m["rust"]))
    # упор для ног пассажиров
    out.append(box("bench_footrest", (w, 0.12, 0.03), (0, BENCH_Y + 0.62, DECK + 0.04), m["steel"], (math.radians(15), 0, 0)))


def bag(m, out):
    """Армейский вещмешок-баул из брезента: тело-цилиндр с провисшими боками, клапан, кожаные ремни с
    пряжками, ручка, боковой карман, шнуровка, заплатка. Лежит слева впереди (багажник)."""
    import bmesh
    bx, by, bz = -0.36, 0.72, DECK + 0.17
    L, R = 0.62, 0.17
    # тело: цилиндр вдоль Y, сплющен снизу, с вмятинами и складками
    bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=R, depth=L, location=(bx, by, bz), rotation=(math.radians(90), 0, 0))
    body = bpy.context.active_object
    body.name = "bag_body"
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.subdivide(number_cuts=10)
    bpy.ops.object.mode_set(mode="OBJECT")
    for v in body.data.vertices:
        x, y, z = v.co                     # локально: ось цилиндра — Z (после поворота ляжет вдоль Y)
        # после поворота локальная Y смотрит вверх: низ мешка сплющен о пол, верх чуть осел
        v.co.y = v.co.y * 0.85
        if v.co.y < -0.11:
            v.co.y = -0.11 + (v.co.y + 0.11) * 0.2
        # торцы скруглить (как набитый мешок)
        t = abs(z) / (L / 2)
        k = 1.0 - 0.35 * t ** 6
        v.co.x *= k
        v.co.y *= k
        # складки поперёк
        v.co.x += math.sin(z * 37 + x * 9) * 0.006
        v.co.y += math.sin(z * 29 + 1.3) * 0.004
    body.data.materials.append(m["canvas"])
    for f in body.data.polygons:
        f.use_smooth = True
    out.append(body)
    # клапан: изогнутая брезентовая накладка по верху мешка, с кожаным кантом
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=R + 0.012, depth=0.3, location=(bx, by + 0.12, bz), rotation=(math.radians(90), 0, 0))
    flap = bpy.context.active_object
    flap.name = "bag_flap"
    bm = bmesh.new()
    bm.from_mesh(flap.data)
    kill = [v for v in bm.verts if v.co.y < R * 0.25]       # локальная Y — вверх: оставляем верхнюю дугу
    bmesh.ops.delete(bm, geom=kill, context="VERTS")
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.006)
    bm.to_mesh(flap.data)
    bm.free()
    flap.data.materials.append(m["canvas"])
    for f in flap.data.polygons:
        f.use_smooth = True
    out.append(flap)
    out.append(box("bag_flap_edge", (0.22, 0.02, 0.014), (bx, by + 0.27, bz + R * 0.86), m["leather"]))
    # два кожаных ремня обхватывают мешок (поверх брезента), пряжки из латуни
    for k, dy in enumerate((-0.17, 0.17)):
        st = torus(f"bag_strap{k}", R * 1.0 + 0.012, 0.007, (bx, by + dy, bz), m["leather"], ROT_Y, (40, 6))
        st.scale = (1.0, 1.0, 0.86)
        out.append(st)
        out.append(box(f"bag_buckle{k}", (0.035, 0.012, 0.04), (bx + R * 0.8, by + dy, bz + R * 0.5), m["steel"], (0, math.radians(50), 0)))
        out.append(box(f"bag_strap_tail{k}", (0.03, 0.03, 0.005), (bx + R * 0.95, by + dy, bz + R * 0.25), m["leather"], (0, math.radians(75), 0)))
    # ручка для переноски
    out.append(torus("bag_handle", 0.06, 0.01, (bx, by, bz + R * 0.95), m["leather"], (0, math.radians(90), 0), (24, 8)))
    for dy in (-0.06, 0.06):
        out.append(box(f"bag_handle_tab{dy}", (0.04, 0.03, 0.006), (bx, by + dy, bz + R * 0.86), m["leather"]))
    # боковой карман с клапаном и кнопкой
    pocket = sphere("bag_pocket", 1, (bx - R * 0.88, by - 0.04, bz - 0.01), m["canvas"], (0.035, 0.11, 0.075), (20, 12))
    out.append(pocket)
    out.append(box("bag_pocket_flap", (0.02, 0.21, 0.05), (bx - R * 0.97, by - 0.04, bz + 0.05), m["canvas"], (math.radians(4), 0, 0)))
    out.append(cyl("bag_pocket_button", 0.008, 0.008, (bx - R * 0.95, by - 0.04, bz + 0.04), m["steel"], ROT_X, 12))
    # шнуровка на торце и заплатка
    for k in range(5):
        a = k * 2 * math.pi / 5
        out.append(cyl(f"bag_eyelet{k}", 0.006, 0.006, (bx + math.cos(a) * 0.06, by + L / 2 - 0.02, bz + math.sin(a) * 0.06), m["steel"], ROT_Y, 10))
    out.append(cyl("bag_drawcord", 0.004, 0.18, (bx + 0.03, by + L / 2 + 0.01, bz - 0.02), m["tape"], (0, math.radians(70), 0), 6))
    out.append(box("bag_patch", (0.11, 0.09, 0.004), (bx + 0.05, by - 0.15, bz + R * 0.86), m["leather"], (math.radians(-12), math.radians(14), 0)))
    # верёвка, которой баул привязан к раме
    out.append(cyl("bag_rope", 0.006, 0.5, (bx, by, DECK + 0.01), m["canvas"], ROT_X, 6))


def lamps(m, out, sel_parts):
    """Две фары спереди (лампочки H7 в слотах Reflector_1_1 / Reflector_2_1) и красный фонарь сзади."""
    for sx, sel in ((-1, "light_left"), (1, "light_right")):
        parts = []
        hz.headlamp(f"hl{sx}", (sx * 0.45, 1.29, DECK + 0.02), 1, m, parts)
        glass = [p for p in parts if p.name.endswith("_glass")]
        for p in parts:
            out.append(p)
        for g in glass:
            sel_parts.append((g, sel))
    parts = []
    hz.headlamp("hl_back", (0.0, -1.29, DECK + 0.02), -1, m, parts)
    for p in parts:
        out.append(p)
        if p.name.endswith("_glass"):
            sel_parts.append((p, "light_brake_1_2"))


def build(outdir, tex_dir, save_fn, reset_fn):
    hz.TEX_DIR = tex_dir
    reset_fn()
    m = hz.materials()

    body, wood, metal, props = [], [], [], []
    hz.layer1_frame(m, body)
    hz.layer1_deck(m, wood, metal)
    hz.layer2_running_gear(m, body)
    hz.layer2_couplers(m, body)
    hz.layer3_wear(m, body)
    engine(m, props)
    driver_place(m, props)
    passenger_benches(m, props)
    bag(m, props)
    sel_parts = []
    lamps(m, props, sel_parts)

    # стёкла фар — отдельные объекты со своими выделениями (материал фар переключает скрипт машины)
    lamp_glass = []
    for g, sel in sel_parts:
        props.remove(g)
        uv_cube(g, 0.3)
        selection(g, sel)
        lamp_glass.append(g)

    main = join(body + wood + metal + props, "body")
    uv_cube(main, 0.8)
    main = join([main, hz.layer3_plate(m)], "body")
    smooth(main)
    selection(main, "body")

    for name, x, y in (("wheel_1_1", -hz.HALF, hz.AXLE_Y), ("wheel_2_1", hz.HALF, hz.AXLE_Y),
                       ("wheel_1_2", -hz.HALF, -hz.AXLE_Y), ("wheel_2_2", hz.HALF, -hz.AXLE_Y)):
        hz.wheel(name, x, y, m)

    # ---- экипаж: прокси в View/Fire Geometry (кости crewDriver / crewCargo1 / crewCargo2)
    P = "\\dz\\vehicles\\wheeled\\proxies\\"
    proxy("proxy_driver", P + "crew_driver", "crewDriver", (0, DRIVER_Y, SEAT_H), (0, 1, 0))
    proxy("proxy_cargo1", P + "crew_cargo", "crewCargo1", (-0.32, BENCH_Y + 0.02, BENCH_H + 0.03), (0, 1, 0))
    proxy("proxy_cargo2", P + "crew_cargo", "crewCargo2", (0.32, BENCH_Y + 0.02, BENCH_H + 0.03), (0, 1, 0))

    # ---- колёса для физики машины: прокси ванильного колеса Нивы (слоты NivaWheel_1_1, _1_2, _2_1, _2_2 —
    # в порядке номеров прокси .001-.004). Видимые колёса свои, прокси только в View/Fire Geometry.
    W = "\\dz\\vehicles\\wheeled\\offroadhatchback\\proxy\\nivawheel"
    proxy("proxy_wheel_1", W, "wheel_1_1_proxy", (-hz.HALF, hz.AXLE_Y, hz.WHEEL_R), (0, 1, 0))
    proxy("proxy_wheel_2", W, "wheel_1_2_proxy", (-hz.HALF, -hz.AXLE_Y, hz.WHEEL_R), (0, 1, 0))
    proxy("proxy_wheel_3", W, "wheel_2_1_proxy", (hz.HALF, hz.AXLE_Y, hz.WHEEL_R), (0, 1, 0))
    proxy("proxy_wheel_4", W, "wheel_2_2_proxy", (hz.HALF, -hz.AXLE_Y, hz.WHEEL_R), (0, 1, 0))

    # ---- точки (Memory)
    mem_point("mem_pos_driver", (-1.05, DRIVER_Y, 0.05))
    mem_point("mem_pos_driver_dir", (-0.4, DRIVER_Y, 0.05))
    mem_point("mem_pos_cargo1", (-1.15, BENCH_Y, 0.05))
    mem_point("mem_pos_cargo1_dir", (-0.5, BENCH_Y, 0.05))
    mem_point("mem_pos_cargo2", (-0.15, BENCH_Y + 0.55, DECK))
    mem_point("mem_pos_cargo2_dir", (0.25, BENCH_Y + 0.55, DECK))
    mem_point("mem_seat_con_1_1", (-0.95, DRIVER_Y, DECK))
    mem_point("mem_seat_con_1_2", (-0.95, BENCH_Y, DECK))
    mem_point("mem_seat_con_2_2", (0.95, BENCH_Y, DECK))
    for name, x, y in (("wheel_1_1", -hz.HALF, hz.AXLE_Y), ("wheel_2_1", hz.HALF, hz.AXLE_Y),
                       ("wheel_1_2", -hz.HALF, -hz.AXLE_Y), ("wheel_2_2", hz.HALF, -hz.AXLE_Y)):
        mem_point(f"mem_{name}_damper_land", (x, y, hz.WHEEL_R))
        mem_point(f"mem_{name}_axis", (x, y, hz.WHEEL_R))
    mem_point("mem_axle_front_1", (-hz.HALF, hz.AXLE_Y, hz.WHEEL_R))
    mem_point("mem_axle_front_2", (hz.HALF, hz.AXLE_Y, hz.WHEEL_R))
    mem_point("mem_axle_rear_1", (-hz.HALF, -hz.AXLE_Y, hz.WHEEL_R))
    mem_point("mem_axle_rear_2", (hz.HALF, -hz.AXLE_Y, hz.WHEEL_R))
    mem_point("mem_light_left", (-0.45, 1.36, DECK + 0.02))
    mem_point("mem_light_left_dir", (-0.45, 2.36, DECK - 0.03))
    mem_point("mem_light_right", (0.45, 1.36, DECK + 0.02))
    mem_point("mem_light_right_dir", (0.45, 2.36, DECK - 0.03))
    mem_point("mem_light_reverse", (0.0, -1.36, DECK + 0.02))
    mem_point("mem_drown_engine", (0.22, 0.72, DECK + 0.2))
    mem_point("mem_ptcEnginePos", (0.22, 0.72, DECK + 0.45))
    mem_point("mem_ptcExhaust_start", (0.5, -1.0, DECK + 0.08))
    mem_point("mem_ptcExhaust_end", (0.5, -1.12, DECK + 0.08))
    mem_point("mem_dmgZone_engine", (0.22, 0.72, DECK + 0.2))
    mem_point("mem_dmgZone_lights_1_1", (-0.45, 1.29, DECK + 0.02))
    mem_point("mem_dmgZone_lights_2_1", (0.45, 1.29, DECK + 0.02))
    mem_point("mem_camera", (0, 0, 1.6))

    # ---- Geometry: компоненты (масса считается по всем вершинам, распределена равномерно)
    geo("geometry_chassis", (1.36, 2.4, 0.22), (0, 0, DECK - 0.11), "dmgZone_chassis", m)
    geo("geometry_engine", (0.36, 0.5, 0.42), (0.22, 0.72, DECK + 0.21), "dmgZone_engine", m)
    geo("geometry_tank", (0.28, 0.5, 0.2), (0.22, 0.72, DECK + 0.6), "dmgZone_fuelTank,refill", m)
    mem_point("mem_refill", (0.22, 0.8, DECK + 0.7))
    geo("geometry_bag", (0.46, 0.66, 0.38), (-0.36, 0.72, DECK + 0.19), "dmgZone_bag", m)
    geo("geometry_seat_driver", (0.42, 0.42, 0.5), (0, DRIVER_Y, DECK + 0.25), "seat_driver", m)
    geo("geometry_seat_cargo1", (0.55, 0.4, 0.42), (-0.32, BENCH_Y, DECK + 0.21), "seat_cargo1", m)
    geo("geometry_seat_cargo2", (0.55, 0.4, 0.42), (0.32, BENCH_Y, DECK + 0.21), "seat_cargo2", m)
    for name, x, y in (("1_1", -hz.HALF, hz.AXLE_Y), ("2_1", hz.HALF, hz.AXLE_Y),
                       ("1_2", -hz.HALF, -hz.AXLE_Y), ("2_2", hz.HALF, -hz.AXLE_Y)):
        geo(f"geometry_hub_{name}", (0.1, 0.5, 0.5), (x, y, hz.WHEEL_R + 0.02), f"dmgZone_wheel_{name},wheel_{name}_damper_land", m)

    # В игре нос модели оказался сзади (по ходу машины DayZ «вперёд» — другая сторона), поэтому
    # разворачиваем всю мотодрезину на 180° вокруг вертикали: мотор и водитель смотрят по ходу.
    import mathutils
    rot = mathutils.Matrix.Rotation(math.pi, 4, "Z")
    for o in bpy.data.objects:
        if o.parent is None:
            o.matrix_world = rot @ o.matrix_world
        if "proxy_fwd" in o:
            fx, fy, fz = o["proxy_fwd"]
            o["proxy_fwd"] = (-fx, -fy, fz)

    meshes = [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("geometry")]
    print(f"[Drezina] motor_handcar faces LOD0: {sum(len(o.data.polygons) for o in meshes)}")
    save_fn(outdir, "motor_handcar")

    for lod, ratio in ((1, 0.4), (2, 0.15)):
        for o in meshes:
            mod = o.modifiers.new("decimate", "DECIMATE")
            mod.ratio = ratio
            bpy.context.view_layer.objects.active = o
            bpy.ops.object.modifier_apply(modifier=mod.name)
        save_fn(outdir, f"motor_handcar_lod{lod}")
    bpy.ops.wm.open_mainfile(filepath=os.path.join(outdir, "motor_handcar.blend"))
