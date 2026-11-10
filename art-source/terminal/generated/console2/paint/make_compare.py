from PIL import Image
from pathlib import Path
root=Path('art-source/terminal/generated/console2')
size=(400,225)
canvas=Image.new('RGB',(1600,450),(20,20,20))
def contain(path):
    image=Image.open(path).convert('RGB')
    image.thumbnail(size,Image.Resampling.LANCZOS)
    tile=Image.new('RGB',size,(20,20,20))
    tile.paste(image,((size[0]-image.width)//2,(size[1]-image.height)//2))
    return tile
inputs=[root/'inputs/console-s510-rgba.png',root/'paint/renders/front.png',root/'paint/renders/three-quarter.png',root/'paint/renders/side.png']
palette=Image.open(root/'fit/compare.png').convert('RGB')
row=palette.crop((0,palette.height//2,palette.width,palette.height))
for col,path in enumerate(inputs): canvas.paste(contain(path),(col*size[0],0))
for col in range(4):
    tile=row.crop((col*row.width//4,0,(col+1)*row.width//4,row.height))
    tile=tile.resize(size,Image.Resampling.LANCZOS)
    canvas.paste(tile,(col*size[0],size[1]))
canvas.save(root/'paint/compare.png')
print('wrote paint/compare.png',canvas.size)
