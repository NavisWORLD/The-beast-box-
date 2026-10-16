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
    bc=cm.node_tree.nodes['Principled BSDF'];bc.inputs['Transmission Weight'].default_value=0;bc.inputs['Alpha'].default_value=.015;cm.blend_method='BLEND'
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
if os.environ.get('CYCLES','1')=='1':
    # offline look: Cycles + OIDN, strand fur (clumped children + flyaways) on the coat meshes, SSS ears
    sc.render.engine='CYCLES';sc.cycles.samples=int(os.environ.get('SAMPLES','64'));sc.cycles.use_denoising=True;sc.cycles.denoiser='OPENIMAGEDENOISE';sc.cycles.device='CPU'
    FUR={'res_nyxbean':(.034,(.02,.012,.03)),'res_frostmitt':(.03,(.85,.88,.95)),'res_kairo':(0,None)}[PLAN]
    if FUR[0]>0:
        hm=bpy.data.materials.new('furhair');hm.use_nodes=True;nt2=hm.node_tree;out=nt2.nodes['Material Output']
        for n_ in list(nt2.nodes):
            if n_!=out:nt2.nodes.remove(n_)
        hb=nt2.nodes.new('ShaderNodeBsdfHairPrincipled');hb.parametrization='COLOR' if hasattr(hb,'parametrization') else None
        try:hb.inputs['Color'].default_value=FUR[1]+(1,)
        except Exception:pass
        hb.inputs['Roughness'].default_value=.35;nt2.links.new(hb.outputs[0],out.inputs['Surface'])
        for o in [o for o in sc.objects if o.type=='MESH' and not o.hide_render and (o.name.startswith(('body','prop_catears')) or o.name.split('.')[0] in SHOW)]:
            o.data.materials.append(hm);slot=len(o.data.materials)
            md=o.modifiers.new('fur','PARTICLE_SYSTEM');ps=md.particle_system.settings;ps.type='HAIR';ps.count=int(22000 if o.name.startswith('body') else 3000)
            ps.hair_length=FUR[0]*(.7 if o.name.startswith('ear') else 1);ps.material=slot;ps.child_type='INTERPOLATED';ps.child_percent=6;ps.rendered_child_count=10
            ps.clump_factor=.55;ps.clump_shape=.3;ps.roughness_1=.012;ps.roughness_2=.025;ps.roughness_2_threshold=.85;ps.roughness_endpoint=.006
            ps.use_advanced_hair=False;ps.kink='CURL';ps.kink_amplitude=.002;ps.kink_frequency=3
            ps.radius_scale=.0016;ps.root_radius=1;ps.tip_radius=0;ps.display_step=3;ps.render_step=4
            if o.name.startswith('body'):  # long clumped chest + cheek fluff
                vg=o.vertex_groups.new(name='ruffd');hc_=max(v.co.z for v in o.data.vertices)*.62
                for v in o.data.vertices:
                    w_=max(0,min(1,(-v.normal.y-.2)*2))*(1 if v.co.z<hc_*1.15 else .6)
                    if w_>0:vg.add([v.index],w_,'REPLACE')
                md2=o.modifiers.new('ruff','PARTICLE_SYSTEM');p2=md2.particle_system.settings;md2.particle_system.vertex_group_density='ruffd'
                p2.type='HAIR';p2.count=5000;p2.hair_length=FUR[0]*2.2;p2.material=slot;p2.child_type='INTERPOLATED';p2.child_percent=8;p2.rendered_child_count=12
                p2.clump_factor=.85;p2.clump_shape=.5;p2.roughness_2=.03;p2.roughness_2_threshold=.8;p2.roughness_endpoint=.01;p2.radius_scale=.0018;p2.root_radius=1;p2.tip_radius=0;p2.render_step=5
    for m_ in bpy.data.materials:
        if m_.name in('pm_pink','fur','pm_skin_d') and m_.use_nodes:
            bb=m_.node_tree.nodes.get('Principled BSDF')
            if bb:bb.inputs['Subsurface Weight'].default_value=.35;bb.inputs['Subsurface Radius'].default_value=(1,.3,.3)
bpy.ops.mesh.primitive_plane_add(size=20);fl=bpy.context.active_object;m=bpy.data.materials.new('fl');m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.09,.09,.09,1);m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.95;fl.data.materials.append(m);fl.is_shadow_catcher=True;sc.render.film_transparent=True
ms=[o for o in sc.objects if o.type=='MESH' and not o.hide_render and o!=fl]
zs=[(o.matrix_world@Vector(cn)).z for o in ms for cn in o.bound_box];top=max(zs)
cam=bpy.data.objects.new('cam',bpy.data.cameras.new('cam'));sc.collection.objects.link(cam);sc.camera=cam;cam.data.lens=85
frames=[]
for i,ang in enumerate((0,90,180)):
    r=math.radians(ang);dist=top*float(os.environ.get('FRAME','4.0'));tgt=Vector((0,0,top*.5))
    cam.location=tgt+Vector((math.sin(r)*dist,-math.cos(r)*dist,top*.12));cam.rotation_euler=(tgt-cam.location).to_track_quat('-Z','Y').to_euler()
    for L,base in ((key,(-1.6,-2.2,2.2)),(rim,(1.8,2.0,1.6)),(rim2,(-1.9,1.6,1.0)),(fill,(2,-2,.6))):
        x,y,z=base;L.location=(x*math.cos(r)-y*math.sin(r),x*math.sin(r)+y*math.cos(r),z);L.rotation_euler=(Vector((0,0,.5))-L.location).to_track_quat('-Z','Y').to_euler()
    f='/tmp/ta_%s_%d.png'%(PLAN,i);sc.render.filepath=f;bpy.ops.render.render(write_still=True);frames.append(f)
print('FRAMES',' '.join(frames))
