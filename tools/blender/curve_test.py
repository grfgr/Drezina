import bpy, math, sys, mathutils
from mathutils import Vector
out = sys.argv[1]; mode = sys.argv[2]
# --- port of DrezinaTrack (Catmull-Rom, step 1 m) ---
nodes = [Vector((0,0,0)), Vector((0,60,0)), Vector((30,100,0)), Vector((80,120,0)), Vector((140,125,0))]
def cr(p0,p1,p2,p3,t):
    t2=t*t; t3=t2*t
    return ((p1*2)+(p2-p0)*t+(p0*2-p1*5+p2*4-p3)*t2+(p1*3-p0-p2*3+p3)*t3)*0.5
pts=[nodes[0]]
n=len(nodes)
for i in range(n-1):
    p0=nodes[max(i-1,0)];p1=nodes[i];p2=nodes[i+1];p3=nodes[min(i+2,n-1)]
    steps=max(1,math.ceil((p2-p1).length/1.0))
    for s in range(1,steps+1): pts.append(cr(p0,p1,p2,p3,s/steps))
cum=[0]
for k in range(1,len(pts)): cum.append(cum[-1]+(pts[k]-pts[k-1]).length)
L=cum[-1]
def posdir(d):
    d=max(0,min(L,d))
    lo=0
    for i in range(len(cum)-1):
        if cum[i]<=d: lo=i
    hi=lo+1; f=(d-cum[lo])/max(cum[hi]-cum[lo],1e-4)
    return pts[lo]+(pts[hi]-pts[lo])*f, (pts[hi]-pts[lo]).normalized()
def straight(d0,d1):
    _,a=posdir(d0+0.01);_,b=posdir(d1-0.01);_,m=posdir((d0+d1)/2)
    return a.dot(b)>0.9995 and a.dot(m)>0.9995
bpy.ops.wm.read_factory_settings(use_empty=True); sc=bpy.context.scene
cache={}
def place(name, pos, dir):
    if name not in cache:
        with bpy.data.libraries.load(f"{out}/{name}.blend") as (src,dst):
            dst.objects=[o for o in src.objects if not o.startswith(("geometry","mem_"))]
        cache[name]=dst.objects
    yaw=math.atan2(-dir.x, dir.y)
    for o in cache[name]:
        c=o.copy(); sc.collection.objects.link(c)
        c.matrix_world=mathutils.Matrix.Translation(pos)@mathutils.Matrix.Rotation(yaw,4,'Z')@o.matrix_world
tStart=20; tEnd=L-20; d=tStart; cnt={"10":0,"2":0}
while d<tEnd-0.01:
    if d+10<=tEnd and straight(d,d+10): name,piece="tunnel_10m",10; cnt["10"]+=1
    else: name,piece="tunnel_2m",2; cnt["2"]+=1
    c=d+piece/2
    if c+piece/2>tEnd: c=tEnd-piece/2
    p,dr=posdir(c); place(name,p,dr); d+=piece
print("pieces",cnt,"len",round(L))
# rails along
d=0
while d<L-0.01:
    if d+10<=L and straight(d,d+10): name,piece="rail_10m",10
    else: name,piece="rail_2m",2
    c=d+piece/2
    if c+piece/2>L: c=max(L-piece/2,piece/2)
    p,dr=posdir(c); place(name,p+Vector((0,0,0.27)),dr); d+=piece
cam=bpy.data.objects.new("cam",bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera=cam
if mode=="top":
    for o in sc.objects:
        if o.type=='MESH' and o.data.name.startswith("tunnel"): pass
    cam.data.type='ORTHO'; cam.data.ortho_scale=150; cam.location=(70,62,120); cam.rotation_euler=(0,0,0)
    # hide roof: clip camera above walls? use clip_start so roof (z<=5.5) visible... cut by moving camera low with clip
    cam.location=(70,62,4.4); cam.data.clip_start=0.01; cam.rotation_euler=(0,0,0); cam.data.clip_end=100
    sun=bpy.data.objects.new("sun",bpy.data.lights.new("sun","SUN")); sun.data.energy=4; sc.collection.objects.link(sun)
    sc.render.resolution_x=1000; sc.render.resolution_y=900
else:
    p,dr=posdir(70); cam.location=p+Vector((-1.5,0,1.8))-dr*2; cam.data.lens=16
    p2,_=posdir(95); dd=(p2+Vector((0,0,1.5)))-cam.location; cam.rotation_euler=dd.to_track_quat('-Z','Y').to_euler()
    for k in range(0,int(L),15):
        p,_=posdir(k); l=bpy.data.objects.new("l",bpy.data.lights.new("l","POINT")); l.data.energy=500; l.data.color=(1,.85,.6); l.location=p+Vector((0,0,4)); sc.collection.objects.link(l)
    sc.render.resolution_x=1100; sc.render.resolution_y=700
w=bpy.data.worlds.new("w"); sc.world=w; w.use_nodes=True; w.node_tree.nodes['Background'].inputs[0].default_value=(0.9,0.2,0.2,1) ; w.node_tree.nodes['Background'].inputs[1].default_value=(1.0 if mode=="top" else 0.3)
sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=20
sc.render.filepath=f"{out}/curve_{mode}.png"; bpy.ops.render.render(write_still=True)
