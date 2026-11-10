import bpy,bmesh,numpy as np,json
from pathlib import Path
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'assembly3/console-with-keyboard.blend'))
m=bpy.data.objects['ConsoleBody'].data
bm=bmesh.new();bm.from_mesh(m);bm.normal_update();selected={f for f in bm.faces if f.normal.z<-.2 and .43<f.calc_center_median().z<.55 and f.calc_center_median().y<-.55}
components=[]
while selected:
 first=selected.pop();todo=[first];faces=[first]
 while todo:
  f=todo.pop()
  for e in f.edges:
   for g in e.link_faces:
    if g in selected:selected.remove(g);todo.append(g);faces.append(g)
 verts=np.array([v.co[:] for f in faces for v in f.verts]);components.append({'faces':len(faces),'min':verts.min(0).tolist(),'max':verts.max(0).tolist(),'lowest':verts[np.argmin(verts[:,2])].tolist()})
components.sort(key=lambda c:-c['faces']);print('LIP_COMPONENTS',json.dumps(components),flush=True)
(O/'lip-measure.json').write_text(json.dumps(components,indent=2))
