"""PIL textures for the turnaround residents: galaxy/lavender eyes, knit + fabric normal/albedo maps. python3 turnaround_textures.py"""
import numpy as np,random,math,os
from PIL import Image,ImageDraw,ImageFilter
O=os.path.join(os.path.dirname(os.path.abspath(__file__)),'tex');os.makedirs(O,exist_ok=True)
N=512
def eye(name,c_out,c_in,stars,seed):
    R=random.Random(seed);y,x=np.mgrid[0:N,0:N]/N-.5;r=np.sqrt(x*x+y*y)*2
    t=np.clip(r,0,1)[...,None];img=np.array(c_in)[None,None]*(1-t)+np.array(c_out)*t
    img*=np.clip(1.25-r*.5,0,1)[...,None]
    neb=np.random.RandomState(seed).rand(32,32);neb=np.array(Image.fromarray((neb*255).astype('uint8')).resize((N,N),Image.BICUBIC))/255
    img=img*(.75+.5*neb[...,None]);img[r>.97]=np.array(c_out)*.25
    im=Image.fromarray(np.clip(img,0,255).astype('uint8'));d=ImageDraw.Draw(im)
    for k in range(stars):
        cx,cy=R.uniform(.15,.85)*N,R.uniform(.15,.85)*N;s=R.choice((1,1,2,2,3,6,9));a=R.randint(180,255)
        if s>4:d.line((cx-s,cy,cx+s,cy),fill=(255,255,255),width=2);d.line((cx,cy-s,cx,cy+s),fill=(255,255,255),width=2)
        d.ellipse((cx-s*.4,cy-s*.4,cx+s*.4+1,cy+s*.4+1),fill=(a,a,255))
    # big catchlights
    d.ellipse((N*.25,N*.18,N*.42,N*.35),fill=(255,255,255));d.ellipse((N*.6,N*.62,N*.68,N*.7),fill=(240,235,255))
    im.save(f'{O}/{name}.png')
eye('eye_galaxy',(40,10,90),(190,90,255),90,3)
eye('eye_lavender',(70,50,140),(225,205,255),6,5)
def nmap(h,strength,name):
    gy,gx=np.gradient(h);n=np.dstack((-gx*strength,-gy*strength,np.ones_like(h)));n/=np.linalg.norm(n,axis=2,keepdims=True)
    Image.fromarray(((n*.5+.5)*255).astype('uint8')).save(f'{O}/{name}.png')
y,x=np.mgrid[0:N,0:N]/N
# knit: columns of V stitches (8 columns, 16 rows per tile)
u=(x*8)%1;v=(y*16)%1;side=np.where(u<.5,u*2,(1-u)*2)
st=np.clip(1-((v-side*.5-.25)**2)*12,0,1)*np.sin(np.clip(side,0,1)*math.pi)**.5
h=st+.15*np.random.RandomState(1).rand(N,N);h=np.array(Image.fromarray((h/h.max()*255).astype('uint8')).filter(ImageFilter.GaussianBlur(1.2)))/255.
nmap(h,40,'knit_normal');Image.fromarray(((.55+.45*h)*255).astype('uint8')).convert('RGB').save(f'{O}/knit_ao.png')
# fabric: fine twill
tw=.5+.5*np.sin((x*90+y*90)*math.pi*2)*np.sin(y*180*math.pi);tw=tw+.2*np.random.RandomState(2).rand(N,N)
nmap(tw/tw.max(),6,'fabric_normal')
print('ok',os.listdir(O))
