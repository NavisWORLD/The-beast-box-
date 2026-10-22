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
if sys.argv[-2:-1] and sys.argv[-2] in('res_frostmitt','res_nyxbean'):BODY_TRIS=int(os.environ.get('BODY_TRIS','7000'))
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
    wings=dict(at=[(s*bw*.6,by*p.get('wing_y',-.15),leg+bh*1.6) for s in (-1,1)],parent='spine',size=p.get('wing',.3))
    return P,B,face,ears,tail,wings
def upright(p):
    """Upright family: biped, bird, golem, sprout, moth. Arms reuse the front-leg chain (legF.*), legs the back chain (legB.*)."""
    bh=p['body_h'];bw=p['body_w'];bd=p.get('body_d',bw*.9);leg=p['leg'];hr=p['head_r'];arm=p.get('arm',.5);lt=p.get('leg_t',1.0)
    bz=leg+bh;hz=bz+bh*.85+hr*.75*p.get('neck',1.0);hy=-bd*.15
    P={'body':(ell,((0,0,bz),(bw,bd,bh))),'belly':(ell,((0,-bd*.25,bz-bh*.15),(bw*.85,bd*.8,bh*.8))),
       'neck':(ell,((0,hy*.6,bz+bh*.8),(bw*.55,bd*.55,bh*.35))),'head':(ell,((0,hy,hz),(hr*1.05,hr*.95,hr*.95)))}
    if p.get('muzzle',0)>0:P['muzzle']=(ell,((0,hy-hr*.8,hz-hr*.25),(hr*.32,hr*.25+p['muzzle'],hr*.22)))
    B=[('root',(0,0,0),(0,0,.1),None),('hips',(0,0,leg+bh*.3),(0,0,bz),'root'),('spine',(0,0,bz),(0,0,bz+bh*.75),'hips'),
       ('neck',(0,0,bz+bh*.75),(0,hy,hz-hr*.6),'spine'),('head',(0,hy,hz-hr*.6),(0,hy,hz+hr*.9),'neck')]
    for s_,n in ((-1,'L'),(1,'R')):
        x=s_*bw*.45;pr=(leg*.22+.035)*lt
        P['legB'+n]=(ell,((x,0,leg+bh*.15),(bw*.4*lt,bd*.45*lt,bh*.4)))
        P['shinB'+n]=(tube,([(x,0,leg+bh*.1),(x,-.01,leg*.5),(x,0,.06)],[(leg*.3+.035)*lt,(leg*.22+.025)*lt,(leg*.2+.02)*lt]))
        P['pawB'+n]=(ell,((x,-pr*.4,pr*.6),(pr*1.1,pr*1.45,pr*.62)))
        for k in (-1,0,1):P['toeB%s%d'%(n,k+1)]=(ell,((x+k*pr*.55,-pr*1.35,pr*.42),(pr*.36,pr*.4,pr*.38)))
        sx=s_*bw*.92;sz=bz+bh*.5;hx=s_*(bw*1.05);hzz=bz-bh*.35*arm*2
        if arm>0:
            P['legF'+n]=(tube,([(sx,0,sz),(s_*bw*1.08,-bd*.15,bz),(hx,-bd*.3,hzz)],[bw*.2*arm*1.6,bw*.16*arm*1.6,bw*.13*arm*1.6]))
            P['pawF'+n]=(ell,((hx,-bd*.32,hzz-.02),(bw*.17*arm*1.6,bw*.17*arm*1.6,bw*.19*arm*1.6)))
            B+=[('legF.0.'+n,(sx,0,sz),(s_*bw*1.08,-bd*.15,bz),'spine'),('legF.1.'+n,(s_*bw*1.08,-bd*.15,bz),(hx,-bd*.3,hzz-.03),'legF.0.'+n)]
        B+=[('legB.0.'+n,(x,0,leg+bh*.2),(x,-.01,leg*.5),'hips'),('legB.1.'+n,(x,-.01,leg*.5),(x,-.02,.03),'legB.0.'+n)]
        P['cheek'+n]=(ell,((s_*hr*.5,hy-hr*.55,hz-hr*.22),(hr*.32,hr*.26,hr*.28)))
    for k,v in p.get('extra',lambda **a:{})(bh=bh,bw=bw,bd=bd,bz=bz,hz=hz,hr=hr,leg=leg,hy=hy).items():P[k]=v
    face=dict(head_c=(0,hy,hz),head_r=(hr*1.05,hr*.95,hr*.95),eye_z=hz+hr*.08,eye_x=hr*.44,eye_r=hr*p.get('eye',.26),mouth_z=hz-hr*.42,nose=p.get('nose',True),heart=(0,-bd*.9,bz+bh*.2),mouth_w=p.get('mouth_w',.75))
    ears=dict(at=[(s_*hr*.55,hy+hr*.05,hz+hr*.72) for s_ in (-1,1)],head=(0,hy,hz),hr=hr)
    tail=dict(root=(0,bd*.8,leg+bh*.55),dir=p.get('tail_dir',(0,1,.5)),len=p.get('tail_len',.35),r=p.get('tail_r',.07),parent='hips')
    wings=dict(at=[(s_*bw*.5,bd*.55,bz+bh*.55) for s_ in (-1,1)],parent='spine',size=p.get('wing',.42))
    return P,B,face,ears,tail,wings
def long_(p):
    """Legless family: serpent (raised S-coil), fish (floating, finned). Tail chain continues the body."""
    L_=p['len'];r=p['r'];hr=p['head_r'];z0=p.get('float',0)
    if p.get('kind')=='serpent':
        pts=[(0,-L_*.05,hr*3.1+z0),(0,L_*.0,hr*1.8+z0),(r*.6,L_*.18,r*1.05+z0),(-r*1.4,L_*.36,r+z0),(r*1.2,L_*.55,r*.95+z0)]
        rad=[r*.8,r*.95,r,r*.95,r*.8]
    else:
        pts=[(0,-L_*.25,z0),(0,0,z0+.01),(0,L_*.25,z0)];rad=[r*.8,r,r*.75]
    hy=pts[0][1]-hr*.35;hz=pts[0][2]+hr*.35
    P={'body':(tube,(pts,rad)),'head':(ell,((0,hy,hz),(hr*1.08,hr*1.0,hr*.92))),'neck':(ell,((0,(pts[0][1]+pts[1][1])/2,(pts[0][2]+pts[1][2])/2+r*.1),(r*.9,r*.9,r*.9)))}
    if p.get('kind')=='fish':P['body']=(ell,((0,0,z0),(r*.9,L_*.42,r*1.15)))
    for s_,n in ((-1,'L'),(1,'R')):P['cheek'+n]=(ell,((s_*hr*.5,hy-hr*.55,hz-hr*.22),(hr*.32,hr*.26,hr*.28)))
    for k,v in p.get('extra',lambda **a:{})(pts=pts,r=r,hr=hr,hy=hy,hz=hz,z0=z0,L=L_).items():P[k]=v
    tip=pts[-1]
    B=[('root',(0,0,0),(0,0,.1),None),('hips',tip,(0,(pts[-2][1]+tip[1])/2,pts[-2][2]),'root'),('spine',(0,(pts[-2][1]+tip[1])/2,pts[-2][2]),pts[1],'hips'),
       ('neck',pts[1],pts[0],'spine'),('head',pts[0],(0,hy,hz+hr*.9),'neck')]
    face=dict(head_c=(0,hy,hz),head_r=(hr*1.08,hr*1.0,hr*.92),eye_z=hz+hr*.1,eye_x=hr*.46,eye_r=hr*p.get('eye',.26),mouth_z=hz-hr*.4,nose=False,heart=(0,pts[1][1]-r*.9,pts[1][2]),mouth_w=.8)
    ears=dict(at=[(s_*hr*.55,hy+hr*.05,hz+hr*.72) for s_ in (-1,1)],head=(0,hy,hz),hr=hr)
    tail=dict(root=tip,dir=p.get('tail_dir',(0,1,.15)),len=p.get('tail_len',.4),r=r*.7,parent='hips')
    wings=dict(at=[(s_*r*.9,0,z0+r*.6) for s_ in (-1,1)],parent='spine',size=p.get('wing',.3))
    return P,B,face,ears,tail,wings
def beak_x(bh,bw,bd,bz,hz,hr,leg,hy):
    return {'beak':(cone,((0,hy-hr*.7,hz-hr*.15),(0,hy-hr*1.55,hz-hr*.32),hr*.38,.7,24,.025)),'chest':(ell,((0,-bd*.55,bz+bh*.15),(bw*.8,bd*.6,bh*.75)))}
def golem_x(bh,bw,bd,bz,hz,hr,leg,hy):
    d={}
    for i,(x,z,sc) in enumerate(((-.6,.65,.32),(.65,.55,.28),(-.2,-.4,.26),(.4,-.2,.24),(0,.9,.3))):
        d['rock%d'%i]=(ell,((x*bw,bd*.35,bz+z*bh),(bw*sc,bd*sc*.9,bh*sc*.8),(.4*i,.3*i,.2*i),10,6))
    d['shoulderL']=(ell,((-bw*.95,0,bz+bh*.55),(bw*.42,bd*.5,bh*.35)));d['shoulderR']=(ell,((bw*.95,0,bz+bh*.55),(bw*.42,bd*.5,bh*.35)))
    return d
def sprout_x(bh,bw,bd,bz,hz,hr,leg,hy):
    return {'bulb':(ell,((0,0,bz-bh*.2),(bw*1.15,bd*1.1,bh*.9))),'stem':(tube,([(0,0,hz+hr*.8),(.03,.02,hz+hr*1.15),(.07,.04,hz+hr*1.35)],[.03,.022,.014]))}
def moth_x(bh,bw,bd,bz,hz,hr,leg,hy):
    return {'ruff':(ell,((0,0,bz+bh*.75),(bw*1.25,bd*1.15,bh*.5)))}
def fish_x(pts,r,hr,hy,hz,z0,L):
    return {'dorsal':(ell,((0,.02,z0+r*1.1),(r*.12,L*.2,r*.55))),'finL':(ell,((-r*1.05,-L*.02,z0-r*.35),(r*.7,r*.42,r*.09),(0,.6,0))),'finR':(ell,((r*1.05,-L*.02,z0-r*.35),(r*.7,r*.42,r*.09),(0,-.6,0))),'belfin':(ell,((0,L*.12,z0-r*1.05),(r*.08,L*.12,r*.35)))}
def serp_x(pts,r,hr,hy,hz,z0,L):
    return {'hood':(ell,((0,hy+hr*.35,hz-hr*.35),(hr*1.25,hr*.5,hr*.9)))}
def fox_x(by,bh,bw,hz,hr,leg,hy):
    # long tapering snout + chest ruff
    return {'snout':(tube,([(0,hy-hr*.45,hz-hr*.16),(0,hy-hr*1.0,hz-hr*.26),(0,hy-hr*1.45,hz-hr*.34),(0,hy-hr*1.62,hz-hr*.36)],[hr*.4,hr*.3,hr*.2,hr*.12])),
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
 'dragonling':lambda:quad(dict(body=(.40,.2,.21),head_z=.84,head_r=.27,leg=.2,leg_t=1.15,muzzle=.14,muz_w=1.05,cheek=.6,tail_len=.7,tail_r=.09,eye=.24,tail_dir=(0,1,.18),wing=.5,wing_y=.2,extra=dragon_x)),
 'biped':lambda:upright(dict(body_h=.2,body_w=.19,leg=.2,head_r=.3,arm=.5,eye=.28,tail_len=.3)),
 'bird':lambda:upright(dict(body_h=.22,body_w=.21,body_d=.24,leg=.17,leg_t=.6,head_r=.26,arm=0,eye=.27,nose=False,neck=.6,tail_len=.3,tail_dir=(0,1,.2),wing=.5,extra=beak_x)),
 'golem':lambda:upright(dict(body_h=.27,body_w=.28,body_d=.24,leg=.18,leg_t=1.5,head_r=.22,arm=.85,eye=.24,neck=.4,tail_len=.2,extra=golem_x)),
 'sprout':lambda:upright(dict(body_h=.2,body_w=.22,leg=.12,leg_t=.9,head_r=.28,arm=.35,eye=.28,neck=.6,tail_len=.2,extra=sprout_x)),
 'moth':lambda:upright(dict(body_h=.21,body_w=.19,leg=.16,leg_t=.7,head_r=.27,arm=.35,eye=.3,neck=.5,tail_len=.25,wing=.6,extra=moth_x)),
 'serpent':lambda:long_(dict(kind='serpent',len=1.1,r=.11,head_r=.24,eye=.26,tail_len=.45,tail_dir=(-.4,1,.0),extra=serp_x)),
 'fish':lambda:long_(dict(kind='fish',len=.75,r=.2,head_r=.25,float=.45,eye=.26,tail_len=.22,tail_dir=(0,1,0),extra=fish_x)),
 'res_frostmitt':lambda:quad(dict(body=(.34,.2,.21),head_z=.86,head_r=.31,leg=.18,muzzle=.03,cheek=.9,tail_len=.4,tail_r=.08,eye=.33)),
 'res_nyxbean':lambda:quad(dict(body=(.24,.11,.1),head_z=.86,head_r=.36,leg=.33,leg_t=.75,tail_dir=(0,1,1.7),muzzle=.05,muz_w=.8,muz_h=.7,cheek=.9,tail_len=.4,tail_r=.055,eye=.42,extra=lambda by,bh,bw,hz,hr,leg,hy:{'ruff':(ell,((0,-by*.85,leg+bh*1.35),(bw*.95,bw*.75,bh*.95))),'tuft':(cone,((0,-by*.95,leg+bh*1.5),(0,-by*1.25,leg+bh*.55),bw*.5,.6,16)),'bellyb':(ell,((0,-by*.1,leg+bh*.55),(bw*.9,by*.75,bh*.7)))})),
 'res_shardhowl':lambda:quad(dict(body=(.46,.17,.16),head_z=.95,head_r=.24,leg=.32,leg_t=.85,muzzle=.04,muz_w=.75,muz_h=.8,cheek=.6,tail_len=.6,tail_r=.09,eye=.22,tail_dir=(0,1,.3),tail_in=.15,extra=fox_x)),
 'res_velvetcoil':lambda:long_(dict(kind='serpent',len=1.25,r=.1,head_r=.22,eye=.27,tail_len=.55,tail_dir=(-.4,1,.0),extra=serp_x)),
 'res_kairo':lambda:upright(dict(body_h=.24,body_w=.15,body_d=.11,leg=.42,leg_t=.5,head_r=.23,arm=.5,eye=.19,neck=.55,nose=False,mouth_w=.5,tail_len=.04,tail_r=.015)),
 'axolotl':lambda:quad(dict(body=(.5,.13,.19),head_z=.36,head_r=.27,leg=.1,leg_t=.8,muzzle=.0,muz_w=1.6,muz_h=.7,cheek=.4,tail_len=.6,tail_r=.09,eye=.17,tail_dir=(0,1,.05),extra=axo_x)),
}
if PLAN not in SPECS:raise SystemExit('plan not built yet: '+PLAN)
P,B,FACE,EARS,TAIL,WINGS=SPECS[PLAN]()
if PLAN=='res_shardhowl':BODY_TRIS=2400
if PLAN=='res_kairo':BODY_TRIS=6000   # mostly under clothes/hair   # big crystal facets (flat-shaded at runtime)
parts={k:fn(k,*a) for k,(fn,a) in P.items()}
body,labels=fuse(parts,'body',tris=BODY_TRIS)
print('body tris',tris_of(body))
if PLAN=='res_kairo':
    # sculpted chibi human face on the fused head: cheeks, brow ridge, nose bridge, narrowed chin (gaussian brushes along normals)
    _hc=Vector(FACE['head_c']);_hr=Vector(FACE['head_r']);_ez=FACE['eye_z'];_ex=FACE['eye_x'];_er=FACE['eye_r']
    def _g(p,c,r):return math.exp(-((p-c).length/r)**2)
    for i,v in enumerate(body.data.vertices):
        if (labels[i] or '')!='head':continue
        p=v.co;n=v.normal;fr=max(0,-n.y)  # front-facing weight
        d=0
        for sx in (-1,1):d+=.010*_g(p,Vector((sx*_ex*1.15,p.y,_ez-_er*1.5)),_hr.x*.32)*fr        # cheeks
        d+=.006*math.exp(-((p.z-(_ez+_er*1.3))/(_er*.35))**2)*max(0,1-abs(p.x)/(_hr.x*.75))*fr**2  # brow ridge
        d+=.005*math.exp(-(p.x/(_er*.28))**2)*(1 if _ez-_er*1.2<p.z<_ez+_er*.2 else 0)*fr**3     # nose bridge
        if p.z<_ez-_er*1.6:v.co.x*=1-.12*min(1,(_ez-_er*1.6-p.z)/(_hr.z*.5))                  # chibi chin taper
        v.co+=n*d
body_bvh=bvh(body)

# ============================================================ face (eyes, catchlights, nose, mouth) with shape keys
hc=Vector(FACE['head_c']);hr=Vector(FACE['head_r'])
def surf(x,z,y0=-3):
    h=body_bvh.ray_cast(Vector((x,y0,z)),Vector((0,1,0)));return h[0] if h[0] else Vector((x,hc.y-hr.y,z))
face_objs=[];groups={}
GNAMES=['eyeL','eyeR','irisL','irisR','shineL','shineR','mouth','mouthin','nose','tongue']
def add_face(o,group):
    if PLAN in('res_frostmitt','res_nyxbean','res_kairo') and group[:3] in('eye','iri','shi') or PLAN=='res_nyxbean' and group in('mouthin','tongue'):
        D.objects.remove(o,do_unlink=True);return
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
    mpts.append(tuple(surf(x,z)+Vector((0,-.016,0))))
mo=tube('mouth',mpts,[ER*.13]*9,res=6,bev=8);add_face(mo,'mouth')
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
LEAF_ARGS=[(a,s) for a,s in zip(EA,(-1,1))]
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
            tip=elbow+Vector((s_*math.cos(ang)*ws*L_,.3*ws+k*.12*ws,math.sin(ang)*ws*L_*.8));tips.append(tip)
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
def leaf_mesh(a,s,L_,W_):
    me=D.meshes.new('leaf');bm=bmesh.new();n=10;vs=[];base=Vector(a);d=Vector((s*.55,.05,1)).normalized();side=Vector((s,0,-s*.55)).normalized()*0+Vector((1,0,0))
    rows=[]
    for i in range(n+1):
        u=i/n;w=W_*math.sin(math.pi*min(1,u*1.05))**.8;c=base+d*L_*u+Vector((0,-.04*math.sin(u*math.pi)*L_,0))
        rows.append([bm.verts.new(tuple(c+Vector((k*w*.5,0,0))+Vector((0,abs(k)*w*.12,0)))) for k in (-1,-.5,0,.5,1)])
    for i in range(n):
        for j in range(4):bm.faces.new((rows[i][j],rows[i][j+1],rows[i+1][j+1],rows[i+1][j]))
    bm.to_mesh(me);bm.free();o=D.objects.new('leaf',me);C.collection.objects.link(o)
    m=o.modifiers.new('s','SOLIDIFY');m.thickness=.008;active(o);bpy.ops.object.modifier_apply(modifier='s');return o
raw_variant('ear_leaf',[leaf_mesh(a,s,ehr*1.05,ehr*.5) for a,s in LEAF_ARGS]+[tube('rib',[a,tuple(Vector(a)+Vector((s*.55,.05,1)).normalized()*ehr*.9)],[.006,.003],res=4) for a,s in LEAF_ARGS],tris=1600)
# moth wings: real fore+hind wing membranes with scalloped edges and veins
def moth_wing(a,s,fore=True):
    me=D.meshes.new('mw');bm=bmesh.new();base=Vector(a);c0=bm.verts.new(tuple(base));ring=[]
    for k in range(25):
        t=k/24;ang=(.15+t*1.35) if fore else (-.95+t*1.0);r_=ws*(1.05 if fore else .7)*(.55+.45*math.sin(t*math.pi))*(1+.06*math.sin(t*math.pi*7))
        ring.append(bm.verts.new(tuple(base+Vector((s*math.cos(ang)*r_,.04+.12*t*ws,math.sin(ang)*r_*.9)))))
    for k in range(24):bm.faces.new((c0,ring[k],ring[k+1]))
    bmesh.ops.subdivide_edges(bm,edges=bm.edges[:],cuts=2,use_grid_fill=True);bmesh.ops.triangulate(bm,faces=bm.faces[:])
    bm.to_mesh(me);bm.free();o=D.objects.new('mw',me);C.collection.objects.link(o);m=o.modifiers.new('s','SOLIDIFY');m.thickness=.006;active(o);bpy.ops.object.modifier_apply(modifier='s');return o
if PLAN=='moth':
    D.objects.remove(variants.pop('wing_moth'),do_unlink=True)
    mo_=[moth_wing(a,s,f) for a,s in zip(WA,(-1,1)) for f in (True,False)]
    for a,s in zip(WA,(-1,1)):
        for k in range(4):
            ang=.3+k*.35;tip=Vector(a)+Vector((s*math.cos(ang)*ws*.9,.08*ws,math.sin(ang)*ws*.8));mo_.append(tube('v',[a,tuple((Vector(a)+tip)/2),tuple(tip)],[.007,.005,.002],res=4))
    raw_variant('wing_moth',mo_,tris=3000)
# IMPOSSIBLE DETAIL (per species): a tiny comet for the pup's tail tip, ember-heart for dragonling, etc.
DETAIL={'res_frostmitt':'tide_halo','res_nyxbean':'none','res_shardhowl':'ember_heart','res_velvetcoil':'comet','res_kairo':'ember_heart','pup':'comet','fox':'foxfire','dragonling':'ember_heart','axolotl':'tide_halo','biped':'tide_halo','bird':'comet','golem':'ember_heart','sprout':'foxfire','moth':'tide_halo','serpent':'comet','fish':'foxfire'}
dk=DETAIL.get(PLAN,'comet')
if dk=='comet':dt=[ell('d',tuple(Vector(TP[-1])+td*trad*1.4),(trad*.55,trad*.55,trad*.55),seg=20,ring=10)]+[ell('d',tuple(Vector(TP[-1])+td*trad*(2.2+k*.9)-Vector((0,0,k*.02))),(trad*.3*(1-k*.25),)*3,seg=10,ring=6) for k in range(3)]
elif dk=='foxfire':dt=[ell('d',tuple(Vector(TP[-1])+Vector((s*.12,0,.15))),(.04,.04,.07),seg=14,ring=8) for s in (-1,0,1)]
elif dk=='ember_heart':dt=[ell('d',FACE.get('heart',(0,-.1,.62)),(.06,.03,.06),seg=16,ring=8)]
elif dk=='none':dt=[ell('d',(0,0,.3),(.001,.001,.001),seg=4,ring=3)]
else:dt=[tube('d',[(math.cos(a)*.22,EARS['head'][1]+math.sin(a)*.22,EARS['head'][2]+.36) for a in [k/16*2*math.pi for k in range(17)]],[.012]*17)]
detail=join(dt,'detail');setmat(detail,M['glow'])
# ---- resident props (beanie, crystal shards, hoodie+horns, coil spikes): own materials, rigged to head/spine
props=[];M['prop']=mat('prop',(1,1,1,1),.9,sheen=.5)
hcv=Vector(FACE['head_c']);hrz=hr.z;hrx=hr.x
def prop(name,objs,bone_,tris=2400):
    o=join(objs,name);active(o);m=o.modifiers.new('t','TRIANGULATE');bpy.ops.object.modifier_apply(modifier='t')
    if len(o.data.polygons)>tris:m=o.modifiers.new('d','DECIMATE');m.ratio=tris/len(o.data.polygons);bpy.ops.object.modifier_apply(modifier='d')
    setmat(o,M['prop']);o['bone']=bone_;props.append(o);return o
if PLAN in('res_frostmitt','res_nyxbean','res_kairo') and os.environ.get('LEGACY_PROPS'):
    bz=hcv.z+hrz*.58
    hat=[ell('h',(0,hcv.y+hrx*.12,bz),(hrx*.98,hrx*.95,hrz*.62),seg=40,ring=20),
         tube('b',[(math.cos(a)*hrx*.99,hcv.y+hrx*.12+math.sin(a)*hrx*.96,bz-hrz*.2) for a in [k/24*2*math.pi for k in range(25)]],[hrz*.13]*25,res=4)]
    for k in range(10):  # knit ribs
        a=k/10*2*math.pi;hat.append(ell('r',(math.cos(a)*hrx*.72,hcv.y+hrx*.12+math.sin(a)*hrx*.7,bz+hrz*.15),(hrx*.08,hrx*.08,hrz*.4),seg=10,ring=8))
    if PLAN=='res_kairo':
        hat=[ell('hood',(0,hcv.y+hrx*.45,hcv.z+hrz*.1),(hrx*1.2,hrx*1.0,hrz*1.18),seg=40,ring=20)]
        for k in range(7):  # spiky fringe of black hair peeking out of the hood
            x=(k-3)*hrx*.22;hat.append(cone('hair',(x,hcv.y-hrx*.55,hcv.z+hrz*.62),(x*1.15+.01*(k%2),hcv.y-hrx*.95,hcv.z+hrz*(.25+.08*(k%2))),hrx*.16,.6,8))
        for s_ in (-1,1):hat.append(ell('shoe',(s_*.15*.45,-.04,.035),(.055,.1,.045)));hat.append(ell('sole',(s_*.15*.45,-.04,.012),(.06,.105,.016)))
    if PLAN=='res_kairo':
        # hoodie details from his art: hood rim, drawstrings, kangaroo pocket, zipper, sleeve cuffs, trouser cuffs
        bz_=.42+.24
        for s_ in (-1,1):hat.append(tube('str',[(s_*.04,-.12,bz_+.2),(s_*.045,-.125,bz_+.08),(s_*.05,-.12,bz_+.0)],[.006,.006,.008],res=4))
        hat.append(ell('pocket',(0,-.105,bz_-.12),(.1,.025,.055)))
        hat.append(tube('zip',[(0,-.118,bz_+.2),(0,-.122,bz_),(0,-.11,bz_-.2)],[.005]*3,res=4))
        for s_ in (-1,1):
            hat.append(tube('pcuff',[(s_*.0675+math.cos(a)*.04,math.sin(a)*.04,.1) for a in [k/12*2*math.pi for k in range(13)]],[.012]*13,res=4))
    for s_ in (-1,1):hat.append(cone('horn',(s_*hrx*.55,hcv.y,bz+hrz*.35),(s_*hrx*.75,hcv.y+hrx*.1,bz+hrz*.95),hrz*.14,1))
    prop('prop_hat',hat,'head')
# ---- turnaround-faithful outfits (Cory's sheets): authored PBR 'pm_*' materials the runtime keeps as-is
PM={}
def pmat(n,base,rough=.6,emit=None,es=0,coat=0,sheen=0,metal=0):
    if n not in PM:PM[n]=mat('pm_'+n,base,rough,metal,emit,es,coat=coat,sheen=sheen)
    return PM[n]
CL={}
def cap(o,n):
    active(o);m=o.modifiers.new('t','TRIANGULATE');bpy.ops.object.modifier_apply(modifier='t')
    if len(o.data.polygons)>n:m=o.modifiers.new('d','DECIMATE');m.ratio=n/len(o.data.polygons);bpy.ops.object.modifier_apply(modifier='d')
def addp(o,m,bone_='head',n=None):
    cap(o,n or int(os.environ.get('PROP_TRIS','450')))
    setmat(o,PM[m]) if isinstance(m,str) else setmat(o,m);o['bone']=bone_;props.append(o);return o
def joinm(objs,name):return join(objs,name) if len(objs)>1 else objs[0]
def clothes(name,labs,off,m,zmin=-9,zmax=9,ymax=9,xmin=0):
    """fitted garment: copy of the fused body limited to labels, pushed out along normals; skinned like the body."""
    me=body.data.copy();o=D.objects.new(name,me);C.collection.objects.link(o)
    bm=bmesh.new();bm.from_mesh(me);bm.verts.ensure_lookup_table()
    keep=[v for v in bm.verts if (labels[v.index] or '') .rstrip('LR0123') in labs and zmin<v.co.z<zmax and v.co.y<ymax and abs(v.co.x)>=xmin]
    ks=set(v.index for v in keep);lab=[labels[v.index] for v in bm.verts if v.index in ks]
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index not in ks],context='VERTS')
    for v in bm.verts:v.co+=v.normal*off
    bm.to_mesh(me);bm.free();m_=o.modifiers.new('s','SOLIDIFY');m_.thickness=off*.6;m_.offset=-1;active(o);bpy.ops.object.modifier_apply(modifier='s')
    # solidify duplicates verts in order: originals then copies
    n=len(lab);lab=lab+lab[:max(0,len(o.data.vertices)-n)]
    for p in o.data.polygons:p.use_smooth=True
    o.vertex_groups.clear();CL[name]=lab
    cap(o,1400 if PLAN!='res_kairo' else 1050)
    from mathutils.kdtree import KDTree
    kd=KDTree(len(body.data.vertices))
    for v in body.data.vertices:kd.insert(v.co,v.index)
    kd.balance();CL[name]=[labels[kd.find(v.co)[1]] for v in o.data.vertices];setmat(o,PM[m]);o['bone']='*';props.append(o);return o
def ring(name,c,rx,ry,r,n=24,dz=0):return tube(name,[(c[0]+math.cos(a)*rx,c[1]+math.sin(a)*ry,c[2]+dz*math.sin(a*2)) for a in [k/n*2*math.pi for k in range(n+1)]],[r]*(n+1),res=3)
def beanie(c,rx,ry,rz,crown,slouch,bands,band_m,body_m,knit=14):
    """knit/puffy beanie: cuff ring stack + slouched crown + rib cords; bands = list of (z frac, material)"""
    hat=[];cuff=[]
    puffy_=knit<10
    for k in range(5 if knit<10 else 4):cuff.append(ring('cuff',(c[0],c[1],c[2]+k*rz*(.085 if puffy_ else .09)),rx*(1.06+.012*math.sin(k/5*math.pi)),ry*(1.06+.012*math.sin(k/5*math.pi)),rz*(.15 if puffy_ else .07),32))
    addp(joinm(cuff,'prop_cuff'),band_m if puffy_ else body_m,n=900 if puffy_ else None)
    if puffy_:bands=[]
    for z,bm_ in bands:addp(ring('prop_band',(c[0],c[1],c[2]+z*rz),rx*1.06,ry*1.06,rz*.045,40),bm_)
    cr=[ell('crown',(c[0],c[1]+slouch*.35,c[2]+rz*.55),(rx*(1.0 if knit<10 else .98),ry*(1.0 if knit<10 else .98),rz*crown),seg=48,ring=24),
        ell('slouch',(c[0],c[1]+slouch,c[2]+rz*(crown*.9)),(rx*.75,ry*.8,rz*crown*.55),seg=40,ring=20)]
    if knit>=10:
        for k in range(knit):  # knit rows hugging the crown ellipsoid
            t=(k+.5)/knit;zz=c[2]+rz*.55+rz*crown*t*.92;f=math.sqrt(max(.02,1-t*t))
            cr.append(ring('row',(c[0],c[1]+slouch*.35*t,zz),rx*.99*f,ry*.99*f,rz*.035,40))
        o=joinm(cr,'prop_crown');addp(o,body_m,n=2600 if PLAN!='res_kairo' else 1700);return o
    def droop(v):
        t=max(0,(v.z-c[2])/(rz*(crown+.6)))
        if knit<10 and t>0:  # deep puffy channels: pinch inward along 8 sewn meridians before the cloth settle
            a=math.atan2(v.y-c[1],v.x-c[0]);d=min(abs(((a-k*math.pi/4)+math.pi)%(2*math.pi)-math.pi) for k in range(8))
            pin_=(.22*rx*math.exp(-(d/.12)**2)-.05*rx*(1-math.exp(-(d/.3)**2)))*min(1,t*3)*(1-t*.6);r_=Vector((v.x-c[0],v.y-c[1],0))
            if r_.length>1e-6:v.x-=r_.x/r_.length*pin_;v.y-=r_.y/r_.length*pin_
        v.y+=t*t*rx*(.35 if knit<10 else .6);v.z-=t*t*t*rz*.12;v.x*=1+.06*t
        if knit<10 and v.y<c[1]:v.y-=(c[1]-v.y)*.18*min(1,t*2.5);v.z-=(c[1]-v.y)*.12*min(1,t*2.5) if knit<10 and v.y<c[1] else 0
    for o_ in cr:
        for v in o_.data.vertices:droop(v.co)
    if PLAN=='res_nyxbean' and os.environ.get('CST_SOFT','1')=='1':
        # CST soft-body: the sack settles over the head under gravity + Lorenz wind (scripts/creatures3d/cst_softbody.mjs)
        import json,subprocess
        o_=cr[0];me_=o_.data;zb=c[2]+rz*.25
        pin=[v.index for v in me_.vertices if v.co.z<zb]
        J={'v':[list(v.co) for v in me_.vertices],'e':[list(e.vertices) for e in me_.edges],'pin':pin,'seed':PLAN,
           'head':{'x':hcv.x,'y':hcv.y,'z':hcv.z,'r':hrx*1.02},'steps':int(os.environ.get('CST_STEPS','140'))}
        js=os.path.join(os.path.dirname(os.path.abspath(__file__)),'cst_softbody.mjs')
        r_=subprocess.run(['node',js],input=json.dumps(J).encode(),capture_output=True)
        if r_.returncode==0:
            for v,q in zip(me_.vertices,json.loads(r_.stdout)):v.co=q
            print('CST soft-body settled',len(pin),'pinned');globals()['CROWN_BVH']=bvh(o_)
        else:print('CST soft-body failed',r_.stderr[:300])
    o=joinm(cr,'prop_crown');addp(o,body_m,n=2400)
    seams=[]  # puffer quilting: dark seam meridians pressed into the dome
    for k in range(8):
        a=k/8*2*math.pi;pts=[]
        for t in [i/10 for i in range(11)]:
            el=t*math.pi/2;pts.append((c[0]+math.cos(a)*rx*.985*math.cos(el),c[1]+slouch*.35+math.sin(a)*ry*.985*math.cos(el),c[2]+rz*.55+rz*crown*.985*math.sin(el)))
        pv=[Vector(q) for q in pts]
        for q in pv:droop(q)
        if 'CROWN_BVH' in globals():
            for q in pv:
                h_=CROWN_BVH.find_nearest(q)
                if h_[0] is not None:q[:]=h_[0]+h_[1]*.002
        seams.append(tube('seam',[tuple(q) for q in pv],[rz*.022]*11,res=3))
    pmat('seam',(.02,.008,.04,1),.7);addp(joinm(seams,'prop_seams'),'seam',n=500)
    st=[]  # glowing ribbed band: vertical stripe ribs
    for k in range(28):
        a=k/28*2*math.pi;st.append(ell('rib',(c[0]+math.cos(a)*rx*1.14,c[1]+math.sin(a)*ry*1.14,c[2]+rz*.13),(rx*.06,rx*.06,rz*.3),seg=8,ring=6))
    addp(joinm(st,'prop_bandribs'),'trim',n=900);return o
NEW_OUTFIT=PLAN in('res_frostmitt','res_nyxbean','res_kairo')
if NEW_OUTFIT:
    pmat('trim',(.55,.15,1,1),.3,emit=(.62,.2,1,1),es=6)
    pmat('horn_purple',(.16,.02,.62,1),.1,emit=(.22,.02,.85,1),es=.45,coat=1)
    pmat('horn_grey',(.62,.6,.66,1),.35,coat=.8)
    hb=Vector((0,hcv.y+hrx*.05,hcv.z+hrz*.18))
    if PLAN=='res_nyxbean':
        hb=hb+Vector((0,hrx*.14,hrz*.7));del PM['trim'];pmat('trim',(.25,.045,1,1),.5,emit=(.25,.045,1,1),es=.9)
        pmat('puffy',(.03,.011,.065,1),.7,sheen=.3)
        pmat('bandbase',(.07,.012,.25,1),.6,emit=(.2,.03,.7,1),es=.25);beanie(hb,hrx*1.2,hrx*1.14,hrz*1.2,1.45,hrx*.9,[],'bandbase','puffy',knit=0)
        for s_ in (-1,1):addp(tube('prop_horn',[(s_*hrx*.26,hcv.y-hrx*.82,hcv.z+hrz*.46),(s_*hrx*.36,hcv.y-hrx*1.0,hcv.z+hrz*.66),(s_*hrx*.3,hcv.y-hrx*1.08,hcv.z+hrz*.88)],[hrz*.19,hrz*.12,hrz*.018],res=8),'horn_purple',n=500)
    if PLAN=='res_kairo':del PM['trim'];pmat('trim',(.45,.12,.9,1),.4,emit=(.5,.15,1,1),es=1.4)
    if PLAN=='res_frostmitt':
        hb=hb+Vector((0,hrx*.1,hrz*.5))
        pmat('knit',(.07,.03,.2,1),.92,sheen=.22)
        pmat('magenta',(.8,.15,.9,1),.5,emit=(.85,.2,1,1),es=2.5)
        pmat('ice',(.72,.88,1,1),.05,emit=(.35,.6,1,1),es=.35,coat=1)
        beanie(hb,hrx*1.15,hrx*1.1,hrz*1.3,1.05,hrx*.75,[(.08,'magenta'),(.28,'magenta')],'magenta','knit',knit=16)
        for s_ in (-1,1):
            addp(cone('prop_horn',(s_*hrx*.45,hcv.y-hrx*.75,hcv.z+hrz*.3),(s_*hrx*.6,hcv.y-hrx*1.05,hcv.z+hrz*.72),hrz*.12,1,16),'horn_grey')
            addp(cone('prop_horn',(s_*hrx*1.05,hcv.y,hcv.z+hrz*.9),(s_*hrx*1.35,hcv.y-.02,hcv.z+hrz*1.3),hrz*.09,1,12),'horn_grey')
        import random;R=random.Random(11);ic=[]
        bvb=body_bvh
        for k in range(26):  # icicles hanging from chest/legs/cheeks
            a=R.uniform(0,2*math.pi);z=R.uniform(.12,hcv.z-hrz*.2);o_=Vector((math.cos(a)*.5,math.sin(a)*.5-.1,z))
            h=bvb.find_nearest(o_)
            if h[0] is None or h[1].z>-.1 and z>.35 and R.random()<.5:continue
            p=h[0];L=R.uniform(.03,.07);ic.append(cone('ice',tuple(p+h[1]*.004),tuple(p+Vector((h[1].x*.01,h[1].y*.01,-L))),R.uniform(.008,.014),1,6))
        addp(joinm(ic,'prop_icicles'),'ice','spine')
        cubes=[]
        for k in range(14):  # floating pixel cubes (frost data)
            a=R.uniform(0,2*math.pi);r=R.uniform(.28,.45);bpy.ops.mesh.primitive_cube_add(size=R.uniform(.014,.026),location=(math.cos(a)*r,math.sin(a)*r,R.uniform(.15,.9)),rotation=(R.random(),R.random(),R.random()))
            cubes.append(C.active_object);apply_all(cubes[-1])
        addp(joinm(cubes,'prop_pixels'),'ice','root')
    if PLAN=='res_kairo':
        pmat('cloth',(.01,.009,.013,1),.7,sheen=.2)
        pmat('tee',(.04,.035,.045,1),.85,sheen=.4)
        pmat('hair',(.006,.005,.008,1),.82);PM['hair'].node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value=.15
        pmat('ear_in',(.55,.2,.9,1),.5,emit=(.4,.1,.8,1),es=.4)
        pmat('sole',(.6,.25,1,1),.4,emit=(.55,.2,1,1),es=1.5)
        pmat('zip',(.8,.8,.85,1),.25,metal=1)
        pmat('tattoo',(.45,.15,.75,1),.5,emit=(.5,.2,.9,1),es=.8)
        # garments fitted to the sculpted body
        clothes('prop_hoodie',('body','belly','neck','legF'),.014,'cloth',zmin=.36)
        clothes('prop_joggers',('legB','shinB'),.012,'cloth',zmin=.07)
        clothes('prop_shoes',('pawB','toeB'),.012,'cloth')
        bz_=FACE['head_c'][2]
        trl=[]
        sp_=[b for b in B if b[0]=='spine'][0];zt=sp_[2][2];zb=sp_[1][2]
        h=body_bvh
        def onb(x,z,front=True,off=.018):
            r=h.ray_cast(Vector((x,-2 if front else 2,z)),Vector((0,1 if front else -1,0)));return (r[0]+r[1]*off) if r[0] else Vector((x,0,z))
        # zipper, neon trim lines, hem/cuff ribbing, back swirl emblem, chest glyph patch
        addp(tube('prop_zip',[tuple(onb(0,z,off=.02)) for z in (zt-.02,zb+(zt-zb)*.4,zb-.1)],[.004]*3,res=4),'zip','spine')
        for s_ in (-1,1):
            trl.append(tube('t',[tuple(onb(s_*.05,zt,off=.022)),tuple(onb(s_*.11,zt-.06,off=.022)),tuple(onb(s_*.12,zb-.05,off=.022))],[.0035]*3,res=4))
            trl.append(tube('t',[tuple(onb(s_*.06,zb,off=.022)),tuple(onb(s_*.1,zb-.03,off=.022))],[.004]*2,res=4))
            trl.append(tube('t',[tuple(onb(s_*.04,zb+.05,False,.022)),tuple(onb(s_*.12,zt-.04,False,.022))],[.0035]*2,res=4))
            for z in (.11,.25,.38):trl.append(tube('t',[(s_*.068,-.03,z),(s_*.07,-.035,z-.05)],[.003]*2,res=3))  # jogger piping
        sw=[]
        for k in range(30):
            t=k/29;a=t*math.pi*3;r=.055*(1-t*.8);sw.append(tuple(onb(math.cos(a)*r,(zb+zt)/2+math.sin(a)*r,False,.022)))
        trl.append(tube('t',sw,[.0045]*30,res=3))
        addp(joinm(trl,'prop_trim'),'trim','spine')
        # folded hood behind the neck (sheet: hood rests on the shoulders) + purple edge trim
        hp=[(-.1,-.0,.83),(-.085,.06,.87),(0,.1,.9),(.085,.06,.87),(.1,-.0,.83)]
        addp(tube('prop_hood',hp,[.022,.034,.04,.034,.022],res=10),'cloth','spine')
        addp(tube('prop_hoodtrim',[(x*1.04,y+.012*(1 if y>0 else 0),z+.03) for x,y,z in hp],[.0035]*5,res=4),'trim','spine')
        # ribbed elbow cuffs on the short sleeves (3 ribs each) + pixel glyph patch on the left shoulder
        for side,bx in (('L',-.16),('R',.16)):
            cf=[ring('cuff',(bx,-.012,.665+k*.011),.036,.034,.0045,18) for k in range(3)]
            addp(joinm(cf,'prop_slcuff'+side),'trim','legF.0.'+side)
        R6=__import__('random').Random(4);px=[]
        for i in range(5):
            for j in range(4):
                if R6.random()<.45:continue
                z=.80-j*.016;y=-.03+i*.014;hh=h.ray_cast(Vector((-.6,y,z)),Vector((1,0,0)))
                if not hh[0]:continue
                bpy.ops.mesh.primitive_cube_add(size=.012,location=tuple(hh[0]+Vector((-.003,0,0))));px.append(C.active_object)
        if px:addp(joinm(px,'prop_patch'),'trim','legF.0.L',n=300)
        rib=[ring('rib',(0,0,zb-.06+k*.012),.16,.12,.006,28) for k in range(3)]
        addp(joinm(rib,'prop_hem'),'trim','hips')
        # hair: messy black locks + cat ears (purple inner) + purple horns + striped beanie
        R=__import__('random').Random(5);hr_=[]
        for k in range(40):
            a=R.uniform(-math.pi,math.pi);el=R.uniform(-.2,.9);d=Vector((math.sin(a)*math.cos(el),-math.cos(a)*math.cos(el),math.sin(el)))
            base=hcv+Vector((d.x*hrx*.9,d.y*hrx*.9,d.z*hrz*.9))
            if d.y<-.5 and el<.45:continue  # keep the face clear (fringe added below)
            tip=base+d*hrx*.35+Vector((R.uniform(-.03,.03),R.uniform(-.02,.02),-.06))
            hr_.append(cone('lock',tuple(base),tuple(tip),hrx*.17,.55,8))
        for k in range(7):
            x=(k-3)*hrx*.2;hr_.append(cone('fringe',(x,hcv.y-hrx*.7,hcv.z+hrz*.55),(x*1.2,hcv.y-hrx*1.0,hcv.z+hrz*(.12+.07*(k%2))),hrx*.15,.5,8))
        addp(joinm(hr_[-7:],'prop_hair'),'hair')  # fringe only; dense tufts in pass 2
        ears=[];ein=[]
        for s_ in (-1,1):
            b0=(s_*hrx*.62,hcv.y+hrx*.05,hcv.z+hrz*.95)
            ears.append(cone('cear',b0,(s_*hrx*.82,hcv.y+hrx*.1,hcv.z+hrz*1.55),hrz*.28,.45,16))
            ein.append(cone('cin',(b0[0]*.98,b0[1]-hrz*.08,b0[2]+.01),(s_*hrx*.8,hcv.y,hcv.z+hrz*1.45),hrz*.18,.25,12))
            ears.append(cone('elf',(s_*hrx*.95,hcv.y+hrx*.05,hcv.z-hrz*.05),(s_*hrx*1.35,hcv.y+hrx*.2,hcv.z+hrz*.25),hrz*.12,.4,10))
        addp(joinm(ears,'prop_ears'),'hair');addp(joinm(ein,'prop_earin'),'ear_in')
        pmat('knit_k',(.012,.01,.016,1),.85,sheen=.2)
        bn=Vector((0,hcv.y+hrx*.05,hcv.z+hrz*.42))
        beanie(bn,hrx*1.04,hrx*1.0,hrz*.8,.6,hrx*.12,[(.15,'trim'),(.42,'trim')],'trim','knit_k',knit=14)
        for s_ in (-1,1):
            hs=[(s_*hrx*.4,hcv.y-hrx*.1,hcv.z+hrz*.95),(s_*hrx*.55,hcv.y-hrx*.05,hcv.z+hrz*1.3),(s_*hrx*.48,hcv.y+hrx*.12,hcv.z+hrz*1.55)]
            addp(tube('prop_horn',hs,[hrz*.11,hrz*.07,hrz*.012],res=6),'horn_purple')
        # tattoos: swirl on cheek + neck, freckles
        tt=[]
        for s_,(x,z,r_) in ((1,(hrx*.55,hcv.z-hrz*.35,.022)),(1,(.03,hcv.z-hrz*1.05,.02))):
            pts=[tuple(onb(x+math.cos(t*9)*r_*(1-t*.7),z+math.sin(t*9)*r_*(1-t*.7),off=.003)) for t in [k/15 for k in range(16)]]
            tt.append(tube('tt',pts,[.0022]*16,res=3))
        for k in range(6):tt.append(ell('fr',tuple(onb(R.choice((-1,1))*R.uniform(.05,.1),hcv.z-hrz*R.uniform(.2,.4),off=.002)),(.004,.002,.004),seg=6,ring=4))
        addp(joinm(tt,'prop_tattoo'),'tattoo')
# ================= pass 2: layered glossy eyes, Kairo face + dense hair, knit/fabric maps, frost FX, kitten tips/whiskers
TEX=os.path.join(os.path.dirname(os.path.abspath(__file__)),'tex')
def img(n,data=False):
    im=D.images.load(os.path.join(TEX,n+'.png'),check_existing=True)
    if data:im.colorspace_settings.name='Non-Color'
    return im
def add_normal(m,n,scale,strength=1.0):
    nt=m.node_tree;b=nt.nodes['Principled BSDF'];t=nt.nodes.new('ShaderNodeTexImage');t.image=img(n,True)
    mp=nt.nodes.new('ShaderNodeMapping');mp.inputs['Scale'].default_value=(scale,scale,1);tc=nt.nodes.new('ShaderNodeTexCoord')
    nt.links.new(tc.outputs['UV'],mp.inputs['Vector']);nt.links.new(mp.outputs['Vector'],t.inputs['Vector'])
    nm=nt.nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=strength;nt.links.new(t.outputs['Color'],nm.inputs['Color']);nt.links.new(nm.outputs['Normal'],b.inputs['Normal'])
def uvp(o):
    active(o);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.15,island_margin=.01);bpy.ops.object.mode_set(mode='OBJECT')
def eye_mat(n,tex):
    m=D.materials.new('pm_'+n);m.use_nodes=True;nt=m.node_tree;b=nt.nodes['Principled BSDF'];t=nt.nodes.new('ShaderNodeTexImage');t.image=img(tex)
    nt.links.new(t.outputs['Color'],b.inputs['Base Color']);nt.links.new(t.outputs['Color'],b.inputs['Emission Color']);b.inputs['Emission Strength'].default_value=2.2;b.inputs['Roughness'].default_value=.1
    PM[n]=m;return m
if NEW_OUTFIT:
    etex={'res_nyxbean':'eye_galaxy','res_kairo':'eye_galaxy','res_frostmitt':'eye_lavender'}[PLAN]
    eye_mat('eyeball','nyx_eye' if PLAN=='res_nyxbean' else etex)
    if PLAN in('res_nyxbean','res_frostmitt'):PM['eyeball'].node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value=.55
    m=D.materials.new('pm_cornea');m.use_nodes=True;b=m.node_tree.nodes['Principled BSDF'];b.inputs['Base Color'].default_value=(1,1,1,1);b.inputs['Roughness'].default_value=.02
    b.inputs['Transmission Weight'].default_value=1;b.inputs['IOR'].default_value=1.38;b.inputs['Coat Weight'].default_value=1;PM['cornea']=m
    pmat('lash',(.01,.008,.015,1),.5)
    SC={'res_nyxbean':1.15,'res_kairo':1.05,'res_frostmitt':1.0}[PLAN]
    eyes=[];corn=[];lash=[]
    for n,c in eye_c.items():
        s=-1 if n=='L' else 1;rx,ry,rz=ER*.95*SC,ER*.42,ER*1.05*SC*(.92 if PLAN=='res_kairo' else 1)
        cc=c+Vector((0,-ER*.1,0));SG_=32 if PLAN=='res_nyxbean' else 22;e=ell('eyeb',cc,(rx,ry,rz),seg=SG_,ring=SG_//2)
        uv=e.data.uv_layers.new(name='UVMap') if not e.data.uv_layers else e.data.uv_layers[0]
        for lp in e.data.loops:
            co=e.data.vertices[lp.vertex_index].co;uv.data[lp.index].uv=(.5+(co.x-cc.x)/(2*rx)*s*-1*-1,.5+(co.z-cc.z)/(2*rz))
        eyes.append(e);corn.append(ell('corn',cc+Vector((0,-ER*.03,0)),(rx*1.02,ry*1.08,rz*1.02),seg=SG_,ring=SG_//2))
        lash.append(tube('lash',[tuple(cc+Vector((x*rx*1.05,-ry*.6,math.sqrt(max(0,1-x*x))*rz*1.02))) for x in (-1,-.6,0,.6,1)],[ER*.03,ER*.05,ER*.06,ER*.05,ER*.025],res=4))
    eo=joinm(eyes,'prop_eyes');co_=joinm(corn,'prop_cornea')
    for o_,nm_ in ((eo,'eyeball'),(co_,'cornea')):
        # pblink: squash each eye vertically onto its centre line (runtime drives it with the face blink)
        o_.shape_key_add(name='Basis');k=o_.shape_key_add(name='pblink',from_mix=False)
        for i,v in enumerate(o_.data.vertices):
            c=eye_c['L' if v.co.x<0 else 'R'];k.data[i].co=Vector((v.co.x,v.co.y,c.z+(v.co.z-c.z)*.08))
        setmat(o_,PM[nm_]);o_['bone']='head';props.append(o_)
    addp(joinm(lash,'prop_lash'),'lash')
    def eye_keys(o_):
        # Zeref expression set on the layered eye props (life brain drives p<name>): blink, happy ^^, sleepy, curious, scared, angry
        if not o_.data.shape_keys:o_.shape_key_add(name='Basis')
        def K(name,f):
            if name in o_.data.shape_keys.key_blocks:return
            k=o_.shape_key_add(name=name,from_mix=False)
            for i,v in enumerate(o_.data.vertices):
                n='L' if v.co.x<0 else 'R';c=eye_c[n];s=-1 if n=='L' else 1;k.data[i].co=f(v.co.copy(),c,s)
        R_=ER*1.05*SC
        K('pblink',lambda co,c,s:Vector((co.x,co.y,c.z+(co.z-c.z)*.08)))
        K('phappy',lambda co,c,s:Vector((co.x,co.y,c.z+(co.z-c.z)*.16+R_*.42*(1-min(1,((co.x-c.x)/(R_*.95))**2))-R_*.18)))
        K('psleepy',lambda co,c,s:Vector((co.x,co.y,min(co.z,c.z+R_*.12)-max(0,co.z-c.z-R_*.12)*.0)))
        K('pcurious',lambda co,c,s:c+(co-c)*(1.16 if s<0 else .9))
        K('pscared',lambda co,c,s:c+(co-c)*1.2)
        K('pangry',lambda co,c,s:Vector((co.x,co.y,min(co.z,c.z+R_*.5-(co.x-c.x)*s*.9))))

    if PLAN=='res_kairo':
        pmat('skin_d',(.55,.32,.24,1),.5);pmat('brow',(.01,.008,.012,1),.6)
        ns=surf(0,FACE['eye_z']-ER*1.15);addp(ell('prop_nose',tuple(ns+Vector((0,-.004,0))),(ER*.22,ER*.2,ER*.3),seg=12,ring=8),'skin_d')
        bw_=[]
        for n,c in eye_c.items():
            s=-1 if n=='L' else 1;bw_.append(tube('brow',[tuple(surf(c.x+s*x*ER,c.z+ER*1.35+ER*.15*(1-x*x))+Vector((0,-.004,0))) for x in (-.9,0,.9)],[ER*.07,ER*.1,ER*.05],res=4))
        addp(joinm(bw_,'prop_brows'),'brow')
        # dense hair: scalp cap over back/top of the head + ~150 tufts
        me=body.data.copy();cap_o=D.objects.new('prop_scalp',me);C.collection.objects.link(cap_o);bm=bmesh.new();bm.from_mesh(me);bm.verts.ensure_lookup_table()
        kill=[v for v in bm.verts if (labels[v.index] or '')!='head' or (v.co.y<hcv.y-hrx*.25 and v.co.z<hcv.z+hrz*.55) or v.co.z<hcv.z-hrz*.45]
        bmesh.ops.delete(bm,geom=kill,context='VERTS')
        for v in bm.verts:v.co+=v.normal*.01
        bm.to_mesh(me);bm.free();addp(cap_o,'hair')
        R2=__import__('random').Random(9);tf=[]
        for k in range(150):
            a=R2.uniform(-math.pi,math.pi);el=R2.uniform(-.55,1.4);d=Vector((math.sin(a)*math.cos(el),-math.cos(a)*math.cos(el),math.sin(el)))
            if d.y<-.35 and el<.6:continue
            base=hcv+Vector((d.x*hrx*.95,d.y*hrx*.95,d.z*hrz*.95))
            tip=base+d*hrx*R2.uniform(.18,.4)+Vector((R2.uniform(-.02,.02),R2.uniform(0,.02),-R2.uniform(.03,.08)))
            tf.append(cone('tuft',tuple(base),tuple(tip),hrx*R2.uniform(.1,.16),.5,6))
        # fringe: flattened clump cards from the hairline down over the brow, alternating length (sheet: messy bangs)
        for k in range(16):
            x=(k/15*2-1)*hrx*.85;base=surf(x,hcv.z+hrz*.62)+Vector((0,-.004,0));L=hrz*R2.uniform(.42,.62)
            pts=[tuple(base),tuple(base+Vector((x*.06,-.03,-L*.5))),tuple(base+Vector((x*.12+R2.uniform(-.01,.01),-.028,-L)))]
            c_=tube('fr',pts,[hrx*.07,hrx*.05,hrx*.006],res=4);c_.scale=(1,.45,1) if False else (1,1,1);tf.append(c_)
        for k in range(26):  # side + nape locks (cards hanging down)
            s_=R2.choice((-1,1));a=R2.uniform(.2,1.6);base=hcv+Vector((s_*math.sin(a)*hrx*.98,math.cos(a)*hrx*.6,R2.uniform(-.1,.5)*hrz))
            tip=base+Vector((s_*R2.uniform(.02,.05),R2.uniform(0,.04),-hrz*R2.uniform(.35,.6)))
            tf.append(cone('lock',tuple(base),tuple(tip),hrx*R2.uniform(.1,.14),.35,6))
        o=joinm(tf,'prop_tufts');active(o);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.remove_doubles(threshold=.0005);bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT');cap(o,2350);setmat(o,PM['hair']);o['bone']='head';props.append(o)
        pmat('lip',(.42,.18,.16,1),.45,coat=.3);pmat('skin_ear',(.62,.38,.28,1),.5);pmat('freckle',(.18,.09,.06,1),.7)
        lz=FACE['mouth_z'];lp=[]
        lp.append(tube('lipU',[tuple(surf(x*ER*.55,lz+ER*.12+abs(x)*-ER*.06)+Vector((0,-.003,0))) for x in (-1,-.5,0,.5,1)],[ER*.03,ER*.07,ER*.06,ER*.07,ER*.03],res=4))
        lp.append(tube('lipL',[tuple(surf(x*ER*.45,lz-ER*.12)+Vector((0,-.004,0))) for x in (-1,0,1)],[ER*.04,ER*.09,ER*.04],res=4))
        addp(joinm(lp,'prop_lips'),'lip')
        el=[]
        for s_ in (-1,1):  # pointed elf ears from the side of the head, sweeping back/up
            b0=hcv+Vector((s_*hrx*.97,hrx*.05,-hrz*.05));el.append(cone('elf',tuple(b0),tuple(b0+Vector((s_*hrx*.45,hrx*.3,hrz*.42))),hrz*.17,.35,12))
        addp(joinm(el,'prop_elfears'),'skin_ear',n=400)
        fk=[]
        for k in range(14):
            sx=R2.choice((-1,1));x=sx*R2.uniform(.25,.75)*FACE['eye_x']*1.5;z=FACE['eye_z']-ER*R2.uniform(1.1,1.8)
            fk.append(ell('fk',tuple(surf(x,z)+Vector((0,.0005,0))),(ER*.05,ER*.02,ER*.05),seg=6,ring=3))
        for d_ in ((-1.05,-1.3),(-1.25,-1.45),(-.9,-1.55)):fk.append(ell('mole',tuple(surf(d_[0]*FACE['eye_x'],FACE['eye_z']+d_[1]*ER)+Vector((0,.0002,0))),(ER*.075,ER*.03,ER*.075),seg=8,ring=4))
        addp(joinm(fk,'prop_freckles'),'freckle',n=500)
    if PLAN=='res_frostmitt':  # defined face: slate eye rims, catchlights, blue-grey nose + w mouth, muzzle shadow (sheet)
        pmat('rimf',(.035,.04,.09,1),.3,coat=.9);pmat('catchf',(1,1,1,1),.08,emit=(1,1,1,1),es=3.2);pmat('nosef',(.12,.13,.26,1),.28,coat=.8)
        rims,cat=[],[]
        for n,c in eye_c.items():
            s=-1 if n=='L' else 1;rx,rz=ER*.95*.95,ER*1.05*.95;cc=c+Vector((0,-ER*.1,0))
            rims.append(tube('rim',[(cc.x+math.cos(a)*rx*1.03,cc.y-ER*.16,cc.z+math.sin(a)*rz*1.03) for a in [k/28*2*math.pi for k in range(29)]],[ER*.08]*29,res=3))
            cat.append(ell('c1',(cc.x-s*rx*.3,cc.y-ER*.5,cc.z+rz*.38),(rx*.15,ER*.04,rz*.15),seg=12,ring=6))
        addp(joinm(rims,'prop_eyerim'),'rimf');addp(joinm(cat,'prop_catch'),'catchf')
        np_=surf(0,FACE['eye_z']-ER*1.25);addp(ell('prop_knose',tuple(np_+Vector((0,-.006,0))),(ER*.24,ER*.14,ER*.15),seg=12,ring=8),'nosef')
        w=[tuple(surf(x*ER*.42,FACE['eye_z']-ER*1.65+abs(x)*ER*.12*(1 if abs(x)>.5 else -1))+Vector((0,-.004,0))) for x in (-1,-.5,0,.5,1)]
        addp(tube('prop_kmouth',w,[ER*.042]*5,res=4),'rimf')
        R3=__import__('random').Random(21);ic=[]
        for k in range(400):
            if len(ic)>=18:break  # fewer, longer, thicker: read as icicles, not speckles
            v=body.data.vertices[R3.randrange(len(body.data.vertices))]
            if v.normal.y>-.45 or v.normal.z>.15 or not(.18<v.co.z<.55):continue  # chest front edge, rooted outside the fur
            L=R3.uniform(.12,.2);p=v.co+v.normal*.075
            for j in range(R3.choice((1,2))):
                off=Vector((R3.uniform(-.008,.008),R3.uniform(-.008,.008),0))
                ic.append(cone('ice',tuple(p+off),tuple(p+off+Vector((v.normal.x*.01,v.normal.y*.01,-L*(1-.35*j)))),R3.uniform(.022,.032),1,10))
        def drip(p,L,r,n=8):ic.append(cone('ice',tuple(p),tuple(Vector(p)+Vector((0,0,-L))),r,1,n))
        for x in (-.55,-.2,.15,.5):  # chin fringe
            p=surf(x*ER,FACE['eye_z']-ER*2.2)+Vector((0,.01,0));drip(p,R3.uniform(.05,.08),R3.uniform(.009,.013))
        cxy=Vector((hb.x,hb.y,0));brx,bry=hrx*1.15*1.07,hrx*1.1*1.07
        for k in range(12):  # hat brim: sides and back only, never over the eyes
            a=-math.pi/2+math.radians(55)+k*(2*math.pi-math.radians(110))/11
            drip(Vector((cxy.x+math.cos(a)*brx,cxy.y+math.sin(a)*bry,hb.z-.004)),R3.uniform(.04,.09),R3.uniform(.008,.012))
        m=D.materials.new('pm_iceclear');m.use_nodes=True;b=m.node_tree.nodes['Principled BSDF'];b.inputs['Base Color'].default_value=(.62,.82,1,1);b.inputs['Roughness'].default_value=.12
        b.inputs['Transmission Weight'].default_value=.12;b.inputs['IOR'].default_value=1.31;b.inputs['Subsurface Weight'].default_value=.4;b.inputs['Coat Weight'].default_value=1;b.inputs['Emission Color'].default_value=(.35,.62,1,1);b.inputs['Emission Strength'].default_value=.3;PM['iceclear']=m
        for o_ in [x for x in props if x.name.startswith('prop_icicles')]:props.remove(o_);D.objects.remove(o_,do_unlink=True)
        o=joinm(ic,'prop_icicles');cap(o,2400);setmat(o,PM['iceclear']);o['bone']='spine';props.append(o)
        m=D.materials.new('pm_mist');m.use_nodes=True;b=m.node_tree.nodes['Principled BSDF'];b.inputs['Base Color'].default_value=(.85,.9,1,1);b.inputs['Alpha'].default_value=.28
        b.inputs['Emission Color'].default_value=(.6,.7,1,1);b.inputs['Emission Strength'].default_value=.12;m.blend_method='BLEND';PM['mist']=m
        ms=[]
        for k in range(7):  # curling frost-mist ribbons around legs and tail
            a0=R3.uniform(0,2*math.pi);r0=R3.uniform(.42,.55);z0=R3.uniform(.05,.35)  # mist kept clear of the body (it read as white streaks on his sides)
            pts=[(math.cos(a0+t*2.2)*r0*(1+t*.4),math.sin(a0+t*2.2)*r0*(1+t*.4),z0+t*.25+.03*math.sin(t*9)) for t in [i/7 for i in range(8)]]
            ms.append(tube('mist',pts,[.004,.012,.018,.02,.018,.014,.008,.002],res=5))
        if os.environ.get('FROST_MIST'):addp(joinm(ms,'prop_mist'),'mist','root')  # off: the thin tubes read as white streaks/lines on his sides
        else:[D.objects.remove(m_,do_unlink=True) for m_ in ms]
    if PLAN=='res_nyxbean':
        pmat('pink',(1,.42,.75,1),.4,emit=(1,.35,.75,1),es=1.6);pmat('whisker',(.92,.9,1,1),.3)
        pk=[]
        for a,s in zip(EA,(-1,1)):
            t_=Vector(ear_tip(a,s,ehr*1.0));pk.append(cone('pt',tuple(Vector(ear_tip(a,s,ehr*.7))),tuple(t_+Vector((0,0,.012))),ehr*.15,.5,10))
        pk.append(tube('tt',[TP[-3],TP[-2],TP[-1],tuple(Vector(TP[-1])+td*trad*.8)],[trad*.42,trad*.48,trad*.55,trad*.3],res=6))
        addp(joinm(pk[:-1],'prop_eartips'),'pink');D.objects.remove(pk[-1],do_unlink=True)
        pmat('pink_dim',(.35,.12,.3,1),.5,emit=(.5,.15,.45,1),es=.4);pmat('pink_pale',(1,.75,.9,1),.35,emit=(1,.6,.85,1),es=2.2)
        A,B_,C_=Vector(TP[-3]),Vector(TP[-2]),Vector(TP[-1]);E_=C_+td*trad*.8
        for nm_,pts_,rr,mm in (('prop_tail_g0',[A,(A+B_)/2],[trad*.42,trad*.45],'pink_dim'),('prop_tail_g1',[(A+B_)/2,B_,C_],[trad*.45,trad*.5,trad*.55],'pink'),('prop_tail_g2',[C_,E_],[trad*.55,trad*.15],'pink_pale')):
            o=tube(nm_,[tuple(q) for q in pts_],rr,res=6);cap(o,300);setmat(o,PM[mm]);o['bone']='tail.%d'%(len(TP)-2);props.append(o)
        # sculpted toe beans on each paw
        pmat('bean',(.5,.2,.4,1),.45,coat=.4);bn_=[]
        for lab_ in set(l for l in labels if l and l.startswith('toe')):
            vs=[v.co for v,l in zip(body.data.vertices,labels) if l==lab_];c_=sum(vs,Vector())/len(vs);mz=min(v.z for v in vs)
            bn_.append(ell('bean',(c_.x,c_.y-.004,mz+.006),(.012,.012,.006),seg=10,ring=6))
        if bn_:addp(joinm(bn_,'prop_beans'),'bean','root')
        wk=[]
        for s in (-1,1):
            for j in range(3):
                b0=surf(s*ER*.9,FACE['mouth_z']+ER*(.35-.2*j))
                wk.append(tube('wk',[tuple(b0),tuple(b0+Vector((s*.09,-.01,.012-.012*j))),tuple(b0+Vector((s*.18,.01,.0-.03*j)))],[.0022,.0016,.0006],res=4))
        addp(joinm(wk,'prop_whiskers'),'whisker')

    if PLAN=='res_nyxbean':
        # --- pass 4: sack hat tilt (band follows the head), ears out through the hat sides, kitten face, glossy horns
        from mathutils import Matrix
        hatp=[o_ for o_ in props if o_.name.split('.')[0] in('prop_cuff','prop_crown','prop_seams','prop_bandribs','prop_band')]
        Rm=Matrix.Translation(hb)@Matrix.Rotation(-.26,4,'X')@Matrix.Translation(-hb)
        for o_ in hatp:o_.data.transform(Rm);o_['bone']='hat'  # spring bone: sack jiggle + band follow-through
        
        pmat('earfur',(.012,.009,.02,1),.7,sheen=.6);pmat('earin',(.6,.22,.45,1),.5,emit=(.5,.15,.4,1),es=.3)
        eo_,ei_=[],[]
        for s_ in (-1,1):
            b0=(s_*hrx*1.0,hcv.y+hrx*.1,hcv.z+hrz*.72);t0=(s_*hrx*1.55,hcv.y+hrx*.15,hcv.z+hrz*1.7)
            eo_.append(cone('cear',b0,t0,hrz*.46,.42,16));ei_.append(cone('cin',(b0[0]*1.02,b0[1]-hrz*.09,b0[2]+.01),(t0[0]*.97,t0[1]-hrz*.06,t0[2]-.02),hrz*.2,.22,12))
        addp(joinm(eo_,'prop_catears'),'earfur',n=900);addp(joinm(ei_,'prop_catearin'),'earin')
        for o_ in [x for x in props if x.name.startswith('prop_eartips')]:
            for v in o_.data.vertices:pass
        tp=[]
        for s_ in (-1,1):tp.append(cone('tip',(s_*hrx*1.45,hcv.y+hrx*.14,hcv.z+hrz*1.48),(s_*hrx*1.57,hcv.y+hrx*.15,hcv.z+hrz*1.74),hrz*.07,.5,10))
        addp(joinm(tp,'prop_eartips2'),'pink')
        for o_ in [x for x in props if x.name.startswith('prop_eartips') and not x.name.startswith('prop_eartips2')]:props.remove(o_);D.objects.remove(o_,do_unlink=True)
        # kitten face: rimmed eyes, crisp catchlights, tiny pink nose + w mouth
        pmat('rim',(.004,.003,.006,1),.3,coat=1);pmat('catch',(1,1,1,1),.1,emit=(1,1,1,1),es=2.2);pmat('nosepk',(.75,.35,.5,1),.3,coat=.6)
        rims,cat=[],[]
        for n,c in eye_c.items():
            s=-1 if n=='L' else 1;rx,rz=ER*.95*.92,ER*1.05*.92;cc=c+Vector((0,-ER*.1,0))
            rims.append(tube('rim',[(cc.x+math.cos(a)*rx*1.02,cc.y-ER*.18,cc.z+math.sin(a)*rz*1.02) for a in [k/28*2*math.pi for k in range(29)]],[ER*.07]*29,res=3))
            cat.append(ell('c1',(cc.x-s*rx*.3,cc.y-ER*.5,cc.z+rz*.38),(rx*.17,ER*.04,rz*.17),seg=12,ring=6))
            cat.append(ell('c2',(cc.x+s*rx*.3,cc.y-ER*.5,cc.z-rz*.35),(rx*.07,ER*.03,rz*.07),seg=8,ring=4))
        addp(joinm(rims,'prop_eyerim'),'rim');addp(joinm(cat,'prop_catch'),'catch')
        np_=surf(0,FACE['eye_z']-ER*1.2);addp(ell('prop_knose',tuple(np_+Vector((0,-.006,0))),(ER*.2,ER*.12,ER*.13),seg=12,ring=8),'nosepk')
        w=[tuple(surf(x*ER*.4,FACE['eye_z']-ER*1.55+abs(x)*ER*.12*(1 if abs(x)>.5 else -1))+Vector((0,-.004,0))) for x in (-1,-.5,0,.5,1)]
        addp(tube('prop_kmouth',w,[ER*.025]*5,res=3),'rim')
    if PLAN=='res_nyxbean':
        add_normal(PM['puffy'],'nyx_puffer_normal',1,.9)
        nt=PM['puffy'].node_tree;t=nt.nodes.new('ShaderNodeTexImage');t.image=img('nyx_puffer_rough',True);mr=nt.nodes.new('ShaderNodeMapRange');mr.inputs[3].default_value=.82;mr.inputs[4].default_value=1;nt.links.new(t.outputs['Color'],mr.inputs[0]);nt.links.new(mr.outputs[0],nt.nodes['Principled BSDF'].inputs['Roughness'])
        uvp_list=[o_ for o_ in props if o_.data.materials and o_.data.materials[0].name=='pm_puffy']
        for o_ in uvp_list:uvp(o_)
    # eyelids (upper+lower shells over each eye); basis = retracted to pole, keys close them along expression curves
    if PLAN in('res_nyxbean','res_frostmitt'):
        pmat('tuftcard',{'res_nyxbean':(.016,.011,.03,1),'res_frostmitt':(.72,.76,.86,1)}[PLAN],.85,sheen=.4)
        R4=__import__('random').Random(33);cd=[];ck=[]
        for k in range(40):  # cheek fins (sideways) + chest ruff cards (downward) for silhouette
            if k<16:s_=-1 if k%2 else 1;z=FACE['eye_z']-ER*R4.uniform(.6,2.0);base=surf(s_*hrx*.8,z);base=Vector((s_*hrx*R4.uniform(.9,1.0),base.y+hrx*.3,z));d=Vector((s_*1,.35,-.25+R4.uniform(-.2,.2)))
            else:
                x=R4.uniform(-.09,.09);z=R4.uniform(hcv.z-hrz*1.35,hcv.z-hrz*.9);h_=body_bvh.ray_cast(Vector((x,-2,z)),Vector((0,1,0)))
                if not h_[0]:continue
                base=h_[0];d=Vector((x*2,-.5,-1))
            d.normalize();L=hrx*(R4.uniform(.42,.62) if k<16 else R4.uniform(.22,.36))
            (ck if k<16 else cd).append(cone('card',tuple(base),tuple(base+d*L),hrx*(R4.uniform(.13,.18) if k<16 else R4.uniform(.08,.12)),.22,6))
        addp(joinm(ck,'prop_cheekcards'),'tuftcard','head',n=400)
        if cd:addp(joinm(cd,'prop_chestcards'),'tuftcard','spine',n=600)
    pmat('lid',{'res_nyxbean':(.018,.012,.035,1),'res_kairo':(.03,.03,.06,1),'res_frostmitt':(.55,.6,.75,1)}[PLAN],.85)
    def mklid(name,upper,lines):
        Rl=ER*1.05*SC*1.12;N=13 if PLAN=='res_nyxbean' else 10;vs=[];fs=[];base=[]
        for n,c in eye_c.items():
            s=-1 if n=='L' else 1;o0=len(vs)
            for i in range(N):
                for j in range(N):
                    u,w=i/(N-1)*2-1,j/(N-1)*2-1;r=max(1e-6,math.hypot(u,w));k=max(abs(u),abs(w))/r;vs.append((c.x+u*k*Rl*.98,w*k,c.z,s,c.y))
            for i in range(N-1):
                for j in range(N-1):a=o0+i*N+j;fs.append((a,a+N,a+N+1,a+1))
        def place(line):
            out=[]
            for (x,wk,cz,s,cy) in vs:
                cx=x-(x-0) if False else None
            return out
        cs={n:c for n,c in eye_c.items()}
        def pos(v,line):
            x,wk,cz,s,cy=v;c=cs['L' if s<0 else 'R'];dx=x-c.x;h=math.sqrt(max(0,(Rl*.98)**2-dx*dx))
            z0=c.z+wk*h;L=line(dx/Rl,s)*Rl+c.z
            z=max(z0,L) if upper else min(z0,L);z=max(c.z-h,min(c.z+h,z))
            y=c.y-math.sqrt(max(0,Rl*Rl-dx*dx-(z-c.z)**2))
            return Vector((x,y,z))
        me=D.meshes.new(name);me.from_pydata([pos(v,lambda t,s:(1.2 if upper else -1.2)) for v in vs],[],fs);o=D.objects.new(name,me);C.collection.objects.link(o)
        o.shape_key_add(name='Basis')
        for kn,fn in lines.items():
            k=o.shape_key_add(name=kn,from_mix=False)
            for i,v in enumerate(vs):k.data[i].co=pos(v,fn)
        setmat(o,PM['lid']);o['bone']='head';props.append(o)
    it=lambda t,s:t*(-s)
    mklid('prop_lidup',True,{'pblink':lambda t,s:-1.05,'psleepy':lambda t,s:.05,'pangry':lambda t,s:.42-.6*it(t,s),'pscared':lambda t,s:1.2,'pcurious':lambda t,s:(.75 if s>0 else 1.2)})
    mklid('prop_liddn',False,{'phappy':lambda t,s:-.05+.32*(1-t*t),'psleepy':lambda t,s:-.55,'pblink':lambda t,s:-1.2,'pangry':lambda t,s:-.6})
    for o_ in props:
        if o_.name.split('.')[0] in('prop_eyes','prop_cornea','prop_eyerim','prop_catch','prop_lash'):eye_keys(o_)
    for n_,(tx,sc_) in {'knit':('knit_normal',3),'knit_k':('knit_normal',3),'cloth':('fabric_normal',4)}.items():
        if n_ in PM:add_normal(PM[n_],tx,sc_,.3)
    for o_ in props:
        if o_.data.materials and o_.data.materials[0].name[3:] in ('knit','knit_k','puffy','cloth','hair'):uvp(o_)
if PLAN=='res_shardhowl':
    import random;rnd=random.Random(7);sh=[]
    for i in range(34):
        y=rnd.uniform(-.48,.45);side=rnd.choice((-1,1));x=side*rnd.uniform(0,.12);z=.6-abs(y+.05)*.25+rnd.uniform(-.03,.02)
        L_=rnd.uniform(.2,.42)*(1.3 if y<-.2 else 1);d=Vector((side*rnd.uniform(.3,.9),rnd.uniform(.2,.8),rnd.uniform(.6,1.2))).normalized()
        sh.append(cone('s',(x,y,z-.06),tuple(Vector((x,y,z))+d*L_),rnd.uniform(.05,.09),rnd.uniform(.5,.9),5))
    for k in range(5):  # crown of shards on the head
        a=(k-2)*.35;b=Vector(FACE['head_c'])+Vector((math.sin(a)*.12,.06,.18));sh.append(cone('s',tuple(b),tuple(b+Vector((math.sin(a)*.1,.14,.22))),.04,.6,5))
    prop('prop_shard',sh,'spine',tris=2400)
if PLAN=='res_velvetcoil':
    sp=[cone('s',(0,FACE['head_c'][1]+.05+i*.09,FACE['head_c'][2]+.12-i*.09),(0,FACE['head_c'][1]+.1+i*.09,FACE['head_c'][2]+.24-i*.09),.035,.4,8) for i in range(5)]
    prop('prop_spikes',sp,'neck')

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
    FL={'wing_moth':0,'ear_leaf':0,'ear_dhorn':0,'wing_dragon':0,'ear_horns':0,'ear_crown':0,'ear_frill':.5,'tail_brush':1.0,'ear_fox':.55}.get(nm,.62)
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
if PLAN=='res_nyxbean':bone('hat',tuple(hb),tuple(hb+Vector((0,.09,.12))),'head')
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
def body_cands(i,co):return body_cands_l(labels[i],co)
def body_cands_l(lab,co):
    lab=lab or ''
    if lab.startswith('toe'):lab='paw'+lab[3:5]
    if lab.startswith('shin'):lab='leg'+lab[4:]
    if lab.startswith('leg') or lab.startswith('paw'):
        fb,n=lab[3],lab[4];return ['leg%s.0.%s'%(fb,n),'leg%s.1.%s'%(fb,n)]+(['spine'] if fb=='F' else ['hips'])
    if lab.startswith('spike'):return ['spine','hips','neck']
    if lab.startswith('rock') or lab.startswith('shoulder') or lab in('chest','belly','bulb'):return ['spine','hips']
    if lab in('beak','hood','stem'):return ['head','neck']
    if lab in('dorsal','finL','finR','belfin'):return ['spine']
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
for o in props:
    if o['bone']=='*':
        L_=CL[o.name];skin(o,(lambda L_:(lambda i,co:body_cands_l(L_[i],co)))(L_),4)
    else:skin(o,(lambda b_:(lambda i,co:[b_]))(o['bone']),0)
skin(detail,lambda i,co:(['tail.%d'%(len(TP)-2)] if dk in('comet','foxfire') else ['spine'] if dk=='ember_heart' else ['head']),0)
for o in [body,face,detail]+props+list(variants.values()):
    for p in o.data.polygons:p.use_smooth=True
tot=tris_of(body)+tris_of(face)+tris_of(detail)
print('TRIS body',tris_of(body),'face',tris_of(face),'detail',tris_of(detail),{k:tris_of(v) for k,v in variants.items()})
_keep=set([body,face,detail]+props+list(variants.values()))
for o in [o for o in C.scene.objects if o.type=='MESH' and o not in _keep]:D.objects.remove(o,do_unlink=True)  # stray build scraps (were rendering as white flecks)
for o in C.scene.objects:o.select_set(False)
rig.select_set(True)
for o in [body,face,detail]+props+list(variants.values()):o.select_set(True)
active(rig)
for o in [body,face,detail]+props+list(variants.values()):o.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT,export_format='GLB',use_selection=True,export_skins=True,export_morph=True,export_morph_normal=False,export_animations=False,export_yup=True,export_vertex_color='ACTIVE')
bpy.ops.wm.save_as_mainfile(filepath=OUT.replace('.glb','.blend'))
print('EXPORTED',OUT,os.path.getsize(OUT))
