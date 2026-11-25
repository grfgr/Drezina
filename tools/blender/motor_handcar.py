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
from handcar_zone import box, cyl, sphere, torus, dent, join, set_origin, uv_cube, smooth, selection, mem_point, ROT_X, ROT_Y

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
    """Одноцилиндровый мотор от старого мотоцикла (М-72/ИЖ) на самодельном подрамнике, справа впереди.
    Картер с крышками и болтами, оребрённый цилиндр и головка, свеча с высоковольтным проводом к
    магнето, карбюратор с поплавковой камерой и банкой фильтра, коллектор выхлопа с хомутами и
    глушителем, кикстартер, маховик, цепь со звеньями на переднюю ось, бак с краником и бензошлангом."""
    import mathutils
    ex, ey, ez = 0.22, 0.72, DECK + 0.20
    tilt = math.radians(-15)                                   # цилиндр наклонён вперёд
    up = mathutils.Vector((0, -math.sin(tilt), math.cos(tilt)))  # ось цилиндра
    base = mathutils.Vector((ex, ey + 0.02, ez + 0.06))

    def at(t):
        p = base + up * t
        return (p.x, p.y, p.z)

    # подрамник из уголка с косынками, мотор на резиновых подушках
    for sx in (-1, 1):
        out.append(box(f"eng_rail{sx}", (0.05, 0.56, 0.04), (ex + sx * 0.17, ey, DECK + 0.02), m["rust"]))
        for sy in (-1, 1):
            out.append(cyl(f"eng_mount{sx}{sy}", 0.028, 0.03, (ex + sx * 0.12, ey + sy * 0.12, DECK + 0.055), m["tape"]))
            out.append(cyl(f"eng_mount_bolt{sx}{sy}", 0.01, 0.06, (ex + sx * 0.12, ey + sy * 0.12, DECK + 0.07), m["steel"], (0, 0, 0), 6))
    # картер: два полукартера (цилиндры поперёк) + разъём с болтами
    out.append(cyl("crank_l", 0.12, 0.13, (ex - 0.065, ey, ez - 0.03), m["paint2"], ROT_X, 32))
    out.append(cyl("crank_r", 0.12, 0.13, (ex + 0.065, ey, ez - 0.03), m["paint2"], ROT_X, 32))
    out.append(cyl("crank_seam", 0.125, 0.012, (ex, ey, ez - 0.03), m["steel"], ROT_X, 32))
    for k in range(10):
        a = k * 2 * math.pi / 10
        out.append(cyl(f"crank_bolt{k}", 0.008, 0.03, (ex, ey + math.cos(a) * 0.112, ez - 0.03 + math.sin(a) * 0.112), m["steel"], ROT_X, 6))
    # крышка маховика справа и крышка магнето слева
    out.append(cyl("flywheel_cover", 0.1, 0.035, (ex + 0.15, ey, ez - 0.03), m["steel"], ROT_X, 32))
    out.append(torus("flywheel_rim", 0.095, 0.008, (ex + 0.17, ey, ez - 0.03), m["steel"], ROT_X, (32, 6)))
    for k in range(6):
        a = k * 2 * math.pi / 6
        out.append(cyl(f"flycov_bolt{k}", 0.007, 0.02, (ex + 0.17, ey + math.cos(a) * 0.075, ez - 0.03 + math.sin(a) * 0.075), m["steel"], ROT_X, 6))
    out.append(cyl("magneto", 0.045, 0.07, (ex - 0.16, ey + 0.06, ez + 0.03), m["paint"], ROT_X, 24))
    out.append(cyl("magneto_cap", 0.03, 0.02, (ex - 0.2, ey + 0.06, ez + 0.03), m["tape"], ROT_X, 16))
    # поддон и сливная пробка, подтёк масла
    out.append(box("sump", (0.2, 0.22, 0.04), (ex, ey, ez - 0.15), m["paint2"]))
    out.append(cyl("drain_plug", 0.012, 0.02, (ex, ey + 0.05, ez - 0.175), m["steel"], (0, 0, 0), 6))
    # цилиндр: гильза + 10 круглых рёбер охлаждения, к голове рёбра шире
    rod("cyl_barrel", at(0.02), at(0.24), 0.055, m["steel"], out)
    for k in range(10):
        t = 0.04 + k * 0.02
        fin = rod(f"cyl_fin{k}", at(t - 0.003), at(t + 0.003), 0.085 + k * 0.002, m["rust"], out)
    # головка: оребрённая, с болтами крышки клапанов
    rod("head_base", at(0.245), at(0.265), 0.095, m["paint2"], out)
    for k in range(5):
        t = 0.27 + k * 0.016
        rod(f"head_fin{k}", at(t - 0.003), at(t + 0.003), 0.1 - k * 0.006, m["rust"], out)
    rod("head_top", at(0.35), at(0.37), 0.06, m["paint2"], out)
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        p = mathutils.Vector(at(0.37)) + mathutils.Vector((math.cos(a) * 0.045, math.sin(a) * 0.045 * math.cos(tilt), 0))
        out.append(cyl(f"head_nut{k}", 0.009, 0.015, (p.x, p.y, p.z + 0.005), m["steel"], (tilt, 0, 0), 6))
    # свеча сбоку головки и высоковольтный провод к магнето
    plug_base = mathutils.Vector(at(0.3)) + mathutils.Vector((-0.1, 0, 0))
    plug_tip = plug_base + mathutils.Vector((-0.05, 0, 0.01))
    rod("plug_body", tuple(plug_base), tuple(plug_tip), 0.011, m["steel"], out)
    rod("plug_cap", tuple(plug_tip), tuple(plug_tip + mathutils.Vector((-0.04, 0, 0.01))), 0.016, m["tape"], out)
    lead = [tuple(plug_tip + mathutils.Vector((-0.04, 0, 0.01))), (ex - 0.24, ey + 0.1, ez + 0.2), (ex - 0.24, ey + 0.08, ez + 0.08), (ex - 0.21, ey + 0.06, ez + 0.03)]
    for i in range(len(lead) - 1):
        rod(f"ht_lead{i}", lead[i], lead[i + 1], 0.006, m["tape"], out)
    # карбюратор сзади цилиндра: корпус, поплавковая камера, трос газа, банка воздушного фильтра
    carb = mathutils.Vector((ex, ey - 0.13, ez + 0.17))
    rod("intake", at(0.18), tuple(carb), 0.022, m["steel"], out)
    out.append(cyl("carb_body", 0.03, 0.08, tuple(carb), m["steel"], ROT_Y, 20))
    out.append(cyl("float_bowl", 0.032, 0.06, (carb.x - 0.05, carb.y, carb.z - 0.04), m["steel"], (0, 0, 0), 20))
    out.append(cyl("tickler", 0.006, 0.03, (carb.x - 0.05, carb.y, carb.z + 0.005), m["steel"], (0, 0, 0), 8))
    rod("air_hose", tuple(carb), (carb.x, carb.y - 0.12, carb.z + 0.03), 0.028, m["tape"], out)
    out.append(cyl("air_filter", 0.065, 0.09, (carb.x, carb.y - 0.17, carb.z + 0.04), m["rust"], ROT_X, 28))
    out.append(cyl("air_filter_lid", 0.068, 0.012, (carb.x, carb.y - 0.22, carb.z + 0.04), m["paint"], ROT_X, 28))
    out.append(cyl("air_filter_wing", 0.008, 0.04, (carb.x, carb.y - 0.232, carb.z + 0.04), m["steel"], ROT_X, 6))
    for k in range(3):
        out.append(torus(f"hose_clamp{k}", 0.03, 0.004, (carb.x, carb.y - 0.03 - k * 0.04, carb.z + 0.005 + k * 0.01), m["steel"], ROT_X, (16, 4)))
    # выхлоп: колено из головки вниз и назад, хомуты, обмотка асбестом, глушитель с теплозащитой
    path = [at(0.3), (ex + 0.12, ey + 0.12, ez + 0.2), (ex + 0.22, ey + 0.05, ez + 0.02), (0.5, ey - 0.15, DECK + 0.07), (0.5, -0.6, DECK + 0.07)]
    for i in range(len(path) - 1):
        rod(f"exh{i}", path[i], path[i + 1], 0.021, m["rust"], out)
        out.append(sphere(f"exh_joint{i}", 0.022, path[i + 1], m["rust"], (1, 1, 1), (12, 8)))
    for k in range(4):
        out.append(torus(f"exh_wrap{k}", 0.024, 0.005, (0.5, ey - 0.25 - k * 0.05, DECK + 0.07), m["canvas"], ROT_X, (16, 4)))
    for y in (-0.2, -0.55):
        out.append(torus(f"exh_clamp{y}", 0.025, 0.005, (0.5, y, DECK + 0.07), m["steel"], ROT_X, (16, 4)))
        out.append(box(f"exh_hanger{y}", (0.012, 0.02, 0.06), (0.5, y, DECK + 0.035), m["rust"]))
    out.append(cyl("muffler", 0.055, 0.42, (0.5, -0.82, DECK + 0.08), m["rust"], ROT_X, 28))
    out.append(cyl("muffler_cone", 0.04, 0.05, (0.5, -1.05, DECK + 0.08), m["rust"], ROT_X, 20))
    out.append(cyl("muffler_tip", 0.022, 0.07, (0.5, -1.1, DECK + 0.08), m["steel"], ROT_X, 16))
    out.append(box("muffler_shield", (0.004, 0.36, 0.09), (0.44, -0.82, DECK + 0.1), m["steel"]))
    for k in range(6):
        out.append(cyl(f"shield_hole{k}", 0.008, 0.006, (0.437, -0.97 + k * 0.06, DECK + 0.1), m["tape"], ROT_Y, 10))
    # кикстартер на правой стороне
    rod("kick_shaft", (ex + 0.17, ey - 0.06, ez - 0.08), (ex + 0.21, ey - 0.06, ez - 0.08), 0.012, m["steel"], out)
    rod("kick_lever", (ex + 0.21, ey - 0.06, ez - 0.08), (ex + 0.22, ey - 0.25, ez + 0.0), 0.011, m["steel"], out)
    rod("kick_pedal", (ex + 0.22, ey - 0.25, ez), (ex + 0.29, ey - 0.25, ez), 0.013, m["rust"], out)
    # цепной привод на переднюю ось: звёздочки с зубьями, цепь звеньями, кожух
    cx = ex + 0.2
    e_c = mathutils.Vector((cx, ey, ez - 0.06))
    a_c = mathutils.Vector((cx, hz.AXLE_Y, hz.WHEEL_R))
    for name, c, r, teeth in (("spr_eng", e_c, 0.045, 14), ("spr_axle", a_c, 0.1, 30)):
        out.append(cyl(name, r - 0.006, 0.01, tuple(c), m["steel"], ROT_X, 32))
        for k in range(teeth):
            a = k * 2 * math.pi / teeth
            out.append(box(f"{name}_t{k}", (0.008, 0.008, 0.012), (c.x, c.y + math.cos(a) * r, c.z + math.sin(a) * r), m["steel"], (a, 0, 0), round_edges=False))
    # две прямые ветви цепи (касательные снаружи)
    d = (a_c - e_c)
    n = mathutils.Vector((0, -d.z, d.y)).normalized()
    for side, (r1, r2) in ((1, (0.05, 0.105)), (-1, (0.05, 0.105))):
        p1 = e_c + n * r1 * side
        p2 = a_c + n * r2 * side
        seg = p2 - p1
        links = max(4, int(seg.length / 0.016))
        for k in range(links):
            q = p1 + seg * (k + 0.5) / links
            out.append(box(f"chain{side}_{k}", (0.012, 0.014, 0.008), tuple(q), m["steel"], (math.atan2(seg.z, seg.y), 0, 0), round_edges=False))
    out.append(box("chain_guard", (0.012, 0.36, 0.06), (cx + 0.02, (ey + hz.AXLE_Y) / 2 + 0.04, max(ez - 0.06, hz.WHEEL_R) + 0.1), m["paint"], (math.radians(-20), 0, 0)))
    # бак на стойках: окраска с вмятиной, крышка-барашек, краник, бензошланг к карбюратору, хомуты-ленты
    for sy in (-1, 1):
        out.append(box(f"tank_post{sy}", (0.03, 0.03, 0.42), (ex, ey + sy * 0.2, DECK + 0.32), m["rust"]))
        band = torus(f"tank_band{sy}", 0.101, 0.006, (ex, ey + sy * 0.15, DECK + 0.6), m["steel"], ROT_Y, (32, 4))
        band.scale = (1.0, 0.84, 1.0)
        out.append(band)
    tank = sphere("tank", 1, (ex, ey, DECK + 0.6), m["paint"], (0.12, 0.26, 0.1), (32, 18))
    dent(tank, 0.004, cuts=1, seed=3)
    out.append(tank)
    out.append(cyl("tank_cap", 0.032, 0.025, (ex, ey + 0.08, DECK + 0.7), m["steel"], (0, 0, 0), 24))
    out.append(box("tank_cap_wing", (0.05, 0.008, 0.02), (ex, ey + 0.08, DECK + 0.72), m["steel"]))
    out.append(cyl("petcock", 0.01, 0.04, (ex, ey - 0.08, DECK + 0.49), m["steel"], (0, 0, 0), 8))
    out.append(box("petcock_lever", (0.03, 0.006, 0.008), (ex + 0.015, ey - 0.08, DECK + 0.48), m["steel"]))
    hose = [(ex, ey - 0.08, DECK + 0.47), (ex - 0.03, ey - 0.12, DECK + 0.43), (carb.x - 0.05, carb.y, carb.z + 0.03)]
    for i in range(len(hose) - 1):
        rod(f"fuel_hose{i}", hose[i], hose[i + 1], 0.006, m["tape"], out)


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


def rail_wheel(name, x, y, m):
    """Колесо мотодрисины: бандаж с катаной до блеска поверхностью катания и ребордой, диск с 8
    спицами-рёбрами, ступица с гайками, противовес, буксовая крышка. Selection/origin как у hz.wheel."""
    R = hz.WHEEL_R
    sx = 1 if x > 0 else -1
    parts = []
    # бандаж: поверхность катания (блестящая, накатанная о рельс) и реборда внутрь колеи
    parts.append(hz.tube_x(name + "_tread", R, R - 0.035, 0.09, (x, y, R), m["steel"], 64))
    parts.append(hz.tube_x(name + "_tyre_side", R - 0.004, R - 0.05, 0.1, (x + sx * 0.004, y, R), m["rust"], 64))
    parts.append(hz.tube_x(name + "_flange", R + 0.03, R - 0.03, 0.022, (x - sx * 0.05, y, R), m["steel"], 64))
    # обод и диск
    parts.append(hz.tube_x(name + "_rim", R - 0.05, R - 0.075, 0.07, (x, y, R), m["paint"], 48))
    for k in range(8):
        a = k * 2 * math.pi / 8 + 0.2
        r_mid = (R - 0.07 + 0.09) / 2
        sp = box(f"{name}_spoke{k}", (0.03, 0.035, R - 0.14), (x, y + math.sin(a) * r_mid, R + math.cos(a) * r_mid), m["paint"], (-a, 0, 0))
        parts.append(sp)
        parts.append(box(f"{name}_rib{k}", (0.07, 0.012, R - 0.16), (x, y + math.sin(a) * r_mid, R + math.cos(a) * r_mid), m["paint"], (-a, 0, 0)))
    # противовес между двумя спицами
    parts.append(box(name + "_weight", (0.06, 0.16, 0.06), (x, y - math.sin(0.6) * (R - 0.12), R - math.cos(0.6) * (R - 0.12)), m["paint"], (0.6, 0, 0)))
    # ступица, фланец, гайки по кругу, колпак
    parts.append(cyl(name + "_hub", 0.09, 0.14, (x, y, R), m["paint"], ROT_X, 32))
    parts.append(cyl(name + "_hubflange", 0.11, 0.02, (x + sx * 0.06, y, R), m["steel"], ROT_X, 32))
    for k in range(8):
        a = k * 2 * math.pi / 8
        parts.append(cyl(f"{name}_nut{k}", 0.012, 0.03, (x + sx * 0.075, y + math.sin(a) * 0.08, R + math.cos(a) * 0.08), m["steel"], ROT_X, 6))
    parts.append(cyl(name + "_cap", 0.05, 0.05, (x + sx * 0.09, y, R), m["steel"], ROT_X, 24))
    parts.append(cyl(name + "_capnut", 0.02, 0.06, (x + sx * 0.1, y, R), m["steel"], ROT_X, 6))
    o = join(parts, name)
    set_origin(o, (x, y, R))
    uv_cube(o, 0.5)
    smooth(o)
    selection(o, name)
    return o


def brakes_and_guards(m, out):
    """Колодочный тормоз на каждое колесо (тяга к правому рычагу), крылья-грязевики над колёсами,
    заклёпочные накладки и раскосы рамы, песочница."""
    import bmesh
    R = hz.WHEEL_R
    for ay in (hz.AXLE_Y, -hz.AXLE_Y):
        inner = -1 if ay > 0 else 1                      # колодка с внутренней стороны базы
        by = ay + inner * (R + 0.03)
        for sx in (-1, 1):
            x = sx * hz.HALF
            out.append(box(f"brake_shoe{ay}{sx}", (0.08, 0.04, 0.22), (x, by, R), m["rust"]))
            out.append(box(f"brake_block{ay}{sx}", (0.075, 0.015, 0.2), (x, by - inner * 0.02, R), m["steel"]))
            rod(f"brake_hanger{ay}{sx}", (x, by, R + 0.1), (sx * (hz.SILL_X + 0.03), by + inner * 0.02, DECK - 0.12), 0.01, m["rust"], out)
        # поперечная балка, соединяющая колодки
        rod(f"brake_beam{ay}", (-hz.HALF, by + inner * 0.03, R - 0.02), (hz.HALF, by + inner * 0.03, R - 0.02), 0.016, m["rust"], out)
    # продольная тяга от балок к рычагу тормоза
    rod("brake_rod", (0.1, -hz.AXLE_Y + R + 0.06, R - 0.02), (0.1, hz.AXLE_Y - R - 0.06, R - 0.02), 0.009, m["steel"], out)
    rod("brake_rod_up", (0.1, -0.12 + 0.66, R - 0.02), (0.17, -0.12 + 0.66, DECK + 0.08), 0.009, m["steel"], out)
    # крылья над колёсами: дуга из листа с отбортовкой и кронштейнами
    for ay in (hz.AXLE_Y, -hz.AXLE_Y):
        for sx in (-1, 1):
            x = sx * (hz.HALF + 0.01)
            bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=R + 0.07, depth=0.16, location=(x, ay, R), rotation=(0, math.radians(90), 0))
            g = bpy.context.active_object
            g.name = f"fender{ay}{sx}"
            bm = bmesh.new()
            bm.from_mesh(g.data)
            # оставить верхнюю дугу (локальная X после поворота — это мировая -Z)
            kill = [v for v in bm.verts if v.co.x > -(R + 0.07) * 0.35]
            bmesh.ops.delete(bm, geom=kill, context="VERTS")
            caps = [f for f in bm.faces if abs(f.normal.z) > 0.9]
            bmesh.ops.delete(bm, geom=caps, context="FACES")
            bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.004)
            bm.to_mesh(g.data)
            bm.free()
            g.data.materials.append(m["paint"])
            hz.dent(g, 0.004, cuts=1, seed=int(ay * 10 + sx))
            out.append(g)
            for dy in (-0.18, 0.18):
                rod(f"fender_bracket{ay}{sx}{dy}", (x, ay + dy, R + 0.33), (sx * hz.SILL_X, ay + dy, DECK - 0.1), 0.008, m["rust"], out)
    # раскосы рамы и заклёпочные накладки на углах
    for sx in (-1, 1):
        rod(f"frame_diag{sx}", (sx * hz.SILL_X, -0.95, DECK - 0.17), (sx * hz.SILL_X * 0.3, 0.95, DECK - 0.17), 0.012, m["rust"], out)
        for y in (-0.9, -0.3, 0.3, 0.9):
            out.append(box(f"splice{sx}{y}", (0.008, 0.12, 0.13), (sx * (hz.SILL_X + 0.016), y, DECK - 0.12), m["rust"]))
            for dz in (-0.04, 0.04):
                for dy in (-0.04, 0.04):
                    out.append(hz.bolt(f"rv{sx}{y}{dz}{dy}", (sx * (hz.SILL_X + 0.02), y + dy, DECK - 0.12 + dz), "x" if sx > 0 else "-x", m["steel"], 0.009))
    # песочница с трубкой к рельсу перед передними колёсами
    out.append(box("sandbox", (0.16, 0.12, 0.14), (-0.5, 1.02, DECK + 0.07), m["paint"]))
    out.append(box("sandbox_lid", (0.17, 0.13, 0.015), (-0.5, 1.02, DECK + 0.145), m["rust"], (math.radians(4), 0, 0)))
    rod("sand_pipe", (-0.5, 1.02, DECK), (-hz.HALF, hz.AXLE_Y + R + 0.03, 0.06), 0.012, m["rust"], out)


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
    brakes_and_guards(m, body)
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
        rail_wheel(name, x, y, m)

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
