"""CST fields -> texture maps. python3 cst_textures_png.py <fielddir> <texdir> [prefix]"""
import sys,json,math,numpy as np
from PIL import Image,ImageDraw,ImageFilter
fd,td=sys.argv[1],sys.argv[2];pre=sys.argv[3] if len(sys.argv)>3 else 'cst'
N=512
L=np.array(Image.open(f'{fd}/lorenz_density.pgm'))/255.
Lb=np.array(Image.fromarray((L*255).astype('uint8')).filter(ImageFilter.GaussianBlur(3)))/255.
coh=np.array(Image.open(f'{fd}/coherence.pgm').resize((N,N),Image.BICUBIC))/255.
cha=np.array(Image.open(f'{fd}/chaos.pgm').resize((N,N),Image.BICUBIC))/255.
def nmap(h,s,name):
    gy,gx=np.gradient(h);n=np.dstack((-gx*s,-gy*s,np.ones_like(h)));n/=np.linalg.norm(n,axis=2,keepdims=True)
    Image.fromarray(((n*.5+.5)*255).astype('uint8')).save(f'{td}/{pre}_{name}.png')
def g(a,r):return np.array(Image.fromarray((np.clip(a,0,1)*255).astype('uint8')).filter(ImageFilter.GaussianBlur(r)))/255.
# fur: clump = blurred Lorenz density, flyaway = sharp trail residue, flow = Lorenz direction
Image.fromarray((g(Lb/Lb.max(),2)*255).astype('uint8')).save(f'{td}/{pre}_fur_clump.png')
fly=np.clip((L-g(L,4))*4,0,1);Image.fromarray((fly*255).astype('uint8')).save(f'{td}/{pre}_fur_flyaway.png')
Image.open(f'{fd}/lorenz_flow.ppm').filter(ImageFilter.GaussianBlur(2)).save(f'{td}/{pre}_fur_flow.png')
# puffer quilting: 3x4 pillowed panels whose loft varies with the coherence field; micro wrinkles from chaos x Lorenz
y,x=np.mgrid[0:N,0:N]/N;u=(x*4)%1;v=(y*3)%1
pillow=np.sin(u*math.pi)**.6*np.sin(v*math.pi)**.6
loft=pillow*(.6+.8*coh)+.08*cha*g(L,1)
nmap(loft,18,'puffer_normal')
Image.fromarray(((.55+.35*(1-pillow)+.1*cha)*255).clip(0,255).astype('uint8')).save(f'{td}/{pre}_puffer_rough.png')
# knit ribs whose stitch height wobbles with coherence (no two ribs alike)
ku=(x*16)%1;kv=(y*24+coh*1.5)%1;side=np.where(ku<.5,ku*2,(1-ku)*2)
st=np.clip(1-((kv-side*.5-.25)**2)*12,0,1)*(.7+.6*coh)
nmap(g(st,1),30,'knit_normal')
# galaxy eyes: deep violet radial base, Lorenz-trail nebula wisps, Hebbian-clustered stars, dark rim
r=np.sqrt((x-.5)**2+(y-.5)**2)*2
base=np.dstack([20+60*(1-r),4+14*(1-r),60+120*(1-r)])
neb=g(L,1.5);neb=neb/neb.max()
img=base+np.dstack([150*neb,40*neb,200*neb])*(1-r)[...,None]
img[r>.86]=np.array([8,2,18]);img[(r>.8)&(r<=.86)]=np.array([40,10,90])
im=Image.fromarray(np.clip(img,0,255).astype('uint8'));d=ImageDraw.Draw(im)
for p in json.load(open(f'{fd}/hebb_stars.json')):
    cx,cy=p['x']*N,p['y']*N
    if math.hypot(cx/N-.5,cy/N-.5)*2>.78:continue
    s=1+p['w']*2.2
    if p['w']>1.15:d.line((cx-s*3,cy,cx+s*3,cy),fill=(255,255,255),width=2);d.line((cx,cy-s*3,cx,cy+s*3),fill=(255,255,255),width=2)
    d.ellipse((cx-s*.6,cy-s*.6,cx+s*.6,cy+s*.6),fill=(255,250,255))
d.ellipse((N*.27,N*.2,N*.4,N*.33),fill=(255,255,255))
im.save(f'{td}/{pre}_eye.png');print('maps ok')
