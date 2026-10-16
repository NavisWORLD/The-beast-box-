"""Playbook #1: sculpt -> retopo -> bake. blender -b X.blend -P sculpt_bake.py -- PLAN OUTDIR
High-res: voxel remesh of the game mesh + layered displacement (fur clumps, paws/face creases,
hat quilting puffs), then Cycles bakes normal (tangent), AO and curvature (pointiness) back onto
the <=25k game mesh's UVs. The game mesh itself is the retopo (fused voxel body, decimated)."""
import bpy,sys,os,math,functools;print=functools.partial(print,flush=True)
a=sys.argv[sys.argv.index('--')+1:];PLAN,OUT=a[0],a[1];os.makedirs(OUT,exist_ok=True)
RES=int(os.environ.get('BAKE_RES','1024'));C=bpy.context;D=bpy.data;sc=C.scene
sc.render.engine='CYCLES';sc.cycles.device='CPU';sc.cycles.samples=int(os.environ.get('BAKE_SAMPLES','16'))
def sel(objs,act):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:o.select_set(True)
    C.view_layer.objects.active=act
def uv(o):
    if os.environ.get('BAKE_UV') and o.data.uv_layers and 'BakeUV' not in o.data.uv_layers:  # projected UVs overlap: unwrap a dedicated bake UV
        rl=[l for l in o.data.uv_layers if l.active_render][0].name;nl=o.data.uv_layers.new(name='BakeUV');o.data.uv_layers.active=nl
        sel([o],o);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.15,island_margin=.004);bpy.ops.object.mode_set(mode='OBJECT')
        o.data.uv_layers[rl].active_render=True;return
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
def quilt(h,lo,mer=8,rows=4,A=.007,G=.0035):
    """stitched puffer pillows: seams follow the build's 8 meridian channels + horizontal rows; each cell inflates
    like a pressurised pillow (sqrt-sine profile), seams are pinched grooves (playbook #5)."""
    import mathutils
    vs=[lo.matrix_world@v.co for v in lo.data.vertices];c=sum(vs,mathutils.Vector())/len(vs)
    zmin=min(v.z for v in vs);zmax=max(v.z for v in vs)
    R=mathutils.Matrix.Rotation(.26,3,'X')  # undo the build's hat tilt so meridians are vertical
    import numpy as np
    n=len(h.data.vertices);N=np.zeros(n*3);h.data.vertices.foreach_get('normal',N);P=np.zeros(n*3);h.data.vertices.foreach_get('co',P);N=N.reshape(-1,3);P=P.reshape(-1,3)
    for i,v in enumerate(h.data.vertices):
        p=R@(v.co-c);az=math.atan2(p.y,p.x);t=(v.co.z-zmin)/max(1e-6,zmax-zmin)
        if t<.18:continue  # band region stays (separate rolled band mesh)
        u=abs(math.sin(az*mer/2));w=abs(math.sin((t-.18)/.82*rows*math.pi))
        pill=(u**.45)*(w**.45);seam=max(0,1-u/.12)+max(0,1-w/.15)
        P[i]+=N[i]*(A*pill-G*min(1,seam))
    h.data.vertices.foreach_set('co',P.ravel());h.data.update()
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
    sc.cycles.samples=32 if kind=='AO' else 8
    if kind=='AO' and sc.world:sc.world.light_settings.distance=.12
    bpy.ops.object.bake(type=t)
    img.filepath_raw=path;img.file_format='PNG';img.save()
    if kind in('AO','CURV'):  # de-speckle low-spp bakes (pro: denoise/blur AO before use)
        import subprocess;subprocess.run(['python3','-c',"from PIL import Image,ImageFilter;import sys;Image.open(sys.argv[1]).filter(ImageFilter.GaussianBlur(float(sys.argv[2]))).save(sys.argv[1])",path,'2' if kind=='AO' else '1'],check=False)
    for m,n in nodes:m.node_tree.nodes.remove(n)
    for m,s in sav.items():
        if s:out=[n for n in m.node_tree.nodes if n.type=='OUTPUT_MATERIAL'][0];m.node_tree.links.new(s,out.inputs[0])
    print('baked',kind,path)
# --- Nyxbean sculpt recipe ---
body=D.objects[os.environ.get('BODY_OBJ','body')];uv(body)
clump=tex('clump','VORONOI',.018,distance_metric='DISTANCE',noise_intensity=1)      # fur clumps (cell tufts)
fine=tex('fine','CLOUDS',.006,noise_depth=2)                                         # strand-group grain
crease=tex('crease','MARBLE',.05,marble_type='SHARPER',noise_depth=3,turbulence=6)    # paw/face skin creases, comb lines
BODY_LAYERS={'res_kairo':[(tex('pore','CLOUDS',.0015,noise_depth=1),.0006,.5),(crease,.0012,.5)],   # skin: pores + soft creases, no fur clumps
 'res_frostmitt':[(clump,.006,.5),(fine,.0025,.5),(crease,.0015,.5)]}.get(PLAN,[(clump,.010,.5),(fine,.004,.5),(crease,.003,.5)])
H=high(body,float(os.environ.get('VOXEL_HI','.0045')),BODY_LAYERS)
for k in ('NORMAL','CURV'):bake(body,H,k,os.path.join(OUT,'%s_body_%s.png'%(PLAN,k.lower())))
bake(body,None,'AO',os.path.join(OUT,'%s_body_ao.png'%PLAN))
D.objects.remove(H,do_unlink=True)
hat=[o for o in sc.objects if o.type=='MESH' and o.name.startswith('prop_crown')]
if hat:
    hat=hat[0];uv(hat)
    puff=tex('puff','VORONOI',.03,distance_metric='DISTANCE_SQUARED')               # quilted pillows between stitches
    knitg=tex('knitg','STUCCI',.004,stucci_type='WALL_OUT')                           # nylon micro-wrinkle
    HH=high(hat,.004,[(knitg,.0012,.5)])
    if PLAN=='res_nyxbean':quilt(HH,hat)
    for k in ('NORMAL','CURV'):bake(hat,HH,k,os.path.join(OUT,'%s_hat_%s.png'%(PLAN,k.lower())))
    bake(hat,HH,'AO',os.path.join(OUT,'%s_hat_ao.png'%PLAN),extr=.012)  # AO from the sculpt: dark stitched seams
    D.objects.remove(HH,do_unlink=True)
for o in sc.objects:
    if o.type=='MESH' and '_render_uv' in o.keys():o.data.uv_layers[o['_render_uv']].active_render=True  # restore the shading UV after baking
if os.environ.get('EXPORT'):
    # carry the bake into the game GLB: hat normal goes into its authored material (runtime keeps pm_* maps);
    # body gets UVs here and the runtime loads tex/bake maps onto its fur shader (SPECIES.baked)
    if hat:
        m=hat.material_slots[0].material.copy();hat.material_slots[0].material=m;bs=[n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'][0]
        nm=[n for n in m.node_tree.nodes if n.type=='NORMAL_MAP']
        if not nm:nm=[m.node_tree.nodes.new('ShaderNodeNormalMap')];m.node_tree.links.new(nm[0].outputs[0],bs.inputs['Normal'])
        ti=m.node_tree.nodes.new('ShaderNodeTexImage');ti.image=D.images.load(os.path.join(OUT,'%s_hat_normal.png'%PLAN));ti.image.colorspace_settings.name='Non-Color'
        m.node_tree.links.new(ti.outputs[0],nm[0].inputs['Color']);nm[0].inputs['Strength'].default_value=1
    bpy.ops.object.select_all(action='DESELECT')
    for o in sc.objects:
        if o.type in('MESH','ARMATURE') and not o.name.endswith('_hi'):o.select_set(True)
    C.view_layer.objects.active=[o for o in sc.objects if o.type=='ARMATURE'][0]
    bpy.ops.export_scene.gltf(filepath=os.environ['EXPORT'],export_format='GLB',use_selection=True,export_skins=True,export_morph=True,export_morph_normal=False,export_animations=False,export_yup=True,export_vertex_color='ACTIVE')
    print('EXPORTED',os.environ['EXPORT'])
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(bpy.data.filepath),'%s_baked.blend'%PLAN))
print('SAVED baked blend')
