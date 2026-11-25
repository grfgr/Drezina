import bpy, math, sys
out = sys.argv[1]
bpy.ops.wm.open_mainfile(filepath=out+"/handcar.blend")
for o in list(bpy.data.objects):
    if o.name.startswith("geometry"): bpy.data.objects.remove(o)
# lift handcar on rails: rail head at z=0 in rail file -> put rails at z=0
for i in range(-2,3):
    with bpy.data.libraries.load(out+"/rail_2m.blend") as (src, dst):
        dst.objects = ["rail"]
    r = dst.objects[0]; bpy.context.scene.collection.objects.link(r); r.location=(0,i*2,0)
lever = bpy.data.objects["lever"]; lever.rotation_euler[0]=math.radians(15)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); bpy.context.scene.collection.objects.link(cam)
cam.location=(4.2,-3.6,2.4); 
import mathutils
d = mathutils.Vector((0,0,0.8))-cam.location; cam.rotation_euler = d.to_track_quat('-Z','Y').to_euler()
bpy.context.scene.camera=cam
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun","SUN")); bpy.context.scene.collection.objects.link(sun); sun.rotation_euler=(0.7,0.2,0.5)
w=bpy.data.worlds.new("w"); bpy.context.scene.world=w
s=bpy.context.scene; s.render.engine='CYCLES'; s.cycles.device='CPU'; s.cycles.samples=24; w.use_nodes=True; w.node_tree.nodes['Background'].inputs[0].default_value=(0.8,0.85,0.9,1); w.node_tree.nodes['Background'].inputs[1].default_value=0.6; sun.data.energy=4
s.render.resolution_x=1200; s.render.resolution_y=800; s.render.filepath=out+"/preview.png"
bpy.ops.render.render(write_still=True)
