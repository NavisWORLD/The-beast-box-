"""Front/side/back turnaround of a beast_build .blend, painted with the resident palette.
blender -b X.blend -P turnaround_render.py -- out.png plan"""
import bpy,sys,json,math,os
from mathutils import Vector
a=sys.argv[sys.argv.index('--')+1:];OUT,PLAN=a[0],a[1]
here=os.path.dirname(os.path.abspath(__file__))
P=[r for r in json.load(open(os.path.join(here,'../../lib/creatures3d/resident-paints.json'))) if r['seed']==PLAN][0]['paint']
def c(h):return tuple(((h>>s)&255)/255 for s in (16,8,0))
def lin(t):return tuple(x**2.2 for x in t)+(1,)
SHOW={'res_frostmitt':('ear_pointy','tail_fluffy'),'res_nyxbean':('tail_thin',),'res_kairo':()}[PLAN]
sc=bpy.context.scene
for o in list(sc.objects):
    if o.type=='MESH' and (o.name.startswith(('ear_','tail_','wing_'))) and o.name.split('.')[0] not in SHOW:o.hide_render=True
for o in list(sc.objects):
    if os.environ.get('HIDE') and o.name.startswith(tuple(os.environ['HIDE'].split(','))):o.hide_render=True
fur=bpy.data.materials.get('fur');nt=fur.node_tree;b=nt.nodes['Principled BSDF']
vc=[n for n in nt.nodes if n.type=='VERTEX_COLOR'][0]
sep=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(vc.outputs['Color'],sep.inputs[0])
mx=nt.nodes.new('ShaderNodeMix');mx.data_type='RGBA';mx.inputs[6].default_value=lin(c(P['base']));mx.inputs[7].default_value=lin(c(P['belly']))
nt.links.new(sep.outputs[0],mx.inputs[0])
mx2=nt.nodes.new('ShaderNodeMix');mx2.data_type='RGBA';mx2.inputs[7].default_value=lin(c(P['accent']))
nt.links.new(mx.outputs[2],mx2.inputs[6]);nt.links.new(sep.outputs[1],mx2.inputs[0]);nt.links.new(mx2.outputs[2],b.inputs['Base Color'])
b.inputs['Roughness'].default_value=.7;b.inputs['Sheen Weight'].default_value=1;b.inputs['Sheen Tint'].default_value=(.7,.55,1,1)
if PLAN=='res_kairo':b.inputs['Sheen Weight'].default_value=.2;b.inputs['Subsurface Weight'].default_value=.25
ey=bpy.data.materials.get('eye')
if ey:
    be=ey.node_tree.nodes['Principled BSDF'];be.inputs['Base Color'].default_value=lin(c(P['glow']));be.inputs['Emission Color'].default_value=lin(c(P['glow']));be.inputs['Emission Strength'].default_value=1.2
cm=bpy.data.materials.get('pm_cornea')
if cm:
    bc=cm.node_tree.nodes['Principled BSDF'];bc.inputs['Transmission Weight'].default_value=0;bc.inputs['Alpha'].default_value=.006;bc.inputs['Roughness'].default_value=0;cm.blend_method='BLEND'
sc.eevee.use_raytracing=True
ir=bpy.data.materials.get('iris')
if ir:
    bi=ir.node_tree.nodes['Principled BSDF'];g=lin(c(P['glow']));bi.inputs['Base Color'].default_value=g;bi.inputs['Emission Color'].default_value=g;bi.inputs['Emission Strength'].default_value=4
gl=bpy.data.materials.get('glow')
if gl:
    bg=gl.node_tree.nodes['Principled BSDF'];g=lin(c(P['glow']));bg.inputs['Emission Color'].default_value=g
sc.render.engine='BLENDER_EEVEE_NEXT';sc.render.resolution_x=int(os.environ.get('RX','640'));sc.render.resolution_y=int(int(os.environ.get('RX','640'))*1.25);sc.render.film_transparent=False
sc.view_settings.view_transform=os.environ.get('VT','Standard');sc.view_settings.look='None'
w=bpy.data.worlds.new('w');sc.world=w;w.use_nodes=True;w.node_tree.nodes['Background'].inputs[0].default_value=(.09,.09,.09,1);w.node_tree.nodes['Background'].inputs[1].default_value=1
def light(n,t,loc,e,col,size=1):
    l=bpy.data.lights.new(n,t);l.energy=e;l.color=col
    if t=='AREA':l.size=size
    o=bpy.data.objects.new(n,l);sc.collection.objects.link(o);o.location=loc;d=Vector((0,0,.5))-Vector(loc);o.rotation_euler=d.to_track_quat('-Z','Y').to_euler();return o
key=light('key','AREA',(-1.6,-2.2,2.2),110,(1,.97,1),4)
rim=light('rim','AREA',(1.8,2.0,1.6),200,(.6,.4,1),2)
rim2=light('rim2','AREA',(-1.9,1.6,1.0),220,(.3,.5,1),1)
fill=light('fill','AREA',(2,-2,.6),90,(.9,.9,1),4)
chest=light('chest','AREA',(0,-1.6,.15),60,(.7,.5,1),1.2)  # low violet rim on the chest tuft
# playbook #8: AgX + strong violet rim (Standard via VT=Standard)
if os.environ.get('VT','AgX')=='AgX':
    sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium High Contrast'
    rim.data.energy=320;rim.data.color=(.62,.42,1);rim2.data.energy=120;rim2.data.color=(.8,.85,1);key.data.energy=170;key.data.color=(1,.98,.95);fill.data.color=(1,1,1);chest.data.energy=20;chest.data.color=(.85,.8,1)
if os.environ.get('NEUTRAL_RIM'):rim.data.color=(1,1,1);rim2.data.color=(1,1,1)
if PLAN=='res_nyxbean':  # neutral black coat: desaturate palette base, grey sheen (violet only from the rim light)
    b.inputs['Sheen Weight'].default_value=.3;b.inputs['Sheen Tint'].default_value=(.55,.55,.6,1)
    hs=nt.nodes.new('ShaderNodeHueSaturation');hs.inputs['Saturation'].default_value=.35;nt.links.new(mx2.outputs[2],hs.inputs['Color']);nt.links.new(hs.outputs[0],b.inputs['Base Color'])
if PLAN=='res_frostmitt':  # white coat: no lavender sheen blowout, albedo kept under 0.6 (pro value-check)
    b.inputs['Sheen Weight'].default_value=.2;b.inputs['Roughness'].default_value=.8
    vm=nt.nodes.new('ShaderNodeMix');vm.data_type='RGBA';vm.blend_type='MULTIPLY';vm.inputs[0].default_value=1;vm.inputs[7].default_value=(.8,.81,.84,1)
    nt.links.new(mx2.outputs[2],vm.inputs[6]);nt.links.new(vm.outputs[2],b.inputs['Base Color'])
if PLAN=='res_frostmitt':  # white fur: albedo ~0.7, tamer key, punchier AgX so the face reads (no haze)
    key.data.energy*=.6;fill.data.energy*=.5;sc.view_settings.exposure=-.35
    if sc.view_settings.view_transform=='AgX':sc.view_settings.look='AgX - High Contrast'
# playbook #1: sculpt->bake maps (normal/AO/curvature) from sculpt_bake.py onto the game mesh
if os.environ.get('FUR_NOEMIT'):  # diagnostic: fur material without emission
    for m_ in bpy.data.materials:
        b_=m_.node_tree.nodes.get('Principled BSDF') if m_.use_nodes and m_.name.startswith(('fur','pm_fur')) else None
        if b_:b_.inputs['Emission Strength'].default_value=0
BK=os.environ.get('BAKED')
def bakemaps(o,pre):
    if not o.data.uv_layers or not os.path.exists(pre+'_normal.png'):return
    for i,sl in enumerate(o.material_slots):
        if not sl.material or not sl.material.use_nodes:continue
        m=sl.material.copy();sl.material=m;t=m.node_tree;bs=[n for n in t.nodes if n.type=='BSDF_PRINCIPLED']
        if not bs:continue
        bs=bs[0]
        def im(f,cs):
            n=t.nodes.new('ShaderNodeTexImage');n.image=bpy.data.images.load(pre+f,check_existing=True);n.image.colorspace_settings.name=cs;return n
        nm=im('_normal.png','Non-Color');mp=t.nodes.new('ShaderNodeNormalMap');mp.inputs[0].default_value=.7
        t.links.new(nm.outputs[0],mp.inputs['Color']);t.links.new(mp.outputs[0],bs.inputs['Normal'])
        ao=im('_ao.png','Non-Color');cv=im('_curv.png','Non-Color')
        src=bs.inputs['Base Color'].links[0].from_socket if bs.inputs['Base Color'].links else None
        m1=t.nodes.new('ShaderNodeMix');m1.data_type='RGBA';m1.blend_type='MULTIPLY';m1.inputs[0].default_value=.85 if PLAN=='res_nyxbean' else .5
        if src:t.links.new(src,m1.inputs[6])
        else:m1.inputs[6].default_value=bs.inputs['Base Color'].default_value
        if PLAN=='res_frostmitt' and pre.endswith('_body'):  # icy blue creases: mix(ice blue, white) by AO
            cr_=t.nodes.new('ShaderNodeMath');cr_.operation='MULTIPLY';t.links.new(ao.outputs[0],cr_.inputs[0]);cr_.inputs[1].default_value=1
            mr=t.nodes.new('ShaderNodeMapRange');mr.inputs[1].default_value=.3;mr.inputs[2].default_value=.55;t.links.new(cv.outputs[0],mr.inputs[0])  # sculpt curvature: concave -> ice blue
            mn_=t.nodes.new('ShaderNodeMath');mn_.operation='MINIMUM';t.links.new(mr.outputs[0],mn_.inputs[0]);t.links.new(cr_.outputs[0],mn_.inputs[1])
            ic=t.nodes.new('ShaderNodeMix');ic.data_type='RGBA';t.links.new(mn_.outputs[0],ic.inputs[0]);ic.inputs[6].default_value=(.55,.68,.92,1);ic.inputs[7].default_value=(1,1,1,1)
            at_=t.nodes.new('ShaderNodeAttribute');at_.attribute_name='frostmask';inv_=t.nodes.new('ShaderNodeMath');inv_.operation='SUBTRACT';inv_.inputs[0].default_value=1;t.links.new(at_.outputs['Fac'],inv_.inputs[1])
            fq=t.nodes.new('ShaderNodeMath');fq.operation='MAXIMUM';t.links.new(mn_.outputs[0],fq.inputs[0]);t.links.new(inv_.outputs[0],fq.inputs[1])  # factor 1 = white;t.links.new(fq.outputs[0],ic.inputs[0])  # no blue frost on the face
            m1.blend_type='MULTIPLY';m1.inputs[0].default_value=1;t.links.new(ic.outputs[2],m1.inputs[7])
        else:t.links.new(ao.outputs[0],m1.inputs[7])
        m2=t.nodes.new('ShaderNodeMix');m2.data_type='RGBA';m2.blend_type='MULTIPLY' if pre.endswith('_hat') else 'OVERLAY';m2.inputs[0].default_value=(.85 if PLAN=='res_frostmitt' else .5) if pre.endswith('_hat') else (0 if PLAN in('res_kairo','res_frostmitt') else .35);t.links.new(m1.outputs[2],m2.inputs[6]);t.links.new(cv.outputs[0],m2.inputs[7])
        t.links.new(m2.outputs[2],bs.inputs['Base Color'])
    print('BAKED maps on',o.name)
if BK:
    for o in list(sc.objects):
        if o.type!='MESH':continue
        if o.name=='body':bakemaps(o,os.path.join(BK,PLAN+'_body'))
        elif o.name.startswith('prop_crown'):bakemaps(o,os.path.join(BK,PLAN+'_hat'))
if os.environ.get('CYCLES','1')=='1':
    # offline look: Cycles + OIDN, strand fur (clumped children + flyaways) on the coat meshes, SSS ears
    sc.render.engine='CYCLES';sc.cycles.samples=int(os.environ.get('SAMPLES','64'));sc.cycles.use_denoising=True;sc.cycles.denoiser='OPENIMAGEDENOISE';sc.cycles.device='CPU'
    FUR={'res_nyxbean':(.024,(.016,.015,.018)),'res_frostmitt':(.085,(.66,.7,.8)),'res_kairo':(0,None)}[PLAN]
    if FUR[0]>0 and not os.environ.get('NOFUR'):
        hm=bpy.data.materials.new('furhair');hm.use_nodes=True;nt2=hm.node_tree;out=nt2.nodes['Material Output']
        for n_ in list(nt2.nodes):
            if n_!=out:nt2.nodes.remove(n_)
        hb=nt2.nodes.new('ShaderNodeBsdfHairPrincipled');hb.parametrization='COLOR' if hasattr(hb,'parametrization') else None
        try:hb.inputs['Color'].default_value=((1,0,0) if os.environ.get('FURDBG') else FUR[1])+(1,)
        except Exception:pass
        hb.inputs['Roughness'].default_value=.35;nt2.links.new(hb.outputs[0],out.inputs['Surface'])
        for o in [o for o in sc.objects if o.type=='MESH' and not o.hide_render and (o.name.startswith(('body','prop_catears')) or o.name.split('.')[0] in SHOW)]:
            o.data.materials.append(hm);slot=len(o.data.materials)
            md=o.modifiers.new('fur','PARTICLE_SYSTEM');ps=md.particle_system.settings;ps.type='HAIR';ps.count=int((34000 if PLAN=='res_frostmitt' else 22000) if o.name.startswith('body') else 3000)
            vgl=o.vertex_groups.new(name='furlen');zt_=max(v.co.z for v in o.data.vertices)
            for v in o.data.vertices:vgl.add([v.index],(max(.8,min(1,.8+(v.co.z/zt_-.3))) if PLAN=='res_frostmitt' else max(.25,min(1,(v.co.z/zt_-.12)*2.2))),'REPLACE')  # Frostmitt: the old ramp left the torso at ~30% length (bald from the side)
            md.particle_system.vertex_group_length='furlen'
            if PLAN=='res_frostmitt' and o.name.startswith('body'):  # keep the face readable: thin, short fur on the front of the face
                vgd=o.vertex_groups.new(name='furdens');vgf=o.vertex_groups.new(name='facefur');vgh=o.vertex_groups.new(name='headfl');fm_=o.data.attributes.new('frostmask','FLOAT','POINT')
                for v in o.data.vertices:
                    face_=v.co.z>zt_*.55 and v.normal.y<-.45 and abs(v.co.x)<zt_*.3  # true front of the face only; cheeks/head sides keep the long coat  # whole front of the head
                    vgd.add([v.index],0 if face_ else 1,'REPLACE');vgf.add([v.index],1 if face_ else 0,'REPLACE');fm_.data[v.index].value=0 if face_ else 1;vgh.add([v.index],(1 if (v.co.z>zt_*.58 and not face_) else 0),'REPLACE')
                    if face_:vgl.add([v.index],.18,'REPLACE')
                md.particle_system.vertex_group_density='furdens'
                mf=o.modifiers.new('facefur','PARTICLE_SYSTEM');pf=mf.particle_system.settings;mf.particle_system.vertex_group_density='facefur'
                pf.type='HAIR';pf.count=30000;pf.hair_length=.036;pf.material=slot;pf.child_type='INTERPOLATED';pf.child_percent=6;pf.rendered_child_count=10
                mh=o.modifiers.new('headfl','PARTICLE_SYSTEM');ph=mh.particle_system.settings;mh.particle_system.vertex_group_density='headfl'  # head/cheek fluff: the main coat lies flat on the head
                ph.type='HAIR';ph.count=4500;ph.hair_length=.135;ph.material=slot;ph.child_type='INTERPOLATED';ph.child_percent=12;ph.rendered_child_count=20
                ph.clump_factor=.85;ph.clump_shape=.2;ph.roughness_1=.03;ph.roughness_2=.1;ph.roughness_2_threshold=.5;ph.child_length=.5;ph.child_length_threshold=.5;ph.use_clump_noise=True;ph.clump_noise_size=.4;ph.roughness_endpoint=.015;ph.radius_scale=.003;ph.root_radius=1;ph.tip_radius=0;ph.render_step=4
                pf.clump_factor=.2;pf.roughness_2=.004;pf.radius_scale=.0012;pf.root_radius=1;pf.tip_radius=0;pf.render_step=3  # short dense velvet face coat (reference: smooth white face)
            ps.hair_length=FUR[0]*(.7 if o.name.startswith('ear') else 1);ps.material=slot;ps.child_type='INTERPOLATED';ps.child_percent=6;ps.rendered_child_count=10
            ps.clump_factor=.55;ps.clump_shape=.3;ps.roughness_1=.012;ps.roughness_2=.025;ps.roughness_2_threshold=.85;ps.roughness_endpoint=.006
            if PLAN=='res_frostmitt':ps.clump_factor=.7;ps.roughness_2=.05;ps.roughness_endpoint=.012;ps.radius_scale=.0021  # fluffy, clumped coat that breaks the silhouette
            ps.use_advanced_hair=False;ps.kink='CURL';ps.kink_amplitude=.002;ps.kink_frequency=3
            if PLAN=='res_frostmitt':ps.radius_scale=.0024;ps.roughness_1=.03;ps.roughness_2=.09;ps.roughness_2_threshold=.6;ps.child_length=.55;ps.child_length_threshold=.45;ps.use_clump_noise=True;ps.clump_noise_size=.4  # uneven clumps break the even shell into a fluffy silhouette
            ps.radius_scale=.0016;ps.root_radius=1;ps.tip_radius=0;ps.display_step=3;ps.render_step=4
            if os.environ.get('NOCST'):raise_=0
            try:
                if os.environ.get('NOCST'):raise RuntimeError('NOCST')  # CST Lorenz clump map drives strand length + clumping
                tx=bpy.data.textures.get('cstclump') or bpy.data.textures.new('cstclump','IMAGE');tx.image=bpy.data.images.load(os.path.join(here,'tex','nyx_fur_clump.png'),check_existing=True)
                sl=ps.texture_slots.add();sl.texture=tx;sl.texture_coords='UV';sl.use_map_time=False;sl.use_map_length=True;sl.length_factor=.6;sl.use_map_clump=True;sl.clump_factor=.8
                for nm_,inf in (('flyaway','rough'),('flow','twist')):  # CST Lorenz flyaway -> strand roughness, Lorenz flow -> twist/comb
                    t2=bpy.data.textures.get('cst'+nm_) or bpy.data.textures.new('cst'+nm_,'IMAGE');t2.image=bpy.data.images.load(os.path.join(here,'tex','nyx_fur_%s.png'%nm_),check_existing=True)
                    s2=ps.texture_slots.add();s2.texture=t2;s2.texture_coords='UV';s2.use_map_time=False
                    if inf=='rough':s2.use_map_rough=True;s2.rough_factor=1.0
                    else:s2.use_map_twist=True;s2.twist_factor=.6;ps.twist=.4
            except Exception as e:print('cst clump slot',e)
            if o.name.startswith('body') and not os.environ.get('NORUFF'):  # long clumped chest + cheek fluff
                vg=o.vertex_groups.new(name='ruffd');hc_=max(v.co.z for v in o.data.vertices)*.62
                for v in o.data.vertices:
                    w_=max(0,min(1,(-v.normal.y-.2)*2))*((1 if v.co.z<hc_*.8 else 0) if PLAN=='res_frostmitt' else (1 if v.co.z<hc_*1.15 else .6))  # Frostmitt: the long ruff rose over the muzzle = the face haze; keep it on the chest  # Frostmitt: chest ruff only, no cheek fluff over the face
                    if w_>0:vg.add([v.index],w_,'REPLACE')
                md2=o.modifiers.new('ruff','PARTICLE_SYSTEM');p2=md2.particle_system.settings;md2.particle_system.vertex_group_density='ruffd'
                p2.type='HAIR';p2.count=5000;p2.hair_length=FUR[0]*(2.3 if PLAN=='res_frostmitt' else 3.8);p2.material=slot;p2.child_type='INTERPOLATED';p2.child_percent=8;p2.rendered_child_count=12
                p2.clump_factor=.85;p2.clump_shape=.5;p2.roughness_2=.03;p2.roughness_2_threshold=.8;p2.roughness_endpoint=.01;p2.radius_scale=.0018;p2.root_radius=1;p2.tip_radius=0;p2.render_step=5
    for m_ in bpy.data.materials:
        if m_.name in('pm_pink','fur','pm_skin_d') and m_.use_nodes:
            bb=m_.node_tree.nodes.get('Principled BSDF')
            if bb:bb.inputs['Subsurface Weight'].default_value=.06 if PLAN=='res_frostmitt' else .35;bb.inputs['Subsurface Radius'].default_value=(1,.3,.3)
bpy.ops.mesh.primitive_plane_add(size=20);fl=bpy.context.active_object;m=bpy.data.materials.new('fl');m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.09,.09,.09,1);m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.95;fl.data.materials.append(m);fl.is_shadow_catcher=True;sc.render.film_transparent=True
ms=[o for o in sc.objects if o.type=='MESH' and not o.hide_render and o!=fl]
zs=[(o.matrix_world@Vector(cn)).z for o in ms for cn in o.bound_box];top=max(zs)
cam=bpy.data.objects.new('cam',bpy.data.cameras.new('cam'));sc.collection.objects.link(cam);sc.camera=cam;cam.data.lens=85
frames=[]
for i,ang in enumerate((0,90,180)):
    r=math.radians(ang);dist=top*float(os.environ.get('FRAME','4.0'));tgt=Vector((0,0,top*.5))
    cam.location=tgt+Vector((math.sin(r)*dist,-math.cos(r)*dist,top*.12));cam.rotation_euler=(tgt-cam.location).to_track_quat('-Z','Y').to_euler()
    for L,base in ((chest,(0,-1.6,.15)),(key,(-1.6,-2.2,2.2)),(rim,(1.8,2.0,1.6)),(rim2,(-1.9,1.6,1.0)),(fill,(2,-2,.6))):
        x,y,z=base;L.location=(x*math.cos(r)-y*math.sin(r),x*math.sin(r)+y*math.cos(r),z);L.rotation_euler=(Vector((0,0,.5))-L.location).to_track_quat('-Z','Y').to_euler()
    f='/tmp/ta_%s%s_%d.png'%(PLAN,os.environ.get('OUTTAG',''),i);sc.render.filepath=f;bpy.ops.render.render(write_still=True);frames.append(f)
print('FRAMES',' '.join(frames))
