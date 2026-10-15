"""Zeref v1 — headless Blender build. Design reference: components/zeref-figure.tsx (viewBox 400, 1 unit = 100px, ground y=368).
Continuous body: parts -> voxel remesh (fused) -> smooth -> decimate. Rig, shape keys, PBR, glTF."""
import bpy, bmesh, math, sys, os
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
HERE=os.path.dirname(os.path.abspath(__file__))
OUT=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else HERE+'/zeref.glb'
VOXEL=float(os.environ.get('VOXEL','0.022')); BODY_TRIS=int(os.environ.get('BODY_TRIS','12000'))
bpy.ops.wm.read_factory_settings(use_empty=True)
C=bpy.context; D=bpy.data
def hx(h,a=1.0):
    h=h.lstrip('#');c=[int(h[i:i+2],16)/255 for i in (0,2,4)]
    return tuple(((x/12.92) if x<=.04045 else ((x+.055)/1.055)**2.4) for x in c)+(a,)
def active(o):
    for x in C.selected_objects:x.select_set(False)
    C.view_layer.objects.active=o;o.select_set(True)
def apply_all(o):
    active(o);bpy.ops.object.convert(target='MESH')
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
def ell(name,loc,r,rot=(0,0,0),seg=48,ring=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg,ring_count=ring,radius=1,location=loc,rotation=rot)
    o=C.active_object;o.name=name;o.scale=r;apply_all(o);return o
def cone(name,base,tip,rb,flat=1.0,seg=32,tipr=0.03):
    b=Vector(base);t=Vector(tip);d=t-b
    bpy.ops.mesh.primitive_cone_add(vertices=seg,radius1=rb,radius2=tipr,depth=d.length,location=(b+t)/2)
    o=C.active_object;o.name=name;o.scale=(1,flat,1)
    o.rotation_mode='QUATERNION';o.rotation_quaternion=Vector((0,0,1)).rotation_difference(d.normalized())
    apply_all(o);return o
def tube(name,pts,radii,res=6,bev=12,closed=False):
    cu=D.curves.new(name,'CURVE');cu.dimensions='3D';cu.bevel_depth=1.0;cu.bevel_resolution=bev//4;cu.resolution_u=res
    cu.use_fill_caps=True
    sp=cu.splines.new('NURBS');sp.points.add(len(pts)-1);sp.use_endpoint_u=True;sp.order_u=min(4,len(pts))
    for p,(x,y,z),r in zip(sp.points,pts,radii):p.co=(x,y,z,1);p.radius=r
    o=D.objects.new(name,cu);C.collection.objects.link(o);apply_all(o);return o
def join(objs,name):
    active(objs[0])
    for o in objs:o.select_set(True)
    bpy.ops.object.join();o=C.active_object;o.name=name;return o
# =================================================================== body parts (fused)
M=-1  # front is -Y
parts={}
parts['body']=ell('body',(0,.04,.7),(.66,.58,.56))
parts['belly']=ell('belly',(0,-.02,.4),(.74,.6,.4))
for s,n in ((-1,'L'),(1,'R')):
    parts['haunch'+n]=ell('haunch'+n,(s*.56,.14,.24),(.3,.4,.24))
    parts['paw'+n]=ell('paw'+n,(s*.3,-.44,.15),(.22,.26,.15))
parts['neck']=ell('neck',(0,0,1.18),(.56,.5,.28))
parts['head']=ell('head',(0,-.02,1.95),(1.14,.84,.82))
parts['jaw']=ell('jaw',(0,-.1,1.6),(1.0,.68,.42))
parts['muzzle']=ell('muzzle',(0,-.66,1.6),(.3,.18,.18))
for s,n in ((-1,'L'),(1,'R')):
    # jagged cheek fluff (head path tufts at x≈±1.1, z≈1.5)
    parts['cheekA'+n]=cone('cheekA'+n,(s*.92,-.05,1.7),(s*1.36,-.02,1.48),.22,flat=.6)
    parts['cheekB'+n]=cone('cheekB'+n,(s*.84,-.08,1.52),(s*1.14,-.06,1.3),.17,flat=.6)
    parts['ear'+n]=cone('ear'+n,(s*.66,.04,2.36),(s*.9,.06,3.26),.44,flat=.38,tipr=.03)
for i,(x,h) in enumerate(((-.2,2.98),(0,3.1),(.2,2.96))):
    parts['tuft%d'%i]=cone('tuft%d'%i,(x,-.05,2.55),(x*1.15,-.06,h),.12,flat=.6,tipr=.01)
TAIL=[(.5,.42,.32),(1.0,.62,.34),(1.42,.55,.7),(1.55,.4,1.25),(1.4,.25,1.62),(1.15,.18,1.72)]
parts['tail']=tube('tail',TAIL,[.2,.21,.2,.17,.14,.11])
names=list(parts.keys())
# build BVH of each part (for labels/weights) BEFORE fusing
deps=C.evaluated_depsgraph_get()
def bvh(o):
    bm=bmesh.new();bm.from_mesh(o.data);t=BVHTree.FromBMesh(bm);bm.free();return t
part_bvh={k:bvh(o) for k,o in parts.items()}
fur=join([parts[k] for k in names],'fur')
active(fur)
m=fur.modifiers.new('remesh','REMESH');m.mode='VOXEL';m.voxel_size=VOXEL;m.adaptivity=0
bpy.ops.object.modifier_apply(modifier='remesh')
m=fur.modifiers.new('smooth','CORRECTIVE_SMOOTH');m.factor=.6;m.iterations=8;m.use_only_smooth=True
bpy.ops.object.modifier_apply(modifier='smooth')
m=fur.modifiers.new('lap','LAPLACIANSMOOTH');m.lambda_factor=.6;m.iterations=4;m.use_volume_preserve=True
bpy.ops.object.modifier_apply(modifier='lap')
ratio=min(1.0,BODY_TRIS/max(1,len(fur.data.polygons)*2))
m=fur.modifiers.new('dec','DECIMATE');m.ratio=ratio;m.use_collapse_triangulate=True
bpy.ops.object.modifier_apply(modifier='dec')
print('fur tris',sum(len(p.vertices)-2 for p in fur.data.polygons))
# raycast helper on the fused fur
fur_bvh=bvh(fur)
def surf_y(x,z):
    hit=fur_bvh.ray_cast(Vector((x,-3,z)),Vector((0,1,0)))
    return hit[0] if hit[0] else Vector((x,-.7,z))
# =================================================================== eyes + lids
EYE_RX,EYE_RZ,EYE_DEPTH=.37,.41,.13
eyes={}
for s,n in ((-1,'L'),(1,'R')):
    cx,cz=s*.47,1.9; p=surf_y(cx,cz)
    cy=p.y+EYE_DEPTH*.78   # sphere center so front cap bulges just out of the face
    eyes[n]=(cx,cy,cz)
    e=ell('eye'+n,(cx,cy,cz),(EYE_RX,EYE_DEPTH,EYE_RZ),seg=36,ring=18)
    # planar UV from front
    me=e.data
    while me.uv_layers:me.uv_layers.remove(me.uv_layers[0])
    uv=me.uv_layers.new(name='UVMap')
    for poly in me.polygons:
        for li in poly.loop_indices:
            v=me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv=((v.x-cx)/(2*EYE_RX)+.5,(v.z-cz)/(2*EYE_RZ)+.5)
    parts['eye'+n]=e
def lid_point(cx,cy,cz,u,h,scale=1.06):
    a,b,c=EYE_RX*scale,EYE_DEPTH*scale,EYE_RZ*scale
    q=max(0.0,1-u*u-h*h); return Vector((cx+a*u,cy-b*math.sqrt(q),cz+c*h))
NU,NS=26,8
def lid_edge(kind,side,u,state):
    """returns the h (normalized height) of the moving lid edge for a given state"""
    top=math.sqrt(max(0,1-u*u))*.995; bot=-top
    inner=-u*side   # +1 toward the nose
    if kind=='U':
        e={'rest':top-.035,'blink':-.12-.22*(1-u*u),'sleepy':.05+.06*u*u,'angry':.42-.38*inner,'happy':top-.035,
           'scared':top-.035,'curious':top-.035}[state]
        return max(bot+.02,min(top-.02,e))
    else:
        e={'rest':bot+.035,'happy':-.08+.12*u*u*0-.0,'blink':bot+.035,'sleepy':bot+.035,'angry':-.55,'scared':bot+.035,'curious':bot+.035}[state]
        return max(bot+.02,min(top-.02,e))
lid_objs=[];lid_meta=[]
for s,n in ((-1,'L'),(1,'R')):
    cx,cy,cz=eyes[n]
    for kind in ('U','D'):
        bm=bmesh.new();grid=[]
        for i in range(NU):
            u=-.985+1.97*i/(NU-1);row=[]
            for j in range(NS):
                row.append(bm.verts.new((0,0,0)))
            grid.append(row)
        for i in range(NU-1):
            for j in range(NS-1):
                f=[grid[i][j],grid[i+1][j],grid[i+1][j+1],grid[i][j+1]]
                bm.faces.new(f if kind=='U' else f[::-1])
        me=D.meshes.new('lid'+kind+n);bm.to_mesh(me);bm.free()
        o=D.objects.new('lid'+kind+n,me);C.collection.objects.link(o)
        lid_objs.append(o);lid_meta.append((o,kind,s,n))
def lid_positions(kind,s,n,state):
    cx,cy,cz=eyes[n];pts=[]
    for i in range(NU):
        u=-.985+1.97*i/(NU-1);top=math.sqrt(max(0,1-u*u))*.995;edge=lid_edge(kind,s,u,state)
        for j in range(NS):
            t=j/(NS-1)
            h=(top+(edge-top)*t) if kind=='U' else (-top+(edge+top)*t)
            pts.append(lid_point(cx,cy,cz,u,h,1.06+.01*(1-t)))
    return pts
for o,kind,s,n in lid_meta:
    for v,p in zip(o.data.vertices,lid_positions(kind,s,n,'rest')):v.co=p
# =================================================================== decals / features (shrinkwrapped to fur)
def wrap(o,off=.008):
    active(o);m=o.modifiers.new('sw','SHRINKWRAP');m.target=fur;m.wrap_method='PROJECT';m.use_project_y=True
    m.use_negative_direction=True;m.use_positive_direction=True;m.offset=off
    bpy.ops.object.modifier_apply(modifier='sw')
def frontpts(pts2):  # (x,z) -> on face
    return [(x,surf_y(x,z).y-.02,z) for x,z in pts2]
feat={}
# brows (vector y132 -> z 2.36)
for s,n in ((-1,'L'),(1,'R')):
    xs=[s*.66,s*.47,s*.28];zs=[2.36,2.43,2.39]
    feat['brow'+n]=tube('brow'+n,frontpts(list(zip(xs,zs))),[.022,.028,.022],bev=8);wrap(feat['brow'+n],.02)
# nose + mouth (w)
feat['nose']=cone('nose',(0,surf_y(0,1.66).y-.01,1.69),(0,surf_y(0,1.6).y-.01,1.6),.07,flat=.5,seg=3,tipr=.005)
mw=[(-.17,1.53),(-.09,1.45),(0,1.53),(.09,1.45),(.17,1.53)]
feat['mouth']=tube('mouth',frontpts(mw),[.016,.02,.018,.02,.016],bev=8);wrap(feat['mouth'],.015)
# blush
for s,n in ((-1,'L'),(1,'R')):
    p=surf_y(s*.82,1.56);feat['blush'+n]=ell('blush'+n,(p.x,p.y+.03,p.z),(.17,.05,.085),seg=16,ring=8)
# forehead crescent + star
def crescent_pts(cx,cz,r):
    out=[];
    for k in range(13):
        a=math.radians(60+240*k/12);out.append((cx+r*math.cos(a)*.9,cz+r*math.sin(a)))
    return out
cp=crescent_pts(.08,2.52,.15)
feat['crescent']=tube('crescent',frontpts(cp),[.02,.04,.055,.065,.07,.07,.07,.07,.065,.055,.04,.025,.012],res=3,bev=8);wrap(feat['crescent'],.02)
# moon horns: crescent arcs beside the ears
for s,n in ((-1,'L'),(1,'R')):
    hp=[(s*1.0,.14,2.22),(s*1.2,.12,2.48),(s*1.22,.1,2.8),(s*1.08,.08,3.04)]
    feat['horn'+n]=tube('horn'+n,hp,[.09,.085,.06,.012],bev=12)
# choker + gem + charm
ck=[];
for k in range(17):
    a=math.radians(-90+k*360/16)
    ck.append((.6*math.cos(a),.5*math.sin(a)-.03,1.2-.06*math.cos(a+math.pi/2)*0+(-.05 if math.sin(a)<0 else .02)))
feat['choker']=tube('choker',ck,[.045]*17,res=3,bev=8)
gy=surf_y(0,1.08).y
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=1,location=(0,gy-.06,1.06));g=C.active_object;g.name='gem';g.scale=(.07,.04,.1);apply_all(g);feat['gem']=g
# paw beans (front of front paws)
for s,n in ((-1,'L'),(1,'R')):
    x0=s*.32;objs=[]
    for dx,dz,r in ((0,.13,(.075,.03,.055)),(-.1,.22,(.032,.025,.032)),(0,.25,(.032,.025,.032)),(.1,.22,(.032,.025,.032))):
        p=surf_y(x0+dx,dz);objs.append(ell('bean',(p.x,p.y+.012,p.z),r,seg=12,ring=6))
    feat['beans'+n]=join(objs,'beans'+n)
# tail wisps (glowing orbs near tip)
wisps=[]
for (x,y,z,r) in ((1.62,.18,1.55,.06),(1.7,.15,1.78,.045),(1.55,.12,1.95,.035),(1.78,.2,1.35,.03)):
    wisps.append(ell('wisp',(x,y,z),(r,r,r),seg=12,ring=6))
feat['wisps']=join(wisps,'wisps')
# =================================================================== wings (membrane, scalloped)
WING2D=[(0,0),(.08,.3),(.3,.62),(.62,.8),(.98,.9),(.86,.72),(.84,.66),(1.02,.5),(.8,.44),(.74,.4),(.82,.16),(.6,.2),(.54,.16),(.52,-.08),(.34,.02),(.28,0),(.06,-.12)]
def wing(s,n):
    bm=bmesh.new();vs=[bm.verts.new((u,0,v)) for u,v in WING2D];f=bm.faces.new(vs)
    bmesh.ops.triangulate(bm,faces=[f])
    bmesh.ops.subdivide_edges(bm,edges=bm.edges[:],cuts=4,use_grid_fill=True)
    bmesh.ops.triangulate(bm,faces=bm.faces[:])
    me=D.meshes.new('wing'+n);bm.to_mesh(me);bm.free()
    o=D.objects.new('wing'+n,me);C.collection.objects.link(o)
    uv=me.uv_layers.new(name='UVMap')
    for poly in me.polygons:
        for li in poly.loop_indices:
            v=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(v.x/1.05,(v.z+.12)/1.0)
    active(o);sm=o.modifiers.new('sol','SOLIDIFY');sm.thickness=.035;sm.offset=0
    bpy.ops.object.modifier_apply(modifier='sol')
    # bend: arc the membrane back + mirror for left; scale & place at shoulder
    for v in me.vertices:
        u=v.co.x;v.co.y+=.35*u*u
    ribs=[]
    for (eu,ev),r0 in (((.98,.9),.045),((1.02,.5),.03),((.82,.16),.026),((.52,-.08),.022)):
        pts=[];rad=[]
        for k in range(5):
            t=k/4;u=eu*t;v=ev*t+(.06*math.sin(t*math.pi) if ev>.6 else 0)
            pts.append((u,.35*u*u-.012,v));rad.append(r0*(1-.65*t))
        ribs.append(tube('rib',pts,rad,res=4,bev=8))
    rb=join(ribs,'ribs'+n)
    for x in (o,rb):
        x.scale=(1.5,1.5,1.4);x.rotation_euler=(0,math.radians(14),math.radians(-30));x.location=(.36,.34,.8)
        apply_all(x)
        if s<0:
            for v in x.data.vertices:v.co.x=-v.co.x
            x.data.flip_normals()
    feat['ribs'+n]=rb
    return o
feat['wingL']=wing(-1,'L');feat['wingR']=wing(1,'R')
# =================================================================== labels (nearest pre-fusion part)
def label_of(co):
    best=None;bd=1e9
    for k,t in part_bvh.items():
        hit=t.find_nearest(co)
        if hit[0] is not None and hit[3]<bd:bd=hit[3];best=k
    return best
fur_labels=[label_of(v.co) for v in fur.data.vertices]
# =================================================================== vertex colours (fur gradient, inner ears, bib, tail tip)
def mix(a,b,t):return tuple(a[i]+(b[i]-a[i])*t for i in range(4))
FUR0,FUR1,FUR2=hx('#07040d'),hx('#150e24'),hx('#30214f')
EARA,EARB=hx('#d6b4ff'),hx('#7a46d8');BIB=hx('#33244f');TAILT=hx('#6b3fd0');LASH=hx('#c7a2ff');LID=hx('#21163a')
key=Vector((-.35,-.7,.62)).normalized()
def ear_inner(co,n,s):
    b=Vector((s*.66,.04,2.36));t=Vector((s*.9,.06,3.26));ax=(t-b);L=ax.length;ax.normalize()
    tt=(co-b).dot(ax)/L
    if tt<.04 or tt>.86:return None
    side=Vector((ax.z,0,-ax.x)).normalized()  # width direction in the ear plane
    R=.44*(1-tt)+.03*tt
    rx=abs((co-b).dot(side))
    if rx<.66*R and n.y<-.2:return tt
    return None
def colour_for(co,n,lab):
    f=max(0,min(1,.5+.5*n.dot(key)));f=f*f
    c=mix(FUR0,FUR1,min(1,f*1.6)) if f<.62 else mix(FUR1,FUR2,(f-.62)/.38)
    if co.z<.5:c=mix(c,FUR0,(.5-co.z)*.9)
    if lab and lab.startswith('ear'):
        s=-1 if lab.endswith('L') else 1;tt=ear_inner(co,n,s)
        if tt is not None:c=mix(EARA,EARB,min(1,tt*1.3))
    if lab in('neck','body') and n.y<-.4 and 1.0-.09*abs(math.sin(co.x*13))<co.z<1.24 and abs(co.x)<.42:c=mix(c,BIB,.85)
    if lab=='tail':
        t=max(0,min(1,(co.z-.6)/1.1));c=mix(c,TAILT,t*.75)
    return c
def vcol(o,fn):
    me=o.data;ca=me.color_attributes.new('Col','FLOAT_COLOR','CORNER')
    me.calc_normals_split() if hasattr(me,'calc_normals_split') else None
    for poly in me.polygons:
        for li in poly.loop_indices:
            vi=me.loops[li].vertex_index;ca.data[li].color=fn(vi,me.vertices[vi].co,me.vertices[vi].normal)
vcol(fur,lambda vi,co,n:colour_for(co,n,fur_labels[vi]))
import collections;print('LABELS',collections.Counter(fur_labels).most_common(30))
print('INNER',sum(1 for i,v in enumerate(fur.data.vertices) if fur_labels[i] and fur_labels[i].startswith('ear') and ear_inner(v.co,v.normal,-1 if fur_labels[i].endswith('L') else 1) is not None))
for o,kind,s,n in lid_meta:
    vcol(o,lambda vi,co,nn:LASH if vi%NS==NS-1 else LID)
# =================================================================== materials
def mat(name,base=(0,0,0,1),rough=.6,metal=0,emit=None,emit_str=0,tex=None,emit_tex=None,vc=False,sheen=0,coat=0,uvname='UVMap'):
    m=D.materials.new(name);m.use_nodes=True;nt=m.node_tree;b=nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value=base;b.inputs['Roughness'].default_value=rough;b.inputs['Metallic'].default_value=metal
    if sheen:b.inputs['Sheen Weight'].default_value=sheen;b.inputs['Sheen Tint'].default_value=hx('#b98aff')
    if coat:b.inputs['Coat Weight'].default_value=coat
    if vc:
        a=nt.nodes.new('ShaderNodeVertexColor');a.layer_name='Col';nt.links.new(a.outputs['Color'],b.inputs['Base Color'])
    if tex:
        t=nt.nodes.new('ShaderNodeTexImage');t.image=D.images.load(tex);nt.links.new(t.outputs['Color'],b.inputs['Base Color'])
    if emit_tex:
        t=nt.nodes.new('ShaderNodeTexImage');t.image=D.images.load(emit_tex);nt.links.new(t.outputs['Color'],b.inputs['Emission Color'])
        b.inputs['Emission Strength'].default_value=emit_str or 1
    elif emit:
        b.inputs['Emission Color'].default_value=emit;b.inputs['Emission Strength'].default_value=emit_str
    return m
T=HERE
MAT={
 'fur':mat('zeref_fur',vc=True,rough=.62,sheen=.35,emit_tex=T+'/fur_emit.png',emit_str=1.3),
 'eye':mat('zeref_eye',tex=T+'/eye_base.png',emit_tex=T+'/eye_emit.png',emit_str=1.8,rough=.08,coat=1.0),
 'wing':mat('zeref_wing',tex=T+'/wing_base.png',emit_tex=T+'/wing_emit.png',emit_str=.7,rough=.6,coat=0),
 'moon':mat('zeref_moon',base=hx('#e9dcff'),rough=.25,coat=.8,emit=hx('#bfa0ff'),emit_str=1.4),
 'glow':mat('zeref_glow',base=hx('#b98aff'),rough=.3,emit=hx('#b98aff'),emit_str=2.5),
 'line':mat('zeref_line',base=hx('#d6b8ff'),rough=.4,emit=hx('#d6b8ff'),emit_str=.8),
 'brow':mat('zeref_brow',base=hx('#7a5bb5'),rough=.5,emit=hx('#7a5bb5'),emit_str=.5),
 'nose':mat('zeref_nose',base=hx('#7b4fc4'),rough=.4),
 'blush':mat('zeref_blush',base=hx('#5c2a4c'),rough=.65,emit=hx('#ff7fd6'),emit_str=.15),
 'choker':mat('zeref_choker',base=hx('#0a0612'),rough=.35,metal=.3),
 'gem':mat('zeref_gem',base=hx('#b57bff'),rough=.05,coat=1,emit=hx('#b57bff'),emit_str=2.2),
 'rib':mat('zeref_rib',base=hx('#140a28'),rough=.4,coat=.5),
 'wisp':mat('zeref_wisp',base=hx('#8fe8ff'),emit=hx('#8fe8ff'),emit_str=4),
}
def setmat(o,m):o.data.materials.clear();o.data.materials.append(m)
setmat(fur,MAT['fur'])
for o,*_ in lid_meta:setmat(o,MAT['fur'])
for n in 'LR':
    setmat(parts['eye'+n],MAT['eye']);setmat(feat['wing'+n],MAT['wing']);setmat(feat['ribs'+n],MAT['rib']);setmat(feat['horn'+n],MAT['moon'])
    setmat(feat['brow'+n],MAT['brow']);setmat(feat['blush'+n],MAT['blush']);setmat(feat['beans'+n],MAT['glow'])
setmat(feat['crescent'],MAT['moon']);setmat(feat['mouth'],MAT['line']);setmat(feat['nose'],MAT['nose'])
setmat(feat['choker'],MAT['choker']);setmat(feat['gem'],MAT['gem']);setmat(feat['wisps'],MAT['wisp'])
# fur UV (smart project) for the starfield
active(fur);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.004);bpy.ops.object.mode_set(mode='OBJECT')
for o,*_ in lid_meta:
    o.data.uv_layers.new(name='UVMap')
for o in list(feat.values())+[parts['eyeL'],parts['eyeR']]:
    if not o.data.uv_layers:o.data.uv_layers.new(name='UVMap')
# =================================================================== part tags as vertex groups, then join
def tag(o,name):
    g=o.vertex_groups.new(name=name);g.add(list(range(len(o.data.vertices))),1.0,'REPLACE')
tag(fur,'P_fur')
for o,kind,s,n in lid_meta:tag(o,'P_lid'+kind+n)
for k in ('eyeL','eyeR'):tag(parts[k],'P_'+k)
for k,o in feat.items():tag(o,'P_'+k)
all_objs=[fur]+[m[0] for m in lid_meta]+[parts['eyeL'],parts['eyeR']]+list(feat.values())
nfur=len(fur.data.vertices)
for o in all_objs: print('  part',o.name,sum(len(p.vertices)-2 for p in o.data.polygons))
zer=join(all_objs,'Zeref');zer.data.name='Zeref'
for p in zer.data.polygons:p.use_smooth=True
me=zer.data;V=me.vertices
def group_verts(name):
    gi=zer.vertex_groups[name].index;return [v.index for v in V if any(g.group==gi and g.weight>.5 for g in v.groups)]
# fur verts keep index order 0..nfur-1 after join (fur was active/first)
labels=fur_labels+[None]*(len(V)-nfur)

print('total tris',sum(len(p.vertices)-2 for p in me.polygons))
# =================================================================== shape keys
base=zer.shape_key_add(name='Basis',from_mix=False)
BASE=[v.co.copy() for v in V]
lididx={}
for o,kind,s,n in lid_meta:lididx[(kind,n)]=group_verts('P_lid'+kind+n)
def ear_rot(co,s,ang_x,ang_y,ang_z=0):
    b=Vector((s*.66,.04,2.36));t=Vector((s*.9,.06,3.26));L=(t-b).length;tt=max(0,min(1,(co-b).dot((t-b).normalized())/L))
    w=max(0,min(1,(tt-.02)/.3))
    R=Matrix.Rotation(ang_x*w,3,'X')@Matrix.Rotation(s*ang_y*w,3,'Y')@Matrix.Rotation(s*ang_z*w,3,'Z')
    return b+R@(co-b)
ear_set={n:[i for i in range(nfur) if labels[i]==('ear'+n)] for n in 'LR'}
# ear-adjacent head verts get partial ear motion handled by w (tt) — ears are fused so only ear-labelled verts move
def eye_scale(idx,cent,k,ky=None):
    out={}
    for i in idx:
        d=BASE[i]-cent;out[i]=cent+Vector((d.x*k,d.y*k,d.z*(ky or k)))
    return out
def brow_move(n,dz_inner,dz_outer,dz=0):
    s=-1 if n=='L' else 1;out={}
    for i in group_verts('P_brow'+n):
        co=BASE[i];t=max(0,min(1,(abs(co.x)-.26)/.36))  # 0 inner,1 outer
        out[i]=co+Vector((0,0,dz+dz_inner*(1-t)+dz_outer*t))
    return out
def mouth_move(widen=1.0,corner=0.0,lift=0.0):
    out={}
    for i in group_verts('P_mouth'):
        co=BASE[i];out[i]=Vector((co.x*widen,co.y,co.z+lift+corner*(abs(co.x)/.17)**2))
    return out
def make_key(name,state,ears=None,brows=None,eyes_k=None,mouth=None,extra=None):
    sk=zer.shape_key_add(name=name,from_mix=False)
    for (kind,n),idx in lididx.items():
        s=-1 if n=='L' else 1
        pts=lid_positions(kind,s,n,state if state else 'rest')
        if eyes_k:  # lids follow eye scaling
            c=Vector(eyes[n]);pts=[c+(p-c)*eyes_k for p in pts]
        for i,p in zip(idx,pts):sk.data[i].co=p
    if eyes_k:
        for n in 'LR':
            for i,p in eye_scale(group_verts('P_eye'+n),Vector(eyes[n]),eyes_k).items():sk.data[i].co=p
    if ears:
        for n in 'LR':
            s=-1 if n=='L' else 1
            for i in ear_set[n]:sk.data[i].co=ear_rot(BASE[i],s,*ears)
    if brows:
        for n in 'LR':
            for i,p in brow_move(n,*brows[n]).items():sk.data[i].co=p
    if mouth:
        for i,p in mouth_move(*mouth).items():sk.data[i].co=p
    return sk
make_key('blink','blink')
make_key('happy','happy',ears=(math.radians(-6),0,math.radians(-8)),brows={'L':(.04,.0),'R':(.04,.0)},mouth=(1.18,.05,.01))
make_key('scared',None,ears=(math.radians(28),math.radians(38),math.radians(-30)),brows={'L':(.1,.02,.04),'R':(.1,.02,.04)},eyes_k=1.12,mouth=(.8,-.03,-.02))
make_key('curious',None,ears=(math.radians(-14),math.radians(-6),math.radians(8)),brows={'L':(.02,.08,.05),'R':(0,0,0)},eyes_k=1.05,mouth=(.85,0,0))
make_key('sleepy','sleepy',ears=(math.radians(10),math.radians(10),math.radians(-38)),brows={'L':(-.03,-.02),'R':(-.03,-.02)},mouth=(.7,0,0))
make_key('angry','angry',ears=(math.radians(30),math.radians(20),math.radians(-12)),brows={'L':(-.11,.05),'R':(-.11,.05)},mouth=(.95,-.06,0))
# =================================================================== armature
arm=D.armatures.new('ZerefRig');rig=D.objects.new('ZerefRig',arm);C.collection.objects.link(rig)
active(rig);bpy.ops.object.mode_set(mode='EDIT')
EB=arm.edit_bones
def bone(name,h,t,parent=None):
    b=EB.new(name);b.head=h;b.tail=t
    if parent:b.parent=EB[parent];b.use_connect=(Vector(EB[parent].tail)-Vector(h)).length<1e-4
    return b
bone('root',(0,0,0),(0,0,.3));bone('spine',(0,0,.3),(0,0,1.0),'root');bone('chest',(0,0,1.0),(0,0,1.32),'spine')
bone('head',(0,0,1.32),(0,0,2.7),'chest')
for s,n in ((-1,'L'),(1,'R')):
    bone('ear.0.'+n,(s*.66,.04,2.36),(s*.78,.05,2.81),'head');bone('ear.1.'+n,(s*.78,.05,2.81),(s*.9,.06,3.26),'ear.0.'+n)
# tail chain along the curve control polygon
tp=[Vector(p) for p in TAIL];prev='spine'
for i in range(len(tp)-1):
    bone('tail.%d'%i,tp[i],tp[i+1],prev);prev='tail.%d'%i
# wings: shoulder -> elbow -> tip along leading edge (from wing mesh extremes)
WINGB={}
for s,n in ((-1,'L'),(1,'R')):
    pts=[Vector((s*.38,.34,.82)),Vector((s*.86,.62,1.15)),Vector((s*1.3,.95,1.45)),Vector((s*1.62,1.2,1.62))]
    prev='chest';WINGB[n]=[]
    for i in range(3):
        nm='wing.%d.%s'%(i,n);bone(nm,pts[i],pts[i+1],prev);prev=nm;WINGB[n].append(nm)
bpy.ops.object.mode_set(mode='OBJECT')
bones={b.name:(b.head_local.copy(),b.tail_local.copy()) for b in arm.bones}
def seg_d(p,a,b):
    ab=b-a;t=max(0,min(1,(p-a).dot(ab)/max(1e-9,ab.length_squared)));return (p-(a+ab*t)).length
def cands(i,co):
    lab=labels[i] if i<nfur else None
    gn=[zer.vertex_groups[g.group].name for g in V[i].groups if zer.vertex_groups[g.group].name.startswith('P_')]
    g=gn[0] if gn else 'P_fur'
    if g!='P_fur':
        if g.startswith('P_wing') or g.startswith('P_ribs'):return ['chest']+WINGB[g[-1]]
        if g in('P_wisps',):return ['tail.3','tail.4']
        if g in('P_beansL','P_beansR'):return ['spine','root']
        if g=='P_choker' or g=='P_gem':return ['chest']
        return ['head']
    if lab is None:return ['spine']
    if lab.startswith('ear'):return ['head','ear.0.'+lab[-1],'ear.1.'+lab[-1]]
    if lab in('head','jaw','muzzle') or lab.startswith('cheek') or lab.startswith('tuft'):return ['head']+(['chest'] if co.z<1.5 else [])
    if lab=='tail':return ['spine']+['tail.%d'%k for k in range(len(tp)-1)]
    if lab=='neck':return ['chest','head','spine']
    return ['root','spine','chest']
rig_groups={b:zer.vertex_groups.new(name=b) for b in bones}
for v in V:
    cs=cands(v.index,v.co);ws=[]
    for b in cs:
        d=seg_d(v.co,*bones[b]);ws.append((1/((d+.02)**4),b))
    ws.sort(reverse=True);ws=ws[:3];tot=sum(w for w,_ in ws)
    for w,b in ws:rig_groups[b].add([v.index],w/tot,'REPLACE')
# remove P_ tag groups (keep data clean for export)
for g in list(zer.vertex_groups):
    if g.name.startswith('P_'):zer.vertex_groups.remove(g)
zer.parent=rig;mod=zer.modifiers.new('rig','ARMATURE');mod.object=rig
# scale the whole creature (vector units -> ~1.45 m tall chibi -> normalise to 1.4 world units)
S=.42;rig.scale=(S,S,S)
active(rig);rig.select_set(True);zer.select_set(True)
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
for p in zer.data.polygons:p.use_smooth=True
print('verts',len(zer.data.vertices),'tris',sum(len(p.vertices)-2 for p in zer.data.polygons))
bpy.ops.wm.save_as_mainfile(filepath=HERE+'/zeref.blend')
active(rig);zer.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT,export_format='GLB',use_selection=True,export_skins=True,export_morph=True,
  export_morph_normal=False,export_animations=False,export_yup=True,export_apply=False,export_attributes=True,export_vertex_color='ACTIVE' if bpy.app.version>=(4,2,0) else None) if False else \
bpy.ops.export_scene.gltf(filepath=OUT,export_format='GLB',use_selection=True,export_skins=True,export_morph=True,export_morph_normal=False,export_animations=False,export_yup=True,export_vertex_color='ACTIVE')
print('EXPORTED',OUT,os.path.getsize(OUT))
