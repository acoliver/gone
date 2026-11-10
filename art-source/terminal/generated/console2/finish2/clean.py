import bpy,bmesh,numpy as np,json
from pathlib import Path
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'source.blend')); b=bpy.data.objects['ConsoleBody']; bm=bmesh.new();bm.from_mesh(b.data)
old=len(bm.faces); bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.co.y>-.03],context='VERTS'); bm.to_mesh(b.data);bm.free();b.data.update()
a=np.array([v.co[:] for v in b.data.vertices]); lo=a.min(0);hi=a.max(0); cx=(lo[0]+hi[0])/2; sx=1.1/(hi[0]-lo[0])
for v in b.data.vertices:v.co.x=(v.co.x-cx)*sx
b.data.update(); print('REMOVED_BACKDROP',old-len(b.data.polygons),'X_SCALE',sx,flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'source.blend'))
(O/'cleanup.json').write_text(json.dumps({'removed_backdrop_faces':old-len(b.data.polygons),'backdrop_y_cut_m':-.03,'console_recentred_x_m':float(cx),'console_width_scale':float(sx),'reason':'Generated rectangular backdrop surrounds the console; remove it, preserve UVs, restore requested 1.10 m console width.'},indent=2))
# Reuse the silhouette renderer without re-importing the original mesh.
s= (O/'prepare.py').read_text(); s=s[s.index('verts=np.array'):]; exec(s,{'bpy':bpy,'np':np,'json':json,'OUT':O,'ROOT':O.parent,'body':b,'scene':bpy.context.scene,'Vector':__import__('mathutils').Vector})
