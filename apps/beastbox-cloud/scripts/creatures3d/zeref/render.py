import bpy,math,sys,os
from mathutils import Vector
a=sys.argv[sys.argv.index('--')+1:]
OUT=a[0];MODE=a[1] if len(a)>1 else 'sheet';RES=int(a[2]) if len(a)>2 else 640;KEY=a[3] if len(a)>3 else ''
bpy.ops.wm.open_mainfile(filepath=os.path.dirname(os.path.abspath(__file__))+'/zeref.blend')
C=bpy.context;S=C.scene;D=bpy.data
z=D.objects['Zeref']
if KEY and z.data.shape_keys:
    for k in z.data.shape_keys.key_blocks:k.value=1.0 if k.name==KEY else 0
S.render.engine='CYCLES';S.cycles.device='CPU';S.cycles.samples=int(os.environ.get('SAMPLES','48'));S.cycles.use_denoising=False
try:S.cycles.denoiser='OPENIMAGEDENOISE'
except:pass
S.render.resolution_x=RES;S.render.resolution_y=RES;S.render.film_transparent=False
S.view_settings.view_transform='AgX';S.view_settings.look='AgX - Medium High Contrast'
w=D.worlds.new('w');S.world=w;w.use_nodes=True;bg=w.node_tree.nodes['Background'];bg.inputs[0].default_value=(.03,.02,.06,1);bg.inputs[1].default_value=1
# backdrop gradient floor
bpy.ops.mesh.primitive_plane_add(size=30,location=(0,0,0));fl=C.active_object
m=D.materials.new('floor');m.use_nodes=True;b=m.node_tree.nodes['Principled BSDF'];b.inputs['Base Color'].default_value=(.003,.002,.007,1);b.inputs['Roughness'].default_value=.85
fl.data.materials.append(m)
def light(name,loc,energy,color,size=2):
    l=D.lights.new(name,'AREA');l.energy=energy;l.color=color;l.size=size
    o=D.objects.new(name,l);C.collection.objects.link(o);o.location=loc
    d=Vector((0,0,.75))-Vector(loc);o.rotation_euler=d.to_track_quat('-Z','Y').to_euler();return o
light('key',(-2.2,-3,3),260,(1,.95,1),2.5);light('fill',(3,-2,1.6),70,(.75,.7,1),3);light('rim',(1.5,3,2.6),420,(.55,.85,1),2);light('rim2',(-2,2.5,2.2),250,(.8,.55,1),2)
cam=D.cameras.new('cam');cam.lens=60;co=D.objects.new('cam',cam);C.collection.objects.link(co);S.camera=co
tgt=Vector((0,0,.66))
def place(yaw,dist=3.9,h=.95):
    r=math.radians(yaw);co.location=(tgt.x+dist*math.sin(r),tgt.y-dist*math.cos(r),h)
    co.rotation_euler=(tgt-co.location).to_track_quat('-Z','Y').to_euler()
os.makedirs(OUT,exist_ok=True)
if MODE=='sheet':
    for yaw in range(0,360,45):
        place(yaw);S.render.filepath=f'{OUT}/angle_{yaw:03d}.png';bpy.ops.render.render(write_still=True)
elif MODE=='front':
    place(0);S.render.filepath=f'{OUT}/front{("_"+KEY) if KEY else ""}.png';bpy.ops.render.render(write_still=True)
elif MODE=='spin':
    n=int(os.environ.get('FRAMES','48'))
    for i in range(n):
        place(360*i/n);S.render.filepath=f'{OUT}/f_{i:03d}.png';bpy.ops.render.render(write_still=True)
