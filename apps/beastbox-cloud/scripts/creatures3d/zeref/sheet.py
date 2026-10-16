import sys,glob
from PIL import Image,ImageFilter
d=sys.argv[1];fs=sorted(glob.glob(d+'/angle_*.png'));im=[Image.open(f).convert('RGB').filter(ImageFilter.MedianFilter(3)) for f in fs];W=im[0].width
s=Image.new('RGB',(W*4,W*2))
for i,x in enumerate(im):s.paste(x,((i%4)*W,(i//4)*W))
s.save(d+'/sheet.png')
