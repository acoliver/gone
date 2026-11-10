from PIL import Image,ImageOps,ImageDraw
from pathlib import Path
root=Path('/Volumes/XS1000/acoliver/projects/gone/branch-3'); out=root/'tmp/issue91/console2/kbfinish'; kb=root/'tmp/issue91/kbmodel'
items=[('Photo',root/'tmp/issue91/console2/outputs/keyboard-s520.png'),('Generated keyboard',out/'top.png'),('Design top view',kb/'render-top.png')]
w,h=900,540; canvas=Image.new('RGB',(w*3,h+50),(238,238,232)); d=ImageDraw.Draw(canvas)
for i,(title,path) in enumerate(items):
 im=Image.open(path).convert('RGB'); im.thumbnail((w-24,h-20)); x=i*w+(w-im.width)//2;y=50+(h-im.height)//2;canvas.paste(im,(x,y));d.text((i*w+18,15),title,fill=(25,25,25))
canvas.save(out/'contact.png')
