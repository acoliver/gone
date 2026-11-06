from pathlib import Path
import sys,json,math
import bpy,bmesh,numpy as np
from mathutils import Matrix
OUT=Path(sys.argv[-3]).resolve()
ROOT=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(ROOT/"tools/blender"))
import build_hatch as build
from hatch_bake import CINV
name=sys.argv[-2];budget=int(sys.argv[-1])
data=np.load(OUT/(name.lower()+"-high.npz"));p,f=data["vertices"],data["faces"]
obj=build.mesh_object(name,p,f,None,Matrix.Identity(4),build.material(),recalc=False)
pins=set()
if name=='Sector':
    # Keep the generated diameter and all repeated axial extrema exactly.
    for angle in np.radians(np.arange(6)*60):
        rotated=np.c_[p[:, 0]*np.cos(angle)-p[:, 1]*np.sin(angle), p[:, 0]*np.sin(angle)+p[:, 1]*np.cos(angle)]
        for axis in range(2):
            pins.update([int(rotated[:,axis].argmin()),int(rotated[:,axis].argmax())])
for axis in range(3):
    pins.update([int(p[:,axis].argmin()),int(p[:,axis].argmax())])
group=obj.vertex_groups.new(name='SourceExtrema')
if name == 'Sector':
    group.add(np.flatnonzero(np.linalg.norm(p[:, :2], axis=1) > .29).tolist(), .01, 'REPLACE')
group.add(sorted(pins),1.,'REPLACE')
modifier=obj.modifiers.new(name+'Reduction','DECIMATE')
modifier.ratio=budget/len(f)
modifier.use_collapse_triangulate=True
modifier.vertex_group=group.name
modifier.invert_vertex_group=True
modifier.vertex_group_factor=1000
bpy.context.view_layer.objects.active=obj
print('REDUCE_START',name,len(f),budget,flush=True)
bpy.ops.object.modifier_apply(modifier=modifier.name)
bm=bmesh.new(); bm.from_mesh(obj.data)
bmesh.ops.dissolve_degenerate(bm,dist=.0001,edges=list(bm.edges))
bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method='BEAUTY',ngon_method='BEAUTY')
bmesh.ops.beautify_fill(bm,faces=list(bm.faces),edges=list(bm.edges),method='ANGLE')
bm.to_mesh(obj.data); bm.free()
points=np.asarray([tuple((CINV@v.co.to_4d())[:3]) for v in obj.data.vertices])
faces=np.asarray([tuple(face.vertices) for face in obj.data.polygons])
points=np.clip(points,p.min(0),p.max(0))
if name == 'Sector':
    for angle in np.radians(np.arange(6)*60):
        rotated=np.c_[points[:,0]*np.cos(angle)-points[:,1]*np.sin(angle), points[:,0]*np.sin(angle)+points[:,1]*np.cos(angle)]
        fraction=np.maximum(np.abs(rotated)/[.3214273452758789,.3186988830566406],1).max(axis=1)
        points[:,:2]/=fraction[:,None]
limit=.32150001021434993
radial=np.linalg.norm(points[:,:2],axis=1)
escape=radial>limit
points[escape,:2]*=(limit/radial[escape])[:,None]

np.savez_compressed(OUT/(name.lower()+"-low.npz"),vertices=points,faces=faces)
print("REDUCED",name,len(faces),flush=True)
