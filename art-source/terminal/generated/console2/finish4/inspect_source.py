import bpy,json,numpy as np
from pathlib import Path
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'finish3/console.blend'))
b=bpy.data.objects['ConsoleBody'];report={}
for i,m in enumerate(b.data.materials):
 faces=[p for p in b.data.polygons if p.material_index==i]
 report[str(i)]={'name':m.name if m else None,'faces':len(faces),'area_m2':sum(p.area for p in faces),'centres_min':np.min(np.array([p.center[:] for p in faces]),0).tolist() if faces else None,'centres_max':np.max(np.array([p.center[:] for p in faces]),0).tolist() if faces else None,'nodes':[(n.name,n.type,getattr(getattr(n,'image',None),'filepath',None)) for n in m.node_tree.nodes] if m and m.use_nodes else None}
print('MATERIALS',json.dumps(report),flush=True)
print('INDEX_COUNTS',np.unique([p.material_index for p in b.data.polygons],return_counts=True),flush=True)
print('UV_LAYERS',[(u.name,u.active_render,u.active) for u in b.data.uv_layers],flush=True)
print('SCENE_OBJECTS',[(o.name,o.type,o.hide_render,len(o.data.polygons) if o.type=='MESH' else None) for o in bpy.context.scene.objects],flush=True)
print('IMAGES',[(i.name,i.size[:],i.colorspace_settings.name,i.filepath) for i in bpy.data.images],flush=True)
(O/'source-materials.json').write_text(json.dumps(report,indent=2))
