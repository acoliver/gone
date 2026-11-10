import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).resolve().parent;P=O.parent
bpy.ops.wm.open_mainfile(filepath=str(P/'finish4/console.blend'))
b=bpy.data.objects['ConsoleBody'];tree=BVHTree.FromPolygons([b.matrix_world@v.co for v in b.data.vertices],[p.vertices[:] for p in b.data.polygons])
samples=[]
for y in np.linspace(-.655,-.545,5):
 for x in np.linspace(-.39,.39,5):
  h,n,f,d=tree.ray_cast(Vector((x,y,.9)),Vector((0,0,-1)));assert h is not None
  samples.append(list(h))
a=np.array(samples);fit=np.linalg.lstsq(np.c_[a[:,:2],np.ones(25)],a[:,2],rcond=None)[0];res=a[:,2]-np.c_[a[:,:2],np.ones(25)]@fit
# Find the flat top's connected interval at the centre by normal and residual.
rows=[]
for y in np.linspace(-.71,-.49,2201):
 h,n,f,d=tree.ray_cast(Vector((0,y,.9)),Vector((0,0,-1)))
 if h is not None:rows.append([y,h.z,n.y,n.z,float(h.z-(fit[1]*y+fit[2]))])
print('DECK',fit,'RESIDUAL',res.min(),res.max(),flush=True)
print('OBJECTS',[(o.name,o.type,list(o.location),list(o.dimensions)) for o in bpy.context.scene.objects if o.name in ['ConsoleBody','DisplayPlane','ScreenSocket','KeyboardSocket']],flush=True)
(O/'measure.json').write_text(json.dumps({'plane':fit.tolist(),'samples':samples,'residual_mm':(res*1000).tolist(),'profile':rows},indent=2))
with bpy.data.libraries.load(str(P/'kb3/keyboard.blend'),link=False) as (src,dst):dst.objects=['Keyboard','KeyboardBase']
for o in dst.objects:bpy.context.scene.collection.objects.link(o)
bpy.context.view_layer.update()
for o in dst.objects:print('KEYBOARD',o.name,'LOCATION',list(o.location),'MATRIX',[list(r) for r in o.matrix_world],'BOUNDS',[list(v) for v in o.bound_box],flush=True)
print('MEASURE_DONE',flush=True)
