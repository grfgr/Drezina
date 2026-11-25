import bpy, sys
from mathutils import Vector, Matrix
out=sys.argv[1]
bpy.ops.wm.read_factory_settings(use_empty=True); sc=bpy.context.scene
def load(name, loc):
    with bpy.data.libraries.load(f"{out}/{name}.blend") as (src,dst):
        dst.objects=[n for n in src.objects if not n.startswith(("geometry","mem_"))]
    for o in dst.objects:
        if o: sc.collection.objects.link(o); o.matrix_world=Matrix.Translation(loc)@o.matrix_world
for i,n in enumerate(["rail_10m","rail_10m_lod1","rail_10m_lod2","rail_10m_lod3"]):
    load(n,(i*5.5,0,0))
bpy.ops.mesh.primitive_plane_add(size=80, location=(8,0,-0.66)); g=bpy.context.active_object
m=bpy.data.materials.new("g"); m.use_nodes=True; m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=(0.14,0.15,0.08,1); g.data.materials.append(m)
c=bpy.data.objects.new("cam",bpy.data.cameras.new("cam")); sc.collection.objects.link(c); c.data.lens=26
c.location=(8.25,-15,7.5); d=Vector((8.25,0,-0.3))-c.location; c.rotation_euler=d.to_track_quat('-Z','Y').to_euler(); sc.camera=c
s=bpy.data.objects.new("sun",bpy.data.lights.new("sun","SUN")); s.data.energy=2.2; s.rotation_euler=(0.8,0.2,2.4); sc.collection.objects.link(s)
w=bpy.data.worlds.new("w"); sc.world=w; w.use_nodes=True; w.node_tree.nodes['Background'].inputs[0].default_value=(0.6,0.62,0.66,1)
sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=32
sc.render.resolution_x=1400; sc.render.resolution_y=700; sc.render.filepath=f"{out}/rail_lods.png"
bpy.ops.render.render(write_still=True)
