import bpy, math, sys, mathutils
from mathutils import Vector, Matrix
out=sys.argv[1]
bpy.ops.wm.read_factory_settings(use_empty=True); sc=bpy.context.scene
def load(name, loc=(0,0,0), rot=0):
    with bpy.data.libraries.load(f"{out}/{name}.blend") as (src,dst):
        dst.objects=[n for n in src.objects if not n.startswith(("geometry","mem_"))]
    for o in dst.objects:
        if o: sc.collection.objects.link(o); o.matrix_world=Matrix.Translation(loc)@Matrix.Rotation(rot,4,'Z')@o.matrix_world
for i in range(-2,3): load("rail_10m",(0,i*10,0))
load("handcar",(0,-3,0))
bpy.ops.mesh.primitive_plane_add(size=80, location=(0,0,-0.6)); g=bpy.context.active_object
mat=bpy.data.materials.new("g"); mat.use_nodes=True; mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=(0.14,0.15,0.08,1); g.data.materials.append(mat)
c=bpy.data.objects.new("cam",bpy.data.cameras.new("cam")); sc.collection.objects.link(c); c.data.lens=32
c.location=(2.3,3.2,0.9); d=Vector((0,-1.0,-0.15))-c.location; c.rotation_euler=d.to_track_quat('-Z','Y').to_euler(); sc.camera=c
s=bpy.data.objects.new("sun",bpy.data.lights.new("sun","SUN")); s.data.energy=2.2; s.rotation_euler=(0.85,0.2,2.4); sc.collection.objects.link(s)
w=bpy.data.worlds.new("w"); sc.world=w; w.use_nodes=True; w.node_tree.nodes['Background'].inputs[0].default_value=(0.6,0.62,0.66,1)
sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=40
sc.render.resolution_x=1300; sc.render.resolution_y=800; sc.render.filepath=f"{out}/rail_real.png"
bpy.ops.render.render(write_still=True)
