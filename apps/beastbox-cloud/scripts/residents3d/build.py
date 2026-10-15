# Build a 3D "visual hull" resident from a 3-view turnaround frame (front | side | back).
# Silhouettes carve a voxel volume; marching cubes gives the mesh; the three views are projected back on.
import sys,json,struct,numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import measure
src,outdir,facing=sys.argv[1],sys.argv[2],sys.argv[3]   # facing: side view faces 'right' or 'left'
im=np.asarray(Image.open(src).convert('RGB')).astype(np.float32);Hh,W,_=im.shape
def mat(sub):
  h,w,_=sub.shape
  # background model: smooth gradient from the border, then distance from it
  border=np.concatenate([sub[:6].reshape(-1,3),sub[-6:].reshape(-1,3),sub[:,:6].reshape(-1,3),sub[:,-6:].reshape(-1,3)])
  bg=np.median(border,axis=0)
  rows=np.median(np.concatenate([sub[:, :8],sub[:,-8:]],axis=1),axis=1)  # per-row bg (vertical gradient)
  d=np.abs(sub-rows[:,None,:]).sum(-1)
  m=d>22
  m=ndi.binary_closing(m,iterations=3);m=ndi.binary_fill_holes(m);m=ndi.binary_opening(m,iterations=2)
  lab,n=ndi.label(m);sizes=ndi.sum(m,lab,range(1,n+1));k=1+int(np.argmax(sizes));m=lab==k
  m=ndi.binary_fill_holes(m)
  return m
views={}
for i,name in enumerate(['front','side','back']):
  x0,x1=int(W*i/3),int(W*(i+1)/3);sub=im[:,x0:x1];m=mat(sub)
  ys,xs=np.nonzero(m);by0,by1,bx0,bx1=ys.min(),ys.max(),xs.min(),xs.max()
  views[name]=dict(sub=sub,m=m,by0=by0,by1=by1,bx0=bx0,bx1=bx1)
H=float(max(v['by1']-v['by0'] for v in views.values()))
def sampler(v,flipx=False):
  m=v['m'];cx=(v['bx0']+v['bx1'])/2;foot=v['by1']
  def f(U,Y):  # U horizontal in units of H (centered), Y in [0,1] from feet up
    px=cx+(-U if flipx else U)*H;py=foot-Y*H
    xi=np.clip(np.round(px).astype(int),0,m.shape[1]-1);yi=np.clip(np.round(py).astype(int),0,m.shape[0]-1)
    ok=(px>=0)&(px<m.shape[1])&(py>=0)&(py<m.shape[0])
    return m[yi,xi]&ok
  return f,cx,foot
fS,_,_=sampler(views['front']);bS,_,_=sampler(views['back'],flipx=True)
sideflip=(facing=='left')
sS,_,_=sampler(views['side'],flipx=sideflip)
NX,NY,NZ=120,128,150
X=np.linspace(-.62,.62,NX);Y=np.linspace(-.02,1.04,NY);Z=np.linspace(-.85,.85,NZ)
XX,YY,ZZ=np.meshgrid(X,Y,Z,indexing='ij')
vol=(fS(XX,YY)&bS(XX,YY)&sS(ZZ,YY)).astype(np.float32)
vol=ndi.gaussian_filter(vol,1.2)
verts,faces,normals,_=measure.marching_cubes(vol,level=.5,step_size=2)
sx=(X[-1]-X[0])/(NX-1);sy=(Y[-1]-Y[0])/(NY-1);sz=(Z[-1]-Z[0])/(NZ-1)
P=np.stack([X[0]+verts[:,0]*sx,Y[0]+verts[:,1]*sy,Z[0]+verts[:,2]*sz],1).astype(np.float32)
N=-normals.astype(np.float32);N/=np.linalg.norm(N,axis=1,keepdims=True)+1e-6
# orient normals outward: compare with centroid direction
c=P.mean(0);flip=((P-c)*N).sum(1).mean()<0
if flip:N=-N
faces=faces.astype(np.uint16 if len(P)<65535 else np.uint32)
import os;os.makedirs(outdir,exist_ok=True)
with open(outdir+'/mesh.bin','wb') as fo:fo.write(P.tobytes());fo.write(N.tobytes());fo.write(faces.tobytes())
meta={'vertices':int(len(P)),'triangles':int(len(faces)),'index':'u16' if faces.dtype==np.uint16 else 'u32','views':{}}
for name,v in views.items():
  sub=v['sub'];m=v['m'];x0,x1,y0,y1=v['bx0'],v['bx1']+1,v['by0'],v['by1']+1
  rgba=np.dstack([sub[y0:y1,x0:x1],ndi.gaussian_filter(m[y0:y1,x0:x1].astype(np.float32),.8)[...,None]*255]).clip(0,255).astype(np.uint8)
  img=Image.fromarray(rgba,'RGBA');s=512/img.height;img=img.resize((max(1,int(img.width*s)),512),Image.LANCZOS);img.save(outdir+f'/{name}.png',optimize=True)
  cx=(v['bx0']+v['bx1'])/2
  u0=(x0-cx)/H;u1=(x1-cx)/H;vv0=(v['by1']-(y1-1))/H;vv1=(v['by1']-y0)/H
  meta['views'][name]={'u0':round(u0,4),'u1':round(u1,4),'v0':round(vv0,4),'v1':round(vv1,4),'flip':bool(name=='back' or (name=='side' and sideflip))}
meta['source']='Cory-provided AI turntable video (artist-drawn resident, no quantum seed); visual hull from front/side/back silhouettes'
json.dump(meta,open(outdir+'/meta.json','w'),indent=1)
print(json.dumps({k:meta[k] for k in ('vertices','triangles','index')}),os.path.getsize(outdir+'/mesh.bin'))
