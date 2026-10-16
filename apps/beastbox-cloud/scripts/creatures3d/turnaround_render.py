"""Front/side/back turnaround of a beast_build .blend, painted with the resident palette.
blender -b X.blend -P turnaround_render.py -- out.png plan"""
import bpy,sys,json,math,os
from mathutils import Vector
a=sys.argv[sys.argv.index('--')+1:];OUT,PLAN=a[0],a[1]
here=os.path.dirname(os.path.abspath(__file__))
P=[r for r in json.load(open(os.path.join(here,'../../lib/creatures3d/resident-paints.json'))) if r['seed']==PLAN][0]['paint']
def c(h):return tuple(((h>>s)&255)/255 for s in (16,8,0))
def lin(t):return tuple(x**2.2 for x in t)+(1,)
SHOW={'res_frostmitt':('ear_pointy','tail_fluffy'),'res_nyxbean':('ear_pointy','tail_thin'),'res_kairo':()}[PLAN]
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
ir=bpy.data.materials.get('iris')
if ir:
    bi=ir.node_tree.nodes['Principled BSDF'];g=lin(c(P['glow']));bi.inputs['Base Color'].default_value=g;bi.inputs['Emission Color'].default_value=g;bi.inputs['Emission Strength'].default_value=4
gl=bpy.data.materials.get('glow')
if gl:
    bg=gl.node_tree.nodes['Principled BSDF'];g=lin(c(P['glow']));bg.inputs['Emission Color'].default_value=g
sc.render.engine='BLENDER_EEVEE_NEXT';sc.render.resolution_x=640;sc.render.resolution_y=800;sc.render.film_transparent=False
sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - High Contrast'
w=bpy.data.worlds.new('w');sc.world=w;w.use_nodes=True;w.node_tree.nodes['Background'].inputs[0].default_value=(.035,.03,.05,1);w.node_tree.nodes['Background'].inputs[1].default_value=1
def light(n,t,loc,e,col,size=1):
    l=bpy.data.lights.new(n,t);l.energy=e;l.color=col
    if t=='AREA':l.size=size
    o=bpy.data.objects.new(n,l);sc.collection.objects.link(o);o.location=loc;d=Vector((0,0,.5))-Vector(loc);o.rotation_euler=d.to_track_quat('-Z','Y').to_euler();return o
key=light('key','AREA',(-1.6,-2.2,2.2),260,(1,.93,.98),1.5)
rim=light('rim','AREA',(1.8,2.0,1.6),420,(.55,.35,1),1.2)
rim2=light('rim2','AREA',(-1.9,1.6,1.0),220,(.3,.5,1),1)
fill=light('fill','AREA',(2,-2,.6),70,(.7,.6,1),2)
bpy.ops.mesh.primitive_plane_add(size=20);fl=bpy.context.active_object;m=bpy.data.materials.new('fl');m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.05,.045,.07,1);m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.6;fl.data.materials.append(m)
ms=[o for o in sc.objects if o.type=='MESH' and not o.hide_render and o!=fl]
zs=[(o.matrix_world@Vector(cn)).z for o in ms for cn in o.bound_box];top=max(zs)
cam=bpy.data.objects.new('cam',bpy.data.cameras.new('cam'));sc.collection.objects.link(cam);sc.camera=cam;cam.data.lens=85
frames=[]
for i,ang in enumerate((0,90,180)):
    r=math.radians(ang);dist=top*4.6;tgt=Vector((0,0,top*.48))
    cam.location=tgt+Vector((math.sin(r)*dist,-math.cos(r)*dist,top*.35));cam.rotation_euler=(tgt-cam.location).to_track_quat('-Z','Y').to_euler()
    for L,base in ((key,(-1.6,-2.2,2.2)),(rim,(1.8,2.0,1.6)),(rim2,(-1.9,1.6,1.0)),(fill,(2,-2,.6))):
        x,y,z=base;L.location=(x*math.cos(r)-y*math.sin(r),x*math.sin(r)+y*math.cos(r),z);L.rotation_euler=(Vector((0,0,.5))-L.location).to_track_quat('-Z','Y').to_euler()
    f='/tmp/ta_%s_%d.png'%(PLAN,i);sc.render.filepath=f;bpy.ops.render.render(write_still=True);frames.append(f)
print('FRAMES',' '.join(frames))
