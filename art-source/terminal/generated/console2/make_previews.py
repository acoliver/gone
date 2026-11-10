from pathlib import Path
import json, subprocess
import numpy as np
import trimesh
from PIL import Image, ImageOps, ImageDraw
root=Path(__file__).resolve().parent
(root/'previews').mkdir(exist_ok=True)
renderer=Path('/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/tests/render_mesh.py')
python=Path('/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python')
views={'front':(['0'],0),'side':(['90'],0),'34':(['45'],0),'top':(['0'],90)}
meshes=sorted((root/'meshes').glob('*.glb'))
records=[]
for path in meshes:
    mesh=trimesh.load(path,force='mesh')
    records.append({'mesh':path.name,'vertices':len(mesh.vertices),'triangles':len(mesh.faces),'bounds_min':mesh.bounds[0].round(6).tolist(),'bounds_max':mesh.bounds[1].round(6).tolist(),'components':len(mesh.split(only_watertight=False)),'watertight':bool(mesh.is_watertight)})
    for view,(angles,elevation) in views.items():
        out=root/'previews'/f'{path.stem}-{view}.png'
        subprocess.run([str(python),str(renderer),str(path),'--out',str(out),'--size','384','--angles',*angles,'--elevation',str(elevation)],check=True,cwd=renderer.parent)
(root/'mesh-metrics.json').write_text(json.dumps(records,indent=2)+'\n')
for kind in ('console','keyboard'):
    rows=[p for p in meshes if p.name.startswith(kind+'-')]
    cells=[]
    for mesh_path in rows:
        input_path=root/'inputs'/(mesh_path.name.rsplit('-',1)[0]+'.png')
        image=Image.open(input_path).convert('RGB')
        image.thumbnail((384,384))
        canvas=Image.new('RGB',(384,384),'white'); canvas.paste(image,((384-image.width)//2,(384-image.height)//2)); cells.append(canvas)
        for view in views:
            cells.append(Image.open(root/'previews'/f'{mesh_path.stem}-{view}.png').convert('RGB').resize((384,384)))
    sheet=Image.new('RGB',(384*5,384*len(rows)),(245,245,245))
    draw=ImageDraw.Draw(sheet)
    for ri,row in enumerate(rows):
        for ci in range(5):
            sheet.paste(cells[ri*5+ci],(ci*384,ri*384))
        draw.rectangle((0,ri*384,384*5-1,(ri+1)*384-1),outline=(180,180,180),width=2)
    sheet.save(root/'previews'/f'{kind}-meshes.png')
print(json.dumps(records,indent=2))
