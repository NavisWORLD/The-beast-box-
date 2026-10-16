import sys
from PIL import Image
a=Image.open(sys.argv[1]).convert('RGB').resize((640,640));b=Image.open('/workspace/cosmo-study/zeref/vector-rig-front.png').convert('RGBA').resize((640,640))
bg=Image.new('RGBA',(640,640),(20,14,36,255));bg.alpha_composite(b)
s=Image.new('RGB',(1280,640));s.paste(bg.convert('RGB'),(0,0));s.paste(a,(640,0));s.save(sys.argv[2])
