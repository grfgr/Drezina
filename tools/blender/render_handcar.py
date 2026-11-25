import bpy, math, sys, mathutils
out=sys.argv[1]; tag=sys.argv[2]; cx,cy,cz=map(float,sys.argv[3:6]); tx,ty,tz=map(float,sys.argv[6:9])
bpy.ops.wm.open_mainfile(filepath=out+"/handcar.blend")
sc=bpy.context.scene
for o in list(bpy.data.objects):
    if o.name.startswith("geometry"): bpy.data.objects.remove(o)
bpy.data.objects["lever"].rotation_euler[0]=math.radians(14)
bpy.data.objects["wheel_fl"].rotation_euler[0]=0.3
for i in range(-3,4):
    with bpy.data.libraries.load(out+"/rail_2m.blend") as (src,dst): dst.objects=["rail"]
    r=dst.objects[0]; sc.collection.objects.link(r); r.location=(0,i*2,0)
bpy.ops.mesh.primitive_plane_add(size=40, location=(0,0,-0.27)); g=bpy.context.active_object
mat=bpy.data.materials.new("ground"); mat.use_nodes=True; nt=mat.node_tree; b=nt.nodes["Principled BSDF"]
n=nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value=8; cr=nt.nodes.new("ShaderNodeValToRGB")
cr.color_ramp.elements[0].color=(0.09,0.08,0.06,1); cr.color_ramp.elements[1].color=(0.2,0.19,0.15,1)
nt.links.new(n.outputs["Fac"],cr.inputs["Fac"]); nt.links.new(cr.outputs["Color"],b.inputs["Base Color"]); g.data.materials.append(mat)
cam=bpy.data.objects.new("cam",bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); cam.data.lens=40
cam.location=(cx,cy,cz); d=mathutils.Vector((tx,ty,tz))-cam.location; cam.rotation_euler=d.to_track_quat('-Z','Y').to_euler(); sc.camera=cam
sun=bpy.data.objects.new("sun",bpy.data.lights.new("sun","SUN")); sun.data.energy=1.6; sun.data.angle=0.4; sun.data.color=(1,0.93,0.82); sun.rotation_euler=(0.9,0.3,0.6); sc.collection.objects.link(sun)
w=bpy.data.worlds.new("w"); sc.world=w; w.use_nodes=True; bg=w.node_tree.nodes['Background']; bg.inputs[0].default_value=(0.55,0.58,0.6,1); bg.inputs[1].default_value=0.9
sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=48
sc.view_settings.look='AgX - Medium High Contrast' if 'AgX - Medium High Contrast' in [x for x in []] else sc.view_settings.look
sc.render.resolution_x=1400; sc.render.resolution_y=900; sc.render.filepath=f"{out}/zone_{tag}.png"
bpy.ops.render.render(write_still=True)
