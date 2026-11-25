import bpy, math, sys, mathutils
out = sys.argv[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
def load(name, loc, rot=0, skip=("geometry", "mem_")):
    with bpy.data.libraries.load(f"{out}/{name}.blend") as (src, dst):
        dst.objects = [n for n in src.objects if not n.startswith(skip)]
    for o in dst.objects:
        if o is None: continue
        sc.collection.objects.link(o)
        o.matrix_world = mathutils.Matrix.Translation(loc) @ mathutils.Matrix.Rotation(rot, 4, 'Z') @ o.matrix_world
# station: origin floor center, open end +Y. place so station spans y -4..20 (STATION_BACK=4)
load("metro_station", (0, 8, 0))
for i in range(4):
    load("tunnel_10m", (0, 20 + 5 + i*10, 0))
for i in range(6):
    load("rail_10m", (0, 0.5 + 5 + i*10, 0.27))
load("handcar", (0, 6, 0.27))
load("dispenser", (2.2, 1.5, 0))
load("metro_ladder", (-3.0, -3.4, 0))
for y in (2, 32):
    load("tunnel_lamp", (0, y, 4.3))
    L = bpy.data.objects.new("pl", bpy.data.lights.new("pl", "POINT")); L.data.energy = 900; L.data.color=(1,0.85,0.6); L.location=(0,y,3.9); sc.collection.objects.link(L)
L = bpy.data.objects.new("pl", bpy.data.lights.new("pl", "POINT")); L.data.energy = 1500; L.data.color=(1,0.85,0.6); L.location=(0,-1,4.5); sc.collection.objects.link(L)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam)
cam.data.lens = 18
cam.location = (-4.5, -3.2, 2.0)
d = mathutils.Vector((0.5, 14, 1.2)) - cam.location; cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
sc.camera = cam
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[1].default_value = 0.02
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 32
sc.render.resolution_x = 1200; sc.render.resolution_y = 750; sc.render.filepath = out + "/metro_preview.png"
bpy.ops.render.render(write_still=True)

# hatch on ground
bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
load("metro_hatch", (0, 0, 0))
bpy.ops.mesh.primitive_plane_add(size=40); g = bpy.context.active_object
mat = bpy.data.materials.new("grass"); mat.use_nodes=True; mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=(0.2,0.33,0.12,1); g.data.materials.append(mat)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam)
cam.location = (6, 8, 3.2); d = mathutils.Vector((0, 0, 1.5)) - cam.location; cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler(); sc.camera = cam
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sun.data.energy = 4; sun.rotation_euler = (0.8, 0.2, 2.2); sc.collection.objects.link(sun)
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value=(0.7,0.8,0.95,1)
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 24
sc.render.resolution_x = 900; sc.render.resolution_y = 600; sc.render.filepath = out + "/hatch_preview.png"
bpy.ops.render.render(write_still=True)
