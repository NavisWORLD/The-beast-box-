# Procedural textures for Zeref, painted to match the ZerefFigure vector palette (lib/zeref/rig-style.mjs ZEREF_SKIN).
from PIL import Image, ImageDraw, ImageFilter
import numpy as np, math, random, sys
out=sys.argv[1]
def hx(h):h=h.lstrip('#');return tuple(int(h[i:i+2],16) for i in (0,2,4))
def lerp(a,b,t):return tuple(int(a[i]+(b[i]-a[i])*t) for i in range(3))
def grad(stops,t):
    t=max(0,min(1,t))
    for i in range(len(stops)-1):
        p0,c0=stops[i];p1,c1=stops[i+1]
        if t<=p1:return lerp(c0,c1,(t-p0)/max(1e-6,p1-p0))
    return stops[-1][1]
def star(d,x,y,r,fill):
    pts=[]
    for k in range(16):
        a=k*math.pi/8; rr=r if k%4==0 else (r*.2 if k%2 else r*.32)
        pts.append((x+rr*math.sin(a),y-rr*math.cos(a)))
    d.polygon(pts,fill=fill)
# ---- eye (front planar UV, square = eye ellipse bbox)
N=1024;im=Image.new('RGB',(N,N),hx('#05030b'));px=im.load()
iris=[(0,hx('#f0e2ff')),(.25,hx('#c69bff')),(.6,hx('#7b3cf0')),(1,hx('#2a0d5e'))]
c=N/2
for y in range(N):
    for x in range(N):
        dx=(x-c)/(N*.5);dy=(y-c)/(N*.5);r=math.hypot(dx,dy)
        if r<.94:
            ir=math.hypot((x-N*.45)/(N*.75*.94),(y-N*.38)/(N*.75*.94))
            px[x,y]=grad(iris,ir*1.25)
        elif r<.985: px[x,y]=hx('#2a1b45')
d=ImageDraw.Draw(im)
d.ellipse([c-N*.17,c-N*.17+N*.05,c+N*.17,c+N*.24+N*.05],fill=hx('#1a0638'))
d.ellipse([c-N*.06,c-N*.01,c+N*.14,c+N*.2],fill=lerp(hx('#1a0638'),hx('#c9a6ff'),.45))
d.ellipse([c-N*.02,c-N*.01,c+N*.16,c+N*.17],fill=hx('#1a0638'))
star(d,c-N*.15,c-N*.19,N*.13,(255,255,255))
d.ellipse([c+N*.11,c+N*.13,c+N*.22,c+N*.24],fill=(255,255,255))
d.ellipse([c+N*.18,c-N*.1,c+N*.23,c-N*.05],fill=hx('#e9dcff'))
im=im.filter(ImageFilter.GaussianBlur(1.2));im.save(out+'/eye_base.png')
# eye emissive: iris glow + highlights
e=np.asarray(im).astype(float);lum=e.mean(2,keepdims=True)/255
em=(e*np.clip((lum-.35)*1.6,0,1)).astype(np.uint8);Image.fromarray(em).save(out+'/eye_emit.png')
# ---- wing (planar UV over the outline bbox; u outward, v up)
N=1024;w=Image.new('RGB',(N,N));wp=w.load()
ws=[(0,hx('#1e0d48')),(.4,hx('#3c1d78')),(.8,hx('#8a4ff0')),(1,hx('#9c86ff'))]
for y in range(N):
    for x in range(N):
        u=x/N;v=1-y/N;t=(u*.65+v*.55)/1.05
        wp[x,y]=grad(ws,t)
wd=ImageDraw.Draw(w)
for (a,b) in [((0,1),(1,.0)),((.08,1),(.86,.45)),((.25,1),(.66,.85))]:
    pass
random.seed(7)
em=Image.new('RGB',(N,N),(0,0,0));ed=ImageDraw.Draw(em)
for i in range(60):
    x=random.random()*N;y=random.random()*N;r=random.choice([2,3,3,4,6])
    col=random.choice([hx('#f3e9ff'),hx('#d8c2ff'),(255,255,255)])
    if r>=4: star(wd,x,y,r*3.2,col);star(ed,x,y,r*3.2,col)
    else: wd.ellipse([x-r,y-r,x+r,y+r],fill=col);ed.ellipse([x-r,y-r,x+r,y+r],fill=col)
# cyan glow toward tip (upper right)
ea=np.asarray(em).astype(float)
yy,xx=np.mgrid[0:N,0:N];tip=np.clip(((xx/N)*.65+(1-yy/N)*.55-.75)/.3,0,1)[...,None]
ea=ea+tip*np.array(hx('#8fe8ff'))*.15
Image.fromarray(np.clip(ea,0,255).astype(np.uint8)).save(out+'/wing_emit.png')
w.save(out+'/wing_base.png')
# ---- fur cosmic emissive: tileable starfield + faint nebula (smart-UV mapped)
N=1024;rng=np.random.default_rng(11)
neb=np.zeros((N,N));
for k in range(6):
    fx,fy,ph=rng.integers(1,5),rng.integers(1,5),rng.random()*6.28
    neb+=np.sin(2*np.pi*(fx*xx[:N,:N]/N+ph))*np.sin(2*np.pi*(fy*yy[:N,:N]/N+ph*.7))
neb=np.clip((neb/6+.15),0,1)**2
img=np.zeros((N,N,3));img+=neb[...,None]*np.array(hx('#4a2a9a'))*.35
im=Image.fromarray(np.clip(img,0,255).astype(np.uint8));d=ImageDraw.Draw(im)
for i in range(380):
    x=rng.random()*N;y=rng.random()*N;r=rng.choice([.8,1,1,1.4,1.8])
    col=tuple(int(v) for v in rng.choice([hx('#c9a6ff'),hx('#e6d6ff'),(255,255,255),hx('#8fe8ff')]))
    for ox in (-N,0,N):
        for oy in (-N,0,N):
            d.ellipse([x+ox-r,y+oy-r,x+ox+r,y+oy+r],fill=col)
for i in range(8):
    x=rng.random()*N;y=rng.random()*N;star(d,x,y,rng.choice([5,7,9]),(240,230,255))
im.save(out+'/fur_emit.png')
print('textures ok')
