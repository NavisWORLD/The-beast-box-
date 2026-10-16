"""Playbook #1: sculpt -> retopo -> bake. blender -b X.blend -P sculpt_bake.py -- PLAN OUTDIR
High-res: voxel remesh of the game mesh + layered displacement (fur clumps, paws/face creases,
hat quilting puffs), then Cycles bakes normal (tangent), AO and curvature (pointiness) back onto
the <=25k game mesh's UVs. The game mesh itself is the retopo (fused voxel body, decimated)."""
import bpy,sys,os,math
a=sys.argv[sys.argv.index('--')+1:];PLAN,OUT=a[0],a[1];os.makedirs(OUT,exist_ok=True)
RES=int(os.environ.get('BAKE_RES','1024'));C=bpy.context;D=bpy.data;sc=C.scene
sc.render.engine='CYCLES';sc.cycles.device='CPU';sc.cycles.samples=int(os.environ.get('BAKE_SAMPLES','16'))
def sel(objs,act):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:o.select_set(True)
    C.view_layer.objects.active=act
def uv(o):
    if o.data.uv_layers:return
    sel([o],o);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.15,island_margin=.004);bpy.ops.object.mode_set(mode='OBJECT')
def tex(name,kind,size,**kw):
    t=D.textures.new(name,kind);t.noise_scale=size
    for k,v in kw.items():setattr(t,k,v)
    return t
def high(o,voxel,layers):
    h=o.copy();h.data=o.data.copy();h.name=o.name+'_hi';sc.collection.objects.link(h)
    for m in list(h.modifiers):h.modifiers.remove(m)
    if h.data.shape_keys:
        sel([h],h);bpy.ops.object.shape_key_remove(all=True)
    r=h.modifiers.new('rm','REMESH');r.mode='VOXEL';r.voxel_size=voxel;r.use_smooth_shade=True
    for i,(t,s,mid) in enumerate(layers):
        d=h.modifiers.new('d%d'%i,'DISPLACE');d.texture=t;d.strength=s;d.mid_level=mid;d.texture_coords='OBJECT'
    sm=h.modifiers.new('sm','SMOOTH');sm.factor=.4;sm.iterations=1
    sel([h],h)
    for m in list(h.modifiers):bpy.ops.object.modifier_apply(modifier=m.name)
    print('high',h.name,len(h.data.polygons));return h
def bake(lo,hi,kind,path,extr=.02):
    img=D.images.new(os.path.basename(path),RES,RES,float_buffer=False);img.colorspace_settings.name='Non-Color' if kind!='AO' else 'sRGB'
    mats=[s.material for s in lo.material_slots if s.material]
    nodes=[]
    for m in mats:
        m.use_nodes=True;n=m.node_tree.nodes.new('ShaderNodeTexImage');n.image=img;m.node_tree.nodes.active=n;nodes.append((m,n))
    sav={}
    if kind=='CURV':  # pointiness of the sculpt -> emission
        for m in [s.material for s in hi.material_slots if s.material]:
            nt=m.node_tree;out=[n for n in nt.nodes if n.type=='OUTPUT_MATERIAL'][0];sav[m]=out.inputs[0].links[0].from_socket if out.inputs[0].links else None
            g=nt.nodes.new('ShaderNodeNewGeometry');cr=nt.nodes.new('ShaderNodeMapRange');cr.inputs[1].default_value=.42;cr.inputs[2].default_value=.58
            em=nt.nodes.new('ShaderNodeEmission');nt.links.new(g.outputs['Pointiness'],cr.inputs[0]);nt.links.new(cr.outputs[0],em.inputs[0]);nt.links.new(em.outputs[0],out.inputs[0])
    sel([hi,lo] if hi else [lo],lo)
    bk=sc.render.bake;bk.use_selected_to_active=hi is not None;bk.cage_extrusion=extr;bk.max_ray_distance=extr*2;bk.margin=6
    t={'NORMAL':'NORMAL','AO':'AO','CURV':'EMIT'}[kind]
    sc.cycles.samples=96 if kind=='AO' else 16
    if kind=='AO' and sc.world:sc.world.light_settings.distance=.12
    bpy.ops.object.bake(type=t)
    img.filepath_raw=path;img.file_format='PNG';img.save()
    for m,n in nodes:m.node_tree.nodes.remove(n)
    for m,s in sav.items():
        if s:out=[n for n in m.node_tree.nodes if n.type=='OUTPUT_MATERIAL'][0];m.node_tree.links.new(s,out.inputs[0])
    print('baked',kind,path)
# --- Nyxbean sculpt recipe ---
body=D.objects['body'];uv(body)
clump=tex('clump','VORONOI',.018,distance_metric='DISTANCE',noise_intensity=1)      # fur clumps (cell tufts)
fine=tex('fine','CLOUDS',.006,noise_depth=2)                                         # strand-group grain
crease=tex('crease','MARBLE',.05,marble_type='SHARPER',noise_depth=3,turbulence=6)    # paw/face skin creases, comb lines
H=high(body,float(os.environ.get('VOXEL_HI','.0045')),[(clump,.010,.5),(fine,.004,.5),(crease,.003,.5)])
for k in ('NORMAL','CURV'):bake(body,H,k,os.path.join(OUT,'%s_body_%s.png'%(PLAN,k.lower())))
bake(body,None,'AO',os.path.join(OUT,'%s_body_ao.png'%PLAN))
D.objects.remove(H,do_unlink=True)
hat=[o for o in sc.objects if o.type=='MESH' and o.name.startswith('prop_crown')]
if hat:
    hat=hat[0];uv(hat)
    puff=tex('puff','VORONOI',.03,distance_metric='DISTANCE_SQUARED')               # quilted pillows between stitches
    knitg=tex('knitg','STUCCI',.004,stucci_type='WALL_OUT')                           # nylon micro-wrinkle
    HH=high(hat,.004,[(puff,-.005,.5),(knitg,.0012,.5)])
    for k in ('NORMAL','CURV'):bake(hat,HH,k,os.path.join(OUT,'%s_hat_%s.png'%(PLAN,k.lower())))
    bake(hat,None,'AO',os.path.join(OUT,'%s_hat_ao.png'%PLAN))
    D.objects.remove(HH,do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(bpy.data.filepath),'%s_baked.blend'%PLAN))
print('SAVED baked blend')
