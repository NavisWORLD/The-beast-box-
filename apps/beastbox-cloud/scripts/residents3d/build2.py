# Resident 3D v2: multi-frame rembg mattes -> rounded visual hull -> Taubin-smoothed mesh -> seam-blended views.
# Input: Cory's turntable video (3-view sheet: front | side | back, each panel animating). Local + free (rembg/u2net on CPU).
import sys,os,json,subprocess,tempfile,numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import measure
from rembg import remove,new_session
video,outdir,facing=sys.argv[1],sys.argv[2],sys.argv[3]
TS=[round(.1*i,1) for i in range(12)]          # 12 frames over the first 1.1 s
tmp=tempfile.mkdtemp();frames=[]
for t in TS:
  p=f'{tmp}/f{t}.png';subprocess.run(['ffmpeg','-loglevel','error','-y','-ss',str(t),'-i',video,'-frames:v','1',p],check=True)
  frames.append(np.asarray(Image.open(p).convert('RGB')))
Hh,W,_=frames[0].shape;sessions=[new_session('isnet-general-use'),new_session('u2net')]
# two local models, max-combined: isnet keeps fine ears/horns, u2net keeps dark obsidian bodies isnet drops
def alpha(sub,back=False):
  # isnet is the clean matte (ears, horns, tail). u2net only helps the back view, where isnet drops a
  # dark obsidian body; it is limited to rows above isnet's feet (u2net keeps the floor reflection).
  a=np.asarray(remove(Image.fromarray(sub),session=sessions[0],only_mask=True)).astype(np.float32)/255
  if not back:return a
  b=np.asarray(remove(Image.fromarray(sub),session=sessions[1],only_mask=True)).astype(np.float32)/255
  r=np.nonzero((a>.5).sum(1)>3)[0]
  if len(r):b[r.max()+3:]=0
  return np.maximum(a,b)
def clean(m,open_r):
  m=ndi.binary_closing(m,structure=np.ones((7,7)));m=ndi.binary_opening(m,structure=np.ones((open_r,open_r)));lab,n=ndi.label(m)
  if n==0:return m
  # keep every sizeable piece (a dark body under a hat can matte as a separate blob), drop specks
  s=ndi.sum(m,lab,range(1,n+1));return ndi.binary_fill_holes(np.isin(lab,1+np.nonzero(s>=.08*s.max())[0]))
views={};log={}
for i,name in enumerate(['front','side','back']):
  x0,x1=int(W*i/3),int(W*(i+1)/3)
  A=[alpha(f[:,x0:x1],name=='back') for f in frames]
  ref=A[0]>.5
  # consensus over the frames whose silhouette still matches the t=0 pose (the panels drift/rotate later)
  keep=[a for a in A if ((a>.5)&ref).sum()/max(1,((a>.5)|ref).sum())>.86]
  cons=np.median(np.stack(keep),0);log[name]=len(keep)
  sub0=frames[0][:,x0:x1].astype(np.float32);rows=np.median(np.concatenate([sub0[:,:8],sub0[:,-8:]],1),1)
  diff=ndi.binary_fill_holes(ndi.binary_closing(np.abs(sub0-rows[:,None,:]).sum(-1)>22,iterations=3))
  ya=np.nonzero((cons>.5).any(1))[0];yd=np.nonzero(diff.any(1))[0]
  if len(yd) and (len(ya)==0 or (ya.max()-ya.min())<.8*(yd.max()-yd.min())):
    cons=np.maximum(cons,ndi.binary_opening(diff,iterations=2).astype(np.float32)*.9);log[name]=f'{len(keep)}+diff'
  tex_m=clean(cons>.5,3)                 # texture matte: keeps ears/horns/tail
  shape_m=clean(cons>.55,9)              # shape matte: thin glow wisps opened away
  ys,xs=np.nonzero(tex_m)
  views[name]=dict(sub=frames[0][:,x0:x1].astype(np.float32),a=cons,m=tex_m,s=shape_m,by0=ys.min(),by1=ys.max(),bx0=xs.min(),bx1=xs.max())
H=float(max(v['by1']-v['by0'] for v in views.values()))
def runs(m):
  # per pixel: centre & half-width of the horizontal run it belongs to
  C=np.zeros(m.shape,np.float32);R=np.zeros(m.shape,np.float32)
  for y in range(m.shape[0]):
    r=m[y];d=np.diff(np.r_[0,r.astype(np.int8),0]);st=np.nonzero(d==1)[0];en=np.nonzero(d==-1)[0]
    for a,b in zip(st,en):C[y,a:b]=(a+b-1)/2;R[y,a:b]=max(1,(b-a)/2)
  return C,R
def sampler(v,flipx=False):
  m=v['s'];C,R=runs(m);cx=(v['bx0']+v['bx1'])/2;foot=v['by1']
  def f(U,Y):
    px=cx+(-U if flipx else U)*H;py=foot-Y*H
    xi=np.clip(np.round(px).astype(int),0,m.shape[1]-1);yi=np.clip(np.round(py).astype(int),0,m.shape[0]-1)
    ok=(px>=0)&(px<m.shape[1])&(py>=0)&(py<m.shape[0])&m[yi,xi]
    t=(px-C[yi,xi])/R[yi,xi];t=np.where(flipx,-t,t) if False else t
    return ok,np.abs(t)
  return f
sf=facing=='left'
fF=sampler(views['front']);fB=sampler(views['back'],True);fS=sampler(views['side'],sf)
NX,NY,NZ=96,112,128
X=np.linspace(-.62,.62,NX);Y=np.linspace(-.02,1.04,NY);Z=np.linspace(-.85,.85,NZ)
XX,YY,ZZ=np.meshgrid(X,Y,Z,indexing='ij')
okF,tF=fF(XX,YY);okB,_=fB(XX,YY);okS,tS=fS(ZZ,YY)
# rounded hull: each front-run x side-run cross-section is a superellipse, not a box
P_=2.4;# back silhouette is unioned with the mirrored front so a neck gap in the back matte cannot cut the head off
inside=okF&(okB|okF)&okS&((tF**P_+tS**P_)<=1.0)
vol=ndi.gaussian_filter(inside.astype(np.float32),1.0)
verts,faces,_,_=measure.marching_cubes(vol,level=.5,step_size=1)
sx=(X[-1]-X[0])/(NX-1);sy=(Y[-1]-Y[0])/(NY-1);sz=(Z[-1]-Z[0])/(NZ-1)
P=np.stack([X[0]+verts[:,0]*sx,Y[0]+verts[:,1]*sy,Z[0]+verts[:,2]*sz],1)
# keep the largest connected piece of the mesh
import scipy.sparse as sp,scipy.sparse.csgraph as cg
n=len(P);e=np.r_[faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]
Adj=sp.coo_matrix((np.ones(len(e)),(e[:,0],e[:,1])),shape=(n,n)).tocsr();Adj=((Adj+Adj.T)>0).astype(np.float32)
nc,lab=cg.connected_components(Adj);big=np.argmax(np.bincount(lab));keepv=lab==big
remap=-np.ones(n,int);remap[keepv]=np.arange(keepv.sum());faces=remap[faces];faces=faces[(faces>=0).all(1)];P=P[keepv];Adj=Adj[keepv][:,keepv]
# Taubin smoothing (shrink-free)
deg=np.asarray(Adj.sum(1)).ravel()+1e-9;L=sp.diags(1/deg)@Adj
for _ in range(14):
  P=P+.5*(L@P-P);P=P-.53*(L@P-P)
# vertex normals from faces (outward, matching the v1 orientation convention)
fn=np.cross(P[faces[:,1]]-P[faces[:,0]],P[faces[:,2]]-P[faces[:,0]]);N=np.zeros_like(P)
for k in range(3):np.add.at(N,faces[:,k],fn)
N/=np.linalg.norm(N,axis=1,keepdims=True)+1e-9
c=P.mean(0)
if ((P-c)*N).sum(1).mean()<0:N=-N
P=P.astype(np.float32);N=N.astype(np.float32);faces=faces.astype(np.uint16 if len(P)<65535 else np.uint32)
os.makedirs(outdir,exist_ok=True)
with open(outdir+'/mesh.bin','wb') as fo:fo.write(P.tobytes());fo.write(N.tobytes());fo.write(faces.tobytes())
meta={'vertices':int(len(P)),'triangles':int(len(faces)),'index':'u16' if faces.dtype==np.uint16 else 'u32','views':{}}
for name,v in views.items():
  sub=v['sub'];m=v['m'];pad=8
  x0,x1,y0,y1=max(0,v['bx0']-pad),min(m.shape[1],v['bx1']+1+pad),max(0,v['by0']-pad),v['by1']+1
  rgb=sub[y0:y1,x0:x1].copy();mm=m[y0:y1,x0:x1]
  # bleed edge colour outward so view blending never pulls in the dark backdrop
  _,(iy,ix)=ndi.distance_transform_edt(~mm,return_indices=True);rgb=rgb[iy,ix]
  a=ndi.gaussian_filter(mm.astype(np.float32),1.0)
  img=Image.fromarray(np.dstack([rgb,a[...,None]*255]).clip(0,255).astype(np.uint8),'RGBA')
  s=768/img.height;img=img.resize((max(1,int(img.width*s)),768),Image.LANCZOS);img.save(outdir+f'/{name}.png',optimize=True)
  cx=(v['bx0']+v['bx1'])/2
  meta['views'][name]={'u0':round((x0-cx)/H,4),'u1':round((x1-cx)/H,4),'v0':round((v['by1']-(y1-1))/H,4),'v1':round((v['by1']-y0)/H,4),'flip':bool(name=='back' or (name=='side' and sf))}
meta['frames']={'used_times_s':TS,'consensus_frames_per_view':log,'matte':'rembg isnet-general-use + u2net max (local CPU) + temporal median'}
meta['source']='Cory-provided AI turntable video (artist-drawn resident, no quantum seed); rounded visual hull from multi-frame front/side/back mattes'
json.dump(meta,open(outdir+'/meta.json','w'),indent=1)
print(json.dumps({k:meta[k] for k in ('vertices','triangles','index','frames')}),os.path.getsize(outdir+'/mesh.bin'))
