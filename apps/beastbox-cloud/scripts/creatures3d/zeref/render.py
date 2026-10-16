import bpy,math,sys,os
from mathutils import Vector
a=sys.argv[sys.argv.index('--')+1:]
OUT=a[0];MODE=a[1] if len(a)>1 else 'sheet';RES=int(a[2]) if len(a)>2 else 640;KEY=a[3] if len(a)>3 else ''
bpy.ops.wm.open_mainfile(filepath=os.path.dirname(os.path.abspath(__file__))+'/zeref.blend')
C=bpy.context;S=C.scene;D=bpy.data
z=D.objects['Zeref']
if KEY and KEY!='pose' and z.data.shape_keys:
    want=dict((kv.split('=')[0],float(kv.split('=')[1])) if '=' in kv else (kv,1.0) for kv in KEY.split(','))
    for k in z.data.shape_keys.key_blocks:k.value=want.get(k.name,0)
if KEY.startswith('hero') or os.environ.get('HERO'):
    import math as _m
    rig=D.objects['ZerefRig'];pb=rig.pose.bones
    for b in pb:b.rotation_mode='XYZ'
    pb['head'].rotation_euler=(_m.radians(-4),_m.radians(-6),_m.radians(-9))   # mid-thought tilt
    pb['ear.0.R'].rotation_euler=(_m.radians(-14),0,_m.radians(10))            # one ear cocked
    pb['ear.0.L'].rotation_euler=(_m.radians(8),0,_m.radians(-6))
    for i in range(5):pb['tail.%d'%i].rotation_euler=(_m.radians(6),0,_m.radians(-6+i*4))
    if z.data.shape_keys:
        for k in z.data.shape_keys.key_blocks:
            if k.name in ('curious',):k.value=.45
            if k.name=='mouth_smile':k.value=.7
            if k.name=='brows_up':k.value=.25
if KEY=='pose60':
    import math as _m
    rig=D.objects['ZerefRig'];pb=rig.pose.bones
    for b in pb:b.rotation_mode='XYZ'
    pb['neck'].rotation_euler=(0,_m.radians(24),0);pb['head'].rotation_euler=(0,_m.radians(36),0)   # 60 deg split neck/head
if KEY=='pose':
    import math as _m
    rig=D.objects['ZerefRig'];pb=rig.pose.bones
    for b in pb:b.rotation_mode='XYZ'
    pb['head'].rotation_euler=(_m.radians(-18),_m.radians(30),_m.radians(22))
    for i in range(5):pb['tail.%d'%i].rotation_euler=(_m.radians(18),0,_m.radians(25))
    pb['wing.0.L'].rotation_euler=(0,0,_m.radians(-35));pb['wing.0.R'].rotation_euler=(0,0,_m.radians(35))
    pb['ear.0.L'].rotation_euler=(_m.radians(30),0,0)
if os.environ.get('FUR','1')=='1':
    # shell fur (same technique as the runtime three.js shells): offset shells, strand alpha rising per shell, combed down/back
    zz=D.objects['Zeref'];HERE_=os.path.dirname(os.path.abspath(__file__))
    tex=D.images.load(HERE_+'/fur_strands.png');tex.colorspace_settings.name='Non-Color'
    SH=int(os.environ.get('SHELLS','7'));L=float(os.environ.get('FURLEN','.016'))
    base=zz.copy();base.data=zz.data.copy();C.collection.objects.link(base)
    import bmesh as _bm
    if base.data.shape_keys:base.shape_key_clear()
    bm=_bm.new();bm.from_mesh(base.data);gi=base.vertex_groups['FURMASK'].index;dl=bm.verts.layers.deform.active
    _bm.ops.delete(bm,geom=[v for v in bm.verts if gi not in v[dl]],context='VERTS');bm.to_mesh(base.data);bm.free()
    for k in range(1,SH+1):
        t=k/SH;o=base.copy();o.data=base.data.copy();C.collection.objects.link(o)
        d1=o.modifiers.new('n','DISPLACE');d1.direction='NORMAL';d1.mid_level=0;d1.strength=L*t
        d2=o.modifiers.new('g','DISPLACE');d2.direction='Z';d2.mid_level=0;d2.strength=-L*.8*t*t
        bpy.context.view_layer.objects.active=o
        bpy.ops.object.modifier_move_to_index(modifier='n',index=0);bpy.ops.object.modifier_move_to_index(modifier='g',index=1)
        m=D.materials.new('shell%d'%k);m.use_nodes=True;nt=m.node_tree;b=nt.nodes['Principled BSDF']
        vc=nt.nodes.new('ShaderNodeVertexColor');vc.layer_name='Col'
        mul=nt.nodes.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1;mul.inputs[2].default_value=(1.0+.7*t,1.0+.7*t,1.15+.8*t,1)
        nt.links.new(vc.outputs['Color'],mul.inputs[1]);nt.links.new(mul.outputs[0],b.inputs['Base Color'])
        b.inputs['Roughness'].default_value=.55;b.inputs['Sheen Weight'].default_value=.6
        uv=nt.nodes.new('ShaderNodeTexCoord');mp=nt.nodes.new('ShaderNodeMapping');mp.inputs['Scale'].default_value=(14,14,14)
        tx=nt.nodes.new('ShaderNodeTexImage');tx.image=tex
        nt.links.new(uv.outputs['UV'],mp.inputs['Vector']);nt.links.new(mp.outputs[0],tx.inputs['Vector'])
        gt=nt.nodes.new('ShaderNodeMath');gt.operation='GREATER_THAN';gt.inputs[1].default_value=.22+.72*t
        nt.links.new(tx.outputs['Color'],gt.inputs[0]);nt.links.new(gt.outputs[0],b.inputs['Alpha'])
        et=nt.nodes.new('ShaderNodeTexImage');et.image=D.images.load(HERE_+'/fur_emit.png');nt.links.new(uv.outputs['UV'],et.inputs['Vector'])
        nt.links.new(et.outputs['Color'],b.inputs['Emission Color']);b.inputs['Emission Strength'].default_value=1.1
        o.data.materials.clear();o.data.materials.append(m)
    D.objects.remove(base)
S.render.engine='CYCLES';S.cycles.device='CPU';S.cycles.samples=int(os.environ.get('SAMPLES','48'));S.cycles.use_denoising=True
try:S.cycles.denoiser='OPENIMAGEDENOISE'
except:pass
S.render.resolution_x=RES;S.render.resolution_y=RES;S.render.film_transparent=os.environ.get('SIL')=='1'
S.view_settings.view_transform='AgX';S.view_settings.look='AgX - Medium High Contrast'
w=D.worlds.new('w');S.world=w;w.use_nodes=True;bg=w.node_tree.nodes['Background'];bg.inputs[0].default_value=(.03,.02,.06,1);bg.inputs[1].default_value=1
# backdrop gradient floor
bpy.ops.mesh.primitive_plane_add(size=30,location=(0,0,0));fl=C.active_object
if os.environ.get('SIL')=='1':fl.hide_render=True
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
if MODE=='turn':
    for yaw in (0,40,90,180):
        place(yaw);S.render.filepath=f'{OUT}/turn_{yaw:03d}.png';bpy.ops.render.render(write_still=True)
elif MODE=='sheet':
    for yaw in range(0,360,45):
        place(yaw);S.render.filepath=f'{OUT}/angle_{yaw:03d}.png';bpy.ops.render.render(write_still=True)
elif MODE=='front':
    place(0);S.render.filepath=f'{OUT}/front{("_"+KEY.replace(",","+").replace("=","")) if KEY else ""}.png';bpy.ops.render.render(write_still=True)
elif MODE=='spin':
    n=int(os.environ.get('FRAMES','48'))
    for i in range(n):
        place(360*i/n);S.render.filepath=f'{OUT}/f_{i:03d}.png';bpy.ops.render.render(write_still=True)
