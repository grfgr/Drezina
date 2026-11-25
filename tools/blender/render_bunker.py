import bpy, math, sys, mathutils
from mathutils import Vector, Matrix
out=sys.argv[1]; scene=sys.argv[2]; MOODY=len(sys.argv)>3
bpy.ops.wm.read_factory_settings(use_empty=True); sc=bpy.context.scene
def load(name, loc=(0,0,0), rot=0, skip=("geometry","mem_")):
    with bpy.data.libraries.load(f"{out}/{name}.blend") as (src,dst):
        dst.objects=[n for n in src.objects if not n.startswith(skip)]
    objs=[o for o in dst.objects if o]
    for o in objs:
        sc.collection.objects.link(o)
        o.matrix_world=Matrix.Translation(loc)@Matrix.Rotation(rot,4,'Z')@o.matrix_world
    return objs
def cam(loc, target, lens=24):
    c=bpy.data.objects.new("cam",bpy.data.cameras.new("cam")); sc.collection.objects.link(c); c.data.lens=lens
    c.location=loc; d=Vector(target)-Vector(loc); c.rotation_euler=d.to_track_quat('-Z','Y').to_euler(); sc.camera=c; return c
def light(kind, loc, energy, color=(1,1,1), target=None, size=0.1, spot=60):
    L=bpy.data.objects.new("l",bpy.data.lights.new("l",kind)); L.data.energy=energy; L.data.color=color; L.location=loc
    if kind=='SPOT': L.data.spot_size=math.radians(spot); L.data.spot_blend=0.6
    if kind in ('SPOT','POINT'): L.data.shadow_soft_size=size
    if target: d=Vector(target)-Vector(loc); L.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
    sc.collection.objects.link(L); return L
def world(color, strength):
    w=bpy.data.worlds.new("w"); sc.world=w; w.use_nodes=True; b=w.node_tree.nodes['Background']; b.inputs[0].default_value=(*color,1); b.inputs[1].default_value=strength
if scene in ("entrance","entrance_front"):
    load("bunker_entrance")
    bpy.ops.mesh.primitive_plane_add(size=60); g=bpy.context.active_object
    mat=bpy.data.materials.new("g"); mat.use_nodes=True; mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=(0.16,0.17,0.09,1); g.data.materials.append(mat)
    if scene=="entrance": cam((6.5,9.5,2.6),(0,-1.0,1.8),26)
    else: cam((1.2,5.2,1.7),(0,0,1.5),30)
    light('SUN',(0,0,10),2.0,(1,0.92,0.8)).rotation_euler=(0.9,0.2,2.6); world((0.55,0.58,0.62),0.8)
elif scene=="stairs":
    import bmesh
    objs=load("bunker_stairs"); load("bunker_inner_door",(0,3.0-0.15,9.6),math.pi)
    for o in objs:   # разрез: убрать стену со стороны +X
        bm=bmesh.new(); bm.from_mesh(o.data)
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:]+bm.edges[:]+bm.faces[:], plane_co=(1.59,0,0), plane_no=(1,0,0), clear_outer=True)
        bm.to_mesh(o.data); bm.free()
    cam((12.5,4.5,6.8),(0,0,5.6),24)
    light('SUN',(0,0,10),2.5,(1,0.95,0.88)).rotation_euler=(0.7,0.0,1.2)
    light('POINT',(1.0,0,10),300,(1,0.9,0.8),size=1); light('POINT',(1.0,0,4),300,(1,0.9,0.8),size=1)
    world((0.5,0.52,0.55),0.6)
elif scene=="station":
    load("metro_station"); load("bunker_corridor",(-3,-16,0)); load("bunker_stairs",(-3,-23.35,0))
    for i in range(1,4): load("tunnel_10m",(0,12+0.0+5+(i-1)*10,0))
    for i in range(-2,5): load("rail_10m",(0,-7.5+5+i*10,0.27))
    load("handcar",(0,-4.0,0.27)); load("dispenser",(2.2,-7.0,0),math.pi)
    # фары дрезины (как в игре: тёплые споты по ходу)
    light('SPOT',(0.45,-4+1.34,0.27+0.6),400,(1,0.8,0.5),(0.45,20,0.5),0.04,75)
    light('SPOT',(-0.45,-4-1.34,0.27+0.6),200,(1,0.8,0.5),(-0.45,-20,0.5),0.04,75)
    light('POINT',(0,-4,0.27+1.37),12,(1,0.72,0.42),size=0.03)
    cam((-4.8,-11.0,1.7),(0.5,0,1.4),20)
    light('SPOT',(-4.6,-10.8,1.6),90 if MOODY else 500,(1,0.95,0.85),(0.5,-2,1.0),0.05,50 if MOODY else 80)
    if not MOODY: light('POINT',(0,0,4),900,(0.65,0.7,0.75),size=4); light('POINT',(0,15,3),500,(0.65,0.7,0.75),size=3)
    world((0.02,0.02,0.025),0.25)
sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=40
sc.render.resolution_x=1300; sc.render.resolution_y=820; sc.render.filepath=f"{out}/bunker_{scene}{'_moody' if MOODY else ''}.png"
bpy.ops.render.render(write_still=True)
