"""Spark Beast body-plan GLB builder (headless Blender 4.x), same pipeline as Zeref (scripts/creatures3d/zeref):
fused parts -> voxel remesh -> corrective + laplacian smooth -> decimate (continuous sculpt-like mesh),
label-aware smoothed skin weights on a full armature (spine/neck/head, legs, ear/tail/wing chains for CST spring bones),
a face mesh with REAL shape keys (blink, happy ^^, sleepy, curious, scared, angry, mouth_grin, mouth_o, mouth_w),
mask vertex colours (R belly, G accent: inner ear/paw pads/tail tip, B glow: the species' impossible detail) so the
runtime paints each quantum Beast's own seeded palette + pattern on one shared asset, and part VARIANT meshes
(ear_*, tail_*, wing_*) that the runtime toggles from the genome.
Usage: blender -b --python beast_build.py -- <plan> <out.glb>
Front is -Y, up +Z (glTF export converts to Y-up). ~1.0 unit tall before runtime scale."""
import bpy, bmesh, math, sys, os
from mathutils import Vector
from mathutils.bvhtree import BVHTree
argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['pup','/tmp/pup.glb']
PLAN,OUT=argv[0],argv[1]
VOXEL=float(os.environ.get('VOXEL','0.011'));BODY_TRIS=int(os.environ.get('BODY_TRIS','11000'))
bpy.ops.wm.read_factory_settings(use_empty=True)
C=bpy.context;D=bpy.data
def active(o):
    for x in C.selected_objects:x.select_set(False)
    C.view_layer.objects.active=o;o.select_set(True)
def apply_all(o):
    active(o);bpy.ops.object.convert(target='MESH');bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
def ell(name,loc,r,rot=(0,0,0),seg=40,ring=20):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg,ring_count=ring,radius=1,location=loc,rotation=rot)
    o=C.active_object;o.name=name;o.scale=r;apply_all(o);return o
def cone(name,base,tip,rb,flat=1.0,seg=28,tipr=0.01):
    b=Vector(base);t=Vector(tip);d=t-b
    bpy.ops.mesh.primitive_cone_add(vertices=seg,radius1=rb,radius2=tipr,depth=d.length,location=(b+t)/2)
    o=C.active_object;o.name=name;o.scale=(1,flat,1);o.rotation_mode='QUATERNION';o.rotation_quaternion=Vector((0,0,1)).rotation_difference(d.normalized())
    apply_all(o);return o
def tube(name,pts,radii,res=8,bev=12):
    cu=D.curves.new(name,'CURVE');cu.dimensions='3D';cu.bevel_depth=1.0;cu.bevel_resolution=bev//4;cu.resolution_u=res;cu.use_fill_caps=True
    sp=cu.splines.new('NURBS');sp.points.add(len(pts)-1);sp.use_endpoint_u=True;sp.order_u=min(4,len(pts))
    for p,(x,y,z),r in zip(sp.points,pts,radii):p.co=(x,y,z,1);p.radius=r
    o=D.objects.new(name,cu);C.collection.objects.link(o);apply_all(o);return o
def join(objs,name):
    active(objs[0])
    for o in objs:o.select_set(True)
    bpy.ops.object.join();o=C.active_object;o.name=name;return o
def bvh(o):
    bm=bmesh.new();bm.from_mesh(o.data);t=BVHTree.FromBMesh(bm);bm.free();return t
def fuse(parts,name,voxel=VOXEL,tris=BODY_TRIS,smooth=8):
    """parts: dict label->obj. Returns fused remeshed object + per-vertex labels (nearest pre-fusion part)."""
    pb={k:bvh(o) for k,o in parts.items()}
    o=join(list(parts.values()),name);active(o)
    m=o.modifiers.new('r','REMESH');m.mode='VOXEL';m.voxel_size=voxel;m.adaptivity=0;bpy.ops.object.modifier_apply(modifier='r')
    m=o.modifiers.new('s','CORRECTIVE_SMOOTH');m.factor=.6;m.iterations=smooth;m.use_only_smooth=True;bpy.ops.object.modifier_apply(modifier='s')
    m=o.modifiers.new('l','LAPLACIANSMOOTH');m.lambda_factor=.5;m.iterations=3;m.use_volume_preserve=True;bpy.ops.object.modifier_apply(modifier='l')
    ratio=min(1.0,tris/max(1,len(o.data.polygons)*2));m=o.modifiers.new('d','DECIMATE');m.ratio=ratio;m.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier='d')
    labels=[]
    for v in o.data.vertices:
        best,bd=None,1e9
        for k,t in pb.items():
            h=t.find_nearest(v.co)
            if h[0] is not None and h[3]<bd:bd=h[3];best=k
        labels.append(best)
    for p in o.data.polygons:p.use_smooth=True
    return o,labels
def tris_of(o):return sum(len(p.vertices)-2 for p in o.data.polygons)

# ============================================================ body-plan specs
# Each spec: parts(label->(fn,args)), bones [(name,head,tail,parent)], weights rules, face anchors, variant anchors.
def L(x):return x
def quad(p):
    """Quadruped family: pup, fox, dragonling, axolotl. p = proportions."""
    bl,bh,bw=p['body']; hz=p['head_z']; hr=p['head_r']; leg=p['leg']; ml=p['muzzle']
    by=bl*.9  # half length in Y
    P={}
    P['body']=(ell,((0,.02,leg+bh*.85),(bw,by,bh)))
    P['chest']=(ell,((0,-by*.55,leg+bh*.95),(bw*.92,by*.5,bh*.95)))
    P['rump']=(ell,((0,by*.6,leg+bh*.8),(bw*.95,by*.45,bh*.9)))
    lt=p.get('leg_t',1.0)
    for s,n in ((-1,'L'),(1,'R')):
        for fb,yy in (('F',-by*.62),('B',by*.62)):
            x=s*bw*.55;back=fb=='B'
            # thigh / shoulder mass -> tapered shin with a real knee/hock -> paw with toe beans
            P['leg'+fb+n]=(ell,((x*1.02,yy+(.02 if back else 0),leg+bh*.55),(bw*.42*lt,by*.32*lt,bh*.62)))
            kz=leg*.55;ky=yy+(.035 if back else -.01)
            P['shin'+fb+n]=(tube,([(x,yy,leg+bh*.3),(x*1.01,ky,kz),(x,yy-.005,.07)],[(leg*.3+.03)*lt,(leg*.2+.02)*lt,(leg*.17+.018)*lt]))
            pr=(leg*.22+.03)*lt
            P['paw'+fb+n]=(ell,((x,yy-pr*.35,pr*.62),(pr*1.05,pr*1.35,pr*.66)))
            for k in (-1,0,1):P['toe%s%s%d'%(fb,n,k+1)]=(ell,((x+k*pr*.55,yy-pr*1.25,pr*.42),(pr*.36,pr*.4,pr*.38)))
        P['cheek'+n]=(ell,((s*hr*.5,-by*.75-hr*.5,hz-hr*.22),(hr*.36*p.get('cheek',1),hr*.3,hr*.3*p.get('cheek',1))))
    P['neck']=(ell,((0,-by*.72,leg+bh*1.35),(bw*.6,bw*.55,bh*.6)))
    P['head']=(ell,((0,-by*.75,hz),(hr*1.08,hr*.95,hr*.95)))
    P['muzzle']=(ell,((0,-by*.75-hr*.72-ml*.35,hz-hr*.26),(hr*.3*p.get('muz_w',1),hr*.24+ml*.4,hr*.22*p.get('muz_h',1))))
    hy=-by*.75
    for k,v in p.get('extra',lambda **a:{})(by=by,bh=bh,bw=bw,hz=hz,hr=hr,leg=leg,hy=hy).items():P[k]=v
    B=[('root',(0,0,0),(0,0,.1),None),('hips',(0,by*.55,leg+bh*.8),(0,0,leg+bh*.85),'root'),('spine',(0,0,leg+bh*.85),(0,-by*.6,leg+bh*.95),'hips'),
       ('neck',(0,-by*.6,leg+bh*.95),(0,hy,hz-hr*.6),'spine'),('head',(0,hy,hz-hr*.6),(0,hy,hz+hr*.9),'neck')]
    for s,n in ((-1,'L'),(1,'R')):
        for fb,yy,par in (('F',-by*.62,'spine'),('B',by*.62,'hips')):
            x=s*bw*.55;B+=[('leg%s.0.%s'%(fb,n),(x,yy,leg+bh*.6),(x,yy,leg*.5),par),('leg%s.1.%s'%(fb,n),(x,yy,leg*.5),(x,yy-.02,.03),'leg%s.0.%s'%(fb,n))]
    face=dict(head_c=(0,hy,hz),head_r=(hr*1.08,hr*.95,hr*.95),eye_z=hz+hr*.08,eye_x=hr*.45,eye_r=hr*p.get('eye',.24),mouth_z=hz-hr*.42,nose=True,muzzle_front=hy-hr*.8-ml*.35-(hr*.3+ml*.4))
    ears=dict(at=[(s*hr*.55,hy+hr*.05,hz+hr*.72) for s in (-1,1)],head=(0,hy,hz),hr=hr)
    tail=dict(root=(0,by*(1.0-p.get('tail_in',0)),leg+bh*1.05),dir=p.get('tail_dir',(0,1,1.1)),len=p['tail_len'],r=p['tail_r'],parent='hips')
    wings=dict(at=[(s*bw*.6,-by*.15,leg+bh*1.6) for s in (-1,1)],parent='spine',size=p.get('wing',.3))
    return P,B,face,ears,tail,wings
def fox_x(by,bh,bw,hz,hr,leg,hy):
    # long tapering snout + chest ruff
    return {'snout':(cone,((0,hy-hr*.6,hz-hr*.18),(0,hy-hr*1.6,hz-hr*.36),hr*.42,.85,28,.07)),
            'ruff':(ell,((0,-by*.8,leg+bh*1.25),(bw*1.15,bw*1.0,bh*1.25))),
            'nape':(ell,((0,hy+hr*.2,hz-hr*.55),(hr*.62,hr*.7,hr*.62))),
            'waist':(ell,((0,0,leg+bh*.9),(bw*1.05,by*.75,bh*1.05)))}
def dragon_x(by,bh,bw,hz,hr,leg,hy):
    # brow ridges, jaw, a row of soft dorsal spikes from neck to rump
    d={'browL':(ell,((-hr*.42,hy-hr*.6,hz+hr*.32),(hr*.3,hr*.2,hr*.12))),'browR':(ell,((hr*.42,hy-hr*.6,hz+hr*.32),(hr*.3,hr*.2,hr*.12)))}
    for i in range(6):
        u=i/5;y=-by*.6+u*by*1.5;z=leg+bh*(1.75-.25*abs(u-.4))
        d['spike%d'%i]=(cone,((0,y,z-.06),(0,y+.05,z+.07-.03*abs(u-.4)),.05-.012*abs(u-.4),.45))
    return d
def axo_x(by,bh,bw,hz,hr,leg,hy):
    return {'jaw':(ell,((0,hy-hr*.35,hz-hr*.35),(hr*1.15,hr*.7,hr*.45)))}
SPECS={
 'pup':lambda:quad(dict(body=(.36,.2,.21),head_z=.86,head_r=.3,leg=.2,muzzle=.05,tail_len=.36,tail_r=.08,eye=.3)),
 'fox':lambda:quad(dict(body=(.44,.15,.145),head_z=.9,head_r=.24,leg=.3,leg_t=.72,muzzle=.04,muz_w=.75,muz_h=.8,cheek=.75,tail_len=.78,tail_r=.13,eye=.24,tail_dir=(0,1,.35),tail_in=.22,extra=fox_x)),
 'dragonling':lambda:quad(dict(body=(.40,.2,.21),head_z=.84,head_r=.27,leg=.2,leg_t=1.15,muzzle=.14,muz_w=1.05,cheek=.6,tail_len=.7,tail_r=.09,eye=.24,tail_dir=(0,1,.18),wing=.55,extra=dragon_x)),
 'axolotl':lambda:quad(dict(body=(.5,.13,.19),head_z=.36,head_r=.27,leg=.1,leg_t=.8,muzzle=.0,muz_w=1.6,muz_h=.7,cheek=.4,tail_len=.6,tail_r=.09,eye=.17,tail_dir=(0,1,.05),extra=axo_x)),
}
if PLAN not in SPECS:raise SystemExit('plan not built yet: '+PLAN)
P,B,FACE,EARS,TAIL,WINGS=SPECS[PLAN]()
parts={k:fn(k,*a) for k,(fn,a) in P.items()}
body,labels=fuse(parts,'body')
print('body tris',tris_of(body))
body_bvh=bvh(body)

# ============================================================ face (eyes, catchlights, nose, mouth) with shape keys
hc=Vector(FACE['head_c']);hr=Vector(FACE['head_r'])
def surf(x,z,y0=-3):
    h=body_bvh.ray_cast(Vector((x,y0,z)),Vector((0,1,0)));return h[0] if h[0] else Vector((x,hc.y-hr.y,z))
face_objs=[];groups={}
GNAMES=['eyeL','eyeR','irisL','irisR','shineL','shineR','mouth','mouthin','nose','tongue']
def add_face(o,group):
    face_objs.append(o);groups.setdefault(group,[]).append(o.name)
    a=o.data.attributes.new('grp','INT','POINT')
    for i in range(len(o.data.vertices)):a.data[i].value=GNAMES.index(group)
ER=FACE['eye_r']
eye_c={}
for s,n in ((-1,'L'),(1,'R')):
    x,z=s*FACE['eye_x'],FACE['eye_z'];p=surf(x,z);c=Vector((x,p.y+ER*.05,z));eye_c[n]=c
    e=ell('eye'+n,c,(ER*.85,ER*.5,ER),seg=32,ring=16);add_face(e,'eye'+n)
    i=ell('iris'+n,c+Vector((0,-ER*.3,-ER*.22)),(ER*.5,ER*.2,ER*.55),seg=20,ring=10);add_face(i,'iris'+n)
    sh=ell('shine'+n,c+Vector((-s*ER*.25,-ER*.42,ER*.4)),(ER*.22,ER*.08,ER*.22),seg=12,ring=6);add_face(sh,'shine'+n)
    sh2=ell('shineb'+n,c+Vector((s*ER*.22,-ER*.42,-ER*.35)),(ER*.09,ER*.05,ER*.09),seg=8,ring=4);add_face(sh2,'shine'+n)
mz=FACE['mouth_z'];mp=surf(0,mz);mouth_c=Vector((0,mp.y-.002,mz))
# visible mouth: a soft 'w' smile line that hugs the muzzle surface, plus a dark mouth cavity + tongue that open with mouth_o
MW=FACE.get('mouth_w',.75)*ER
mpts=[]
for k in range(9):
    u=k/8*2-1;x=u*MW;z=mz+ER*.18*(u*u)-ER*.1*math.exp(-(u*u)/.04)*0+ER*.07*math.cos(u*math.pi*2)*.6
    mpts.append(tuple(surf(x,z)+Vector((0,-.011,0))))
mo=tube('mouth',mpts,[ER*.1]*9,res=6,bev=8);add_face(mo,'mouth')
mi=ell('mouthin',mouth_c+Vector((0,.012,-ER*.12)),(MW*.42,ER*.06,ER*.16),seg=20,ring=10);add_face(mi,'mouthin')
tg=ell('tongue',mouth_c+Vector((0,.014,-ER*.2)),(MW*.26,ER*.05,ER*.09),seg=14,ring=8);add_face(tg,'tongue')
if FACE.get('nose'):
    np_=surf(0,mz+ER*.75);no=ell('nose',np_+Vector((0,.006,0)),(ER*.36,ER*.2,ER*.24),seg=16,ring=8);add_face(no,'nose')
def mat(name,base,rough=.5,metal=0,emit=None,es=0,vc=False,coat=0,sheen=0):
    m=D.materials.new(name);m.use_nodes=True;b=m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value=base;b.inputs['Roughness'].default_value=rough;b.inputs['Metallic'].default_value=metal
    if coat:b.inputs['Coat Weight'].default_value=coat
    if sheen:b.inputs['Sheen Weight'].default_value=sheen
    if emit:b.inputs['Emission Color'].default_value=emit;b.inputs['Emission Strength'].default_value=es
    if vc:
        a=m.node_tree.nodes.new('ShaderNodeVertexColor');a.layer_name='Col';m.node_tree.links.new(a.outputs['Color'],b.inputs['Base Color'])
    return m
M={'fur':mat('fur',(1,1,1,1),.8,vc=True,sheen=1),'eye':mat('eye',(.02,.02,.05,1),.05,coat=1),'iris':mat('iris',(.4,.8,1,1),.3,emit=(.4,.8,1,1),es=2),
   'shine':mat('shine',(1,1,1,1),.2,emit=(1,1,1,1),es=4),'mouth':mat('mouth',(.12,.03,.07,1),.6),'mouthin':mat('mouthin',(.06,.01,.03,1),.7),'tongue':mat('tongue',(.85,.35,.45,1),.45),'nose':mat('nose',(.08,.05,.09,1),.25,coat=.8),'glow':mat('glow',(1,.9,.6,1),.3,emit=(1,.9,.6,1),es=3)}
def setmat(o,m):o.data.materials.clear();o.data.materials.append(m)
for o in face_objs:setmat(o,M['eye' if o.name.startswith('eye') else 'iris' if o.name.startswith('iris') else 'shine' if o.name.startswith('shine') else o.name])
face=join(face_objs,'face')
# vertex groups by original object -> after join we tag by proximity to the creation centres
fv=face.data.vertices
_ga=face.data.attributes['grp']
fgroup=[GNAMES[_ga.data[i].value] for i in range(len(fv))]
# shape keys
face.shape_key_add(name='Basis')
def key(name,fn):
    k=face.shape_key_add(name=name,from_mix=False)
    for i,v in enumerate(fv):
        co=fn(v.co.copy(),fgroup[i]);k.data[i].co=co
def eye_op(f):
    def g(co,grp):
        if grp.startswith('eye'):
            n=grp[-1];c=eye_c[n];s=-1 if n=='L' else 1;return f(co,c,s)
        return co
    return g
def flat(co,c,k,dz=0):return Vector((co.x,co.y,c.z+(co.z-c.z)*k+dz))
key('blink',eye_op(lambda co,c,s:flat(co,c,.06,-ER*.1)))
key('happy',eye_op(lambda co,c,s:Vector((co.x,co.y,c.z+(co.z-c.z)*.14+ER*.45*(1-((co.x-c.x)/(ER*.82))**2)-ER*.2))))
key('sleepy',eye_op(lambda co,c,s:flat(co,c,.35,-ER*.35)))
key('curious',eye_op(lambda co,c,s:c+(co-c)*(1.18 if s<0 else .86)))
key('scared',eye_op(lambda co,c,s:c+(co-c)*1.22))
key('angry',eye_op(lambda co,c,s:Vector((co.x,co.y,min(co.z,c.z+ER*.55-(co.x-c.x)*s*1.1)))))
def mouth_op(f):
    def g(co,grp):
        if grp=='mouth':return f(co)
        if grp in('mouthin','tongue'):return co
        return co
    return g
mc=mouth_c
def grin_open(co,grp):
    if grp=='mouthin':return Vector((mc.x+(co.x-mc.x)*1.5,co.y-.013,mc.z-ER*.1+(co.z-mc.z+ER*.12)*1.1))
    if grp=='tongue':return Vector((co.x,co.y-.008,co.z-ER*.04))
    return co
key('mouth_grin',lambda co,grp:grin_open(co,grp) if grp!='mouth' else (lambda co:Vector((mc.x+(co.x-mc.x)*1.35,co.y,mc.z+(co.z-mc.z)+ER*.35*((co.x-mc.x)/(ER*.9))**2)))(co))
def mouth_open(co,grp):
    if grp=='mouth':return Vector((mc.x+(co.x-mc.x)*.6,co.y,mc.z+(co.z-mc.z)*1.0+ER*.05*(1 if co.z>mc.z else -1)))
    if grp=='mouthin':return Vector((mc.x+(co.x-mc.x)*.95,co.y-.016,mc.z-ER*.08+(co.z-mc.z+ER*.12)*2.6))
    if grp=='tongue':return Vector((co.x,co.y-.014,co.z-ER*.06))
    return co
key('mouth_o',mouth_open)
key('mouth_w',mouth_op(lambda co:Vector((mc.x+(co.x-mc.x)*1.35,co.y,co.z+ER*.22*math.cos((co.x-mc.x)/(ER*.55)*math.pi*1.5)))))
for p in face.data.polygons:p.use_smooth=True

# ============================================================ variant parts (ears / tail / wings) + impossible detail
variants={}
def variant(name,objs,voxel=VOXEL*.8,tris=1800):
    o,lab=fuse({('%s_%d'%(name,i)):x for i,x in enumerate(objs)},name,voxel=voxel,tris=tris,smooth=4);variants[name]=o;return o
EA=EARS['at'];ehr=EARS['hr']
def ear_tip(a,s,h,out=.35):return (a[0]+s*h*out,a[1]+h*.08,a[2]+h)
variant('ear_pointy',[cone('e',a,ear_tip(a,s,ehr*1.0),ehr*.42,flat=.42) for a,s in zip(EA,(-1,1))])
variant('ear_round',[ell('e',(a[0]+s*ehr*.12,a[1],a[2]+ehr*.28),(ehr*.38,ehr*.16,ehr*.36)) for a,s in zip(EA,(-1,1))])
variant('ear_floppy',[tube('e',[a,(a[0]+s*ehr*.45,a[1]-ehr*.05,a[2]+ehr*.05),(a[0]+s*ehr*.62,a[1]-ehr*.12,a[2]-ehr*.45)],[ehr*.2,ehr*.24,ehr*.16]) for a,s in zip(EA,(-1,1))])
variant('ear_horns',[cone('e',a,ear_tip(a,s,ehr*.85,.5),ehr*.16,flat=1) for a,s in zip(EA,(-1,1))])
variant('ear_leaf',[ell('e',(a[0]+s*ehr*.2,a[1],a[2]+ehr*.45),(ehr*.18,ehr*.06,ehr*.5),rot=(0,s*-.4,0)) for a,s in zip(EA,(-1,1))])
variant('ear_feelers',[tube('e',[a,(a[0]+s*ehr*.2,a[1]-ehr*.2,a[2]+ehr*.7),(a[0]+s*ehr*.45,a[1]-ehr*.45,a[2]+ehr*1.1)],[ehr*.05,ehr*.04,ehr*.1]) for a,s in zip(EA,(-1,1))])
variant('ear_gills',[cone('e',(s*ehr*1.0,EARS['head'][1],EARS['head'][2]-ehr*.1+k*ehr*.25),(s*ehr*1.6,EARS['head'][1]+ehr*.15,EARS['head'][2]+k*ehr*.45),ehr*.08,flat=.5) for s in (-1,1) for k in (-1,0,1)])
# crown: ring of five points on the head (accent metal, glow tips)
hcx,hcy,hcz=EARS['head'];cr=[]
for k in range(5):
    a=k/5*2*math.pi;x,y=math.cos(a)*ehr*.42,math.sin(a)*ehr*.42;cr.append(cone('c',(x,hcy+y,hcz+ehr*.86),(x*1.1,hcy+y*1.1,hcz+ehr*1.22),ehr*.1,flat=1))
cr.append(tube('c',[(math.cos(a)*ehr*.44,hcy+math.sin(a)*ehr*.44,hcz+ehr*.87) for a in [k/12*2*math.pi for k in range(13)]],[ehr*.05]*13))
variant('ear_crown',cr)
# tail chain
tr=Vector(TAIL['root']);td=Vector(TAIL['dir']).normalized();tl=TAIL['len'];trad=TAIL['r']
def tail_pts(curl=.0,n=6):
    pts=[];side=Vector((1,0,0))
    for i in range(n):
        u=i/(n-1);p=tr+td*tl*u;p+= Vector((0,0,1))*math.sin(u*math.pi)*tl*.15+Vector((0,-1,0))*curl*u*u*tl;pts.append(tuple(p))
    return pts
TP=tail_pts()
variant('tail_fluffy',[tube('t',TP,[trad*.6,trad*1.0,trad*1.25,trad*1.2,trad*.9,trad*.45])])
variant('tail_thin',[tube('t',TP,[trad*.55,trad*.5,trad*.42,trad*.35,trad*.28,trad*.2])])
variant('tail_flame',[tube('t',TP[:5],[trad*.55,trad*.5,trad*.42,trad*.4,trad*.3]),cone('f',TP[4],tuple(Vector(TP[5])+td*trad*2),trad*.7,flat=.6)])
variant('tail_fin',[tube('t',TP,[trad*.7,trad*.62,trad*.5,trad*.4,trad*.3,trad*.2]),ell('f',TP[4],(trad*.15,trad*2.6,trad*1.6))])
# wings (chain root→tip)
WA=WINGS['at'];ws=WINGS['size']
def wing_feather(a,s):
    out=[]
    for k in range(4):
        ang=.35+k*.33;L=ws*(1-k*.13);base=Vector(a);tip=base+Vector((s*math.cos(ang)*L,.12*L,math.sin(ang)*L*.8))
        out.append(ell('w',tuple((base+tip)/2),(L*.5,.025,L*.12),rot=(0,-s*ang,0)))
    return out
def wing_bat(a,s):
    base=Vector(a);out=[]
    for k in range(3):
        ang=.2+k*.45;tip=base+Vector((s*math.cos(ang)*ws,.1*ws,math.sin(ang)*ws*.85))
        out.append(tube('b',[tuple(base),tuple((base+tip)/2+Vector((0,0,.03))),tuple(tip)],[.022,.018,.01]))
    out.append(ell('m',tuple(base+Vector((s*ws*.42,.05*ws,ws*.3))),(ws*.42,.012,ws*.3),rot=(0,-s*.5,0)))
    return out
variant('wing_feather',[x for a,s in zip(WA,(-1,1)) for x in wing_feather(a,s)])
variant('wing_bat',[x for a,s in zip(WA,(-1,1)) for x in wing_bat(a,s)])
variant('wing_moth',[ell('m',(a[0]+s*ws*.55,a[1]+.03,a[2]+ws*.15),(ws*.6,.015,ws*.5),rot=(0,-s*.3,0)) for a,s in zip(WA,(-1,1))]+[ell('m',(a[0]+s*ws*.38,a[1]+.06,a[2]-ws*.25),(ws*.38,.012,ws*.3),rot=(0,s*.4,0)) for a,s in zip(WA,(-1,1))])
# ---- species-defining parts (always shown for that species; the genome still paints them)
def raw_variant(name,objs,tris=2400):
    o=join(objs,name);active(o)
    m=o.modifiers.new('t','TRIANGULATE');bpy.ops.object.modifier_apply(modifier='t')
    if len(o.data.polygons)>tris:
        m=o.modifiers.new('d','DECIMATE');m.ratio=tris/len(o.data.polygons);bpy.ops.object.modifier_apply(modifier='d')
    for p_ in o.data.polygons:p_.use_smooth=True
    variants[name]=o;return o
if PLAN=='fox':
    # tall alert ears with a cupped inner bowl, and a huge brush tail
    eo=[]
    for a,s_ in zip(EA,(-1,1)):
        eo.append(cone('e',a,(a[0]+s_*ehr*.42,a[1]+ehr*.12,a[2]+ehr*1.45),ehr*.5,flat=.4,tipr=.012))
    variant('ear_fox',eo,tris=2200)
    BP=tail_pts(n=7)
    variant('tail_brush',[tube('t',BP,[trad*.55,trad*1.15,trad*1.7,trad*1.95,trad*1.8,trad*1.25,trad*.35],res=10)],tris=2600)
if PLAN=='dragonling':
    ho=[]
    for a,s_ in zip(EA,(-1,1)):
        b=Vector(a)+Vector((0,.02,-.02))
        ho.append(tube('h',[tuple(b),tuple(b+Vector((s_*ehr*.25,ehr*.35,ehr*.55))),tuple(b+Vector((s_*ehr*.35,ehr*.9,ehr*.75))),tuple(b+Vector((s_*ehr*.3,ehr*1.25,ehr*.6)))],[ehr*.16,ehr*.12,ehr*.07,ehr*.015],res=8))
        for r_ in range(4):  # growth rings
            u=.15+r_*.17;q=Vector(b)+Vector((s_*ehr*.25,ehr*.35,ehr*.55))*u*2.2 if u<.45 else b+Vector((s_*ehr*.3,ehr*.7,ehr*.7))
    variant('ear_dhorn',ho,voxel=VOXEL*.6,tris=2000)
    # membrane wings: 3 finger bones + arm, with a real scalloped skin membrane between them (solidified, not voxelised)
    wo=[]
    for a,s_ in zip(WA,(-1,1)):
        base=Vector(a);elbow=base+Vector((s_*ws*.38,.06*ws,ws*.42));tips=[]
        wo.append(tube('arm',[tuple(base),tuple(elbow)],[.028,.02],res=6))
        for k,(ang,L_) in enumerate(((.95,.75),(.45,.85),(-.05,.7))):
            tip=elbow+Vector((s_*math.cos(ang)*ws*L_,.1*ws+k*.06*ws,math.sin(ang)*ws*L_*.9));tips.append(tip)
            wo.append(tube('f',[tuple(elbow),tuple((elbow+tip)/2+Vector((0,0,.02))),tuple(tip)],[.017,.012,.004],res=6))
        claw=elbow+Vector((0,0,.03));wo.append(cone('c',tuple(elbow),tuple(claw+Vector((s_*.01,-.02,.04))),.014,1))
        me=D.meshes.new('mem');bm=bmesh.new()
        root2=base+Vector((s_*.02,ws*.35,-.02))  # trailing edge meets the flank
        rim=[elbow]+[x for t_ in tips for x in (t_,)]
        pts=[elbow]
        for k in range(len(tips)):
            pts.append(tips[k])
            nxt=tips[k+1] if k+1<len(tips) else root2
            mid=(tips[k]+nxt)/2;inward=(elbow-mid)*.22;pts.append(mid+inward)   # scallop
        pts.append(root2);pts.append(base)
        cvs=[bm.verts.new(tuple(elbow))]
        ring=[bm.verts.new(tuple(x)) for x in pts[1:]]
        for k in range(len(ring)-1):bm.faces.new((cvs[0],ring[k],ring[k+1]))
        bmesh.ops.subdivide_edges(bm,edges=bm.edges[:],cuts=3,use_grid_fill=True)
        bmesh.ops.triangulate(bm,faces=bm.faces[:])
        bm.to_mesh(me);bm.free();mo_=D.objects.new('mem',me);C.collection.objects.link(mo_)
        sm=mo_.modifiers.new('s','SOLIDIFY');sm.thickness=.007;sm.offset=0;active(mo_);bpy.ops.object.modifier_apply(modifier='s')
        sb=mo_.modifiers.new('b','SMOOTH');sb.iterations=4;sb.factor=.5;bpy.ops.object.modifier_apply(modifier='b')
        wo.append(mo_)
    raw_variant('wing_dragon',wo,tris=3200)
if PLAN=='axolotl':
    # three feathery gill stalks per side, each fringed with soft filaments (the frill), and a tall ribbon tail fin
    go=[]
    hx,hy_,hz_=EARS['head']
    for s_ in (-1,1):
        for k,(dz,ang) in enumerate(((.32,.55),(.05,.15),(-.2,-.25))):
            b=Vector((s_*ehr*.92,hy_+ehr*.15,hz_+ehr*dz));d=Vector((s_*math.cos(ang),.35,math.sin(ang)+.25)).normalized();L_=ehr*(.75-abs(k-1)*.12)
            pts=[b+d*L_*u+Vector((0,0,math.sin(u*2.4)*ehr*.08)) for u in (0,.35,.7,1)]
            go.append(tube('g',[tuple(x) for x in pts],[ehr*.07,ehr*.06,ehr*.045,ehr*.02],res=6))
            for j in range(7):
                u=.2+j*.12;c_=pts[0].lerp(pts[3],u)
                for side in (-1,1):
                    fd=Vector((0,side*.7,0))+Vector((0,0,.5))+d*.3
                    go.append(ell('fl',tuple(c_+fd.normalized()*ehr*.11),(ehr*.035,ehr*.05,ehr*.11),rot=(side*.7,0,0),seg=10,ring=6))
    raw_variant('ear_frill',go,tris=3000)
    FP=tail_pts()
    fin=[tube('t',FP,[trad*.85,trad*.75,trad*.6,trad*.45,trad*.3,trad*.15])]
    for k in range(10):
        u=k/9;c_=Vector(FP[0]).lerp(Vector(FP[-1]),u);hh=trad*(2.2*math.sin(min(1,u*1.3)*math.pi*.9)+.4)
        fin.append(ell('fin',tuple(c_+Vector((0,0,0))),(trad*.12,tl*.07,hh)))
    variant('tail_axfin',fin,voxel=VOXEL*.6,tris=2600)
# IMPOSSIBLE DETAIL (per species): a tiny comet for the pup's tail tip, ember-heart for dragonling, etc.
DETAIL={'pup':'comet','fox':'foxfire','dragonling':'ember_heart','axolotl':'tide_halo'}
dk=DETAIL.get(PLAN,'comet')
if dk=='comet':dt=[ell('d',tuple(Vector(TP[-1])+td*trad*1.4),(trad*.55,trad*.55,trad*.55),seg=20,ring=10)]+[ell('d',tuple(Vector(TP[-1])+td*trad*(2.2+k*.9)-Vector((0,0,k*.02))),(trad*.3*(1-k*.25),)*3,seg=10,ring=6) for k in range(3)]
elif dk=='foxfire':dt=[ell('d',tuple(Vector(TP[-1])+Vector((s*.12,0,.15))),(.04,.04,.07),seg=14,ring=8) for s in (-1,0,1)]
elif dk=='ember_heart':dt=[ell('d',(0,-.1,.62),(.06,.03,.06),seg=16,ring=8)]
else:dt=[tube('d',[(math.cos(a)*.22,EARS['head'][1]+math.sin(a)*.22,EARS['head'][2]+.36) for a in [k/16*2*math.pi for k in range(17)]],[.012]*17)]
detail=join(dt,'detail');setmat(detail,M['glow'])

# ============================================================ mask vertex colours
def masks(o,fn):
    me=o.data
    if 'Col' in me.color_attributes:me.color_attributes.remove(me.color_attributes['Col'])
    a=me.color_attributes.new('Col','FLOAT_COLOR','POINT')
    for v in me.vertices:a.data[v.index].color=fn(v.co,v.normal)
    me.color_attributes.active_color=a
def body_mask(co,n,i=None):
    lab=labels[i] if i is not None else ''
    belly=max(0,min(1,(-n.z*.6-n.y*.8+.1)*1.6)) if (co.z<FACE['head_c'][2]-hr.z*.3) else max(0,min(1,(-n.y-.55)*3))*(1 if lab=='muzzle' or lab.startswith('cheek') else .6)
    accent=1.0 if (lab.startswith('paw') or lab.startswith('toe')) and n.z<-.2 else 0.0
    # A = fur length multiplier (short fur on muzzle/face front/paws, none on dragon belly scales and spikes)
    fl=1.0
    if lab in('muzzle','snout','jaw') or lab.startswith('cheek') or lab.startswith('brow'):fl=.28
    elif lab=='head' and n.y<-.45:fl=.4
    elif lab.startswith('paw') or lab.startswith('toe'):fl=.45
    elif lab=='ruff':fl=1.6
    if PLAN=='dragonling':
        if lab.startswith('spike'):fl=0;accent=1.0
        elif belly>.35 and co.z<FACE['head_c'][2]-hr.z*.3:fl=0
    return (belly,accent,0.0,fl/1.6)
me=body.data;a=me.color_attributes.new('Col','FLOAT_COLOR','POINT')
for v in me.vertices:a.data[v.index].color=body_mask(v.co,v.normal,v.index)
me.color_attributes.active_color=a;setmat(body,M['fur'])
for nm,o in variants.items():
    FL={'ear_dhorn':0,'wing_dragon':0,'ear_horns':0,'ear_crown':0,'ear_frill':.5,'tail_brush':1.0,'ear_fox':.55}.get(nm,.62)
    if nm.startswith('ear'):masks(o,lambda co,n:(0,1.0 if (n.y<-.4 and nm in('ear_pointy','ear_round','ear_floppy','ear_fox')) else (.6 if nm in('ear_crown','ear_frill') else 0),1.0 if nm in('ear_crown',) and co.z>EARS['head'][2]+ehr*1.1 else 0,FL*(.2 if n.y<-.4 and nm=='ear_fox' else 1)))
    elif nm.startswith('tail'):masks(o,lambda co,n:(0,max(0,min(1,((co-tr).dot(td)/tl-(.62 if nm=='tail_brush' else .75))*4)),1.0 if nm=='tail_flame' and (co-tr).dot(td)/tl>.8 else 0,FL))
    else:masks(o,lambda co,n:(0,.5 if nm=='wing_moth' else (.35 if nm=='wing_dragon' else 0),0,FL))
    setmat(o,M['fur'])
# smart UVs for the fur strand texture (runtime shells)
for o in [body]+list(variants.values()):
    active(o);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.15,island_margin=.01);bpy.ops.object.mode_set(mode='OBJECT')

# ============================================================ armature
arm=D.armatures.new('BeastRig');rig=D.objects.new('BeastRig',arm);C.collection.objects.link(rig)
active(rig);bpy.ops.object.mode_set(mode='EDIT');EB=arm.edit_bones
def bone(name,h,t,parent=None):
    b=EB.new(name);b.head=h;b.tail=t
    if parent:b.parent=EB[parent]
    return b
for n,h,t,par in B:bone(n,h,t,par)
for s,n,a in zip((-1,1),('L','R'),EA):
    bone('ear.0.'+n,a,ear_tip(a,s,ehr*.5),'head');bone('ear.1.'+n,ear_tip(a,s,ehr*.5),ear_tip(a,s,ehr*1.0),'ear.0.'+n)
prev=TAIL['parent']
for i in range(len(TP)-1):bone('tail.%d'%i,TP[i],TP[i+1],prev);prev='tail.%d'%i
for s,n,a in zip((-1,1),('L','R'),WA):
    base=Vector(a);bone('wing.0.'+n,tuple(base),tuple(base+Vector((s*ws*.5,.05,ws*.35))),WINGS['parent']);bone('wing.1.'+n,tuple(base+Vector((s*ws*.5,.05,ws*.35))),tuple(base+Vector((s*ws,.1,ws*.7))),'wing.0.'+n)
bpy.ops.object.mode_set(mode='OBJECT')
bones={b.name:(b.head_local.copy(),b.tail_local.copy()) for b in arm.bones}
def seg_d(p,a,b):
    ab=b-a;t=max(0,min(1,(p-a).dot(ab)/max(1e-9,ab.length_squared)));return (p-(a+ab*t)).length
def skin(o,cands_fn,smooth_it=8):
    me=o.data;V=me.vertices;W={}
    for v in V:
        cs=cands_fn(v.index,v.co);ws_=sorted(((1/((seg_d(v.co,*bones[b])+.015)**4),b) for b in cs),reverse=True)[:4];tot=sum(w for w,_ in ws_)
        W[v.index]={b:w/tot for w,b in ws_}
    adj=[[] for _ in V]
    for e in me.edges:x,y=e.vertices;adj[x].append(y);adj[y].append(x)
    for _ in range(smooth_it):
        new={}
        for i in range(len(V)):
            acc={}
            for j in adj[i]+[i,i]:
                for b,w in W[j].items():acc[b]=acc.get(b,0)+w
            t=sum(acc.values());new[i]={b:w/t for b,w in acc.items()}
        W=new
    G={}
    for i,d in W.items():
        top=sorted(d.items(),key=lambda x:-x[1])[:4];t=sum(w for _,w in top)
        for b,w in top:
            if w/t>.003:
                if b not in G:G[b]=o.vertex_groups.new(name=b)
                G[b].add([i],w/t,'REPLACE')
    o.parent=rig;m=o.modifiers.new('rig','ARMATURE');m.object=rig
legb=[b for b in bones if b.startswith('leg')]
def body_cands(i,co):
    lab=labels[i] or ''
    if lab.startswith('toe'):lab='paw'+lab[3:5]
    if lab.startswith('shin'):lab='leg'+lab[4:]
    if lab.startswith('leg') or lab.startswith('paw'):
        fb,n=lab[3],lab[4];return ['leg%s.0.%s'%(fb,n),'leg%s.1.%s'%(fb,n)]+(['spine'] if fb=='F' else ['hips'])
    if lab.startswith('spike'):return ['spine','hips','neck']
    if lab in('ruff','nape'):return ['neck','spine','head']
    if lab=='waist':return ['spine','hips']
    if lab in('head','muzzle','snout','jaw') or lab.startswith('cheek') or lab.startswith('brow'):return ['head']+(['neck'] if co.z<FACE['head_c'][2]-hr.z*.5 else [])
    if lab=='neck':return ['neck','head','spine']
    if lab=='rump':return ['hips','spine']
    return ['hips','spine','neck']
skin(body,body_cands)
skin(face,lambda i,co:['head'],0)
for nm,o in variants.items():
    if nm.startswith('ear'):skin(o,lambda i,co:['head']+(['ear.0.L','ear.1.L'] if co.x<0 else ['ear.0.R','ear.1.R']) if nm not in('ear_crown','ear_gills','ear_dhorn','ear_frill') else ['head'],4)
    elif nm.startswith('tail'):skin(o,lambda i,co:[TAIL['parent']]+['tail.%d'%k for k in range(len(TP)-1)],6)
    else:skin(o,lambda i,co:[WINGS['parent']]+(['wing.0.L','wing.1.L'] if co.x<0 else ['wing.0.R','wing.1.R']),4)
skin(detail,lambda i,co:(['tail.%d'%(len(TP)-2)] if dk in('comet','foxfire') else ['spine'] if dk=='ember_heart' else ['head']),0)
for o in [body,face,detail]+list(variants.values()):
    for p in o.data.polygons:p.use_smooth=True
tot=tris_of(body)+tris_of(face)+tris_of(detail)
print('TRIS body',tris_of(body),'face',tris_of(face),'detail',tris_of(detail),{k:tris_of(v) for k,v in variants.items()})
for o in C.scene.objects:o.select_set(False)
rig.select_set(True)
for o in [body,face,detail]+list(variants.values()):o.select_set(True)
active(rig)
for o in [body,face,detail]+list(variants.values()):o.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT,export_format='GLB',use_selection=True,export_skins=True,export_morph=True,export_morph_normal=False,export_animations=False,export_yup=True,export_vertex_color='ACTIVE')
bpy.ops.wm.save_as_mainfile(filepath=OUT.replace('.glb','.blend'))
print('EXPORTED',OUT,os.path.getsize(OUT))
