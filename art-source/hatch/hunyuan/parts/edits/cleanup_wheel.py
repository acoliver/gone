from pathlib import Path
import sys,json
import bpy,bmesh,numpy as np
from mathutils import Matrix
OUT=Path(sys.argv[-1]).resolve();ROOT=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(ROOT/'tools/blender'))
import build_hatch as build
from hatch_bake import CINV
source=np.load(OUT/'wheel-low.npz');p,f=source['vertices'],source['faces']
obj=build.mesh_object('SeamCleanup',p,f,None,Matrix.Identity(4),build.material(),recalc=False)
limit=.32150001021434993
# QEM leaves needle facets at the Boolean seams. Clean only the low-poly
# tessellation; the frozen high-poly source and its approved cut stay intact.
from hatch_bake import C
# Clean in the final part-local float32 frame. Centering after cleanup can
# otherwise quantize a nearly collinear seam back into a zero-tangent facet.
center = (p.min(0) + p.max(0)) / 2
for vertex, point in zip(obj.data.vertices, p):
    vertex.co = C.to_3x3() @ build.Vector(point - center)
bm = bmesh.new()
bm.from_mesh(obj.data)
bmesh.ops.dissolve_degenerate(bm, dist=.0001, edges=list(bm.edges))
bmesh.ops.triangulate(bm, faces=list(bm.faces), quad_method='BEAUTY', ngon_method='BEAUTY')
bmesh.ops.beautify_fill(bm, faces=list(bm.faces), edges=list(bm.edges), method='ANGLE')
# MikkTSpace's float32 corner weights vanish on nearly straight needle
# facets. Collapse their middle vertices onto an endpoint, keeping bound pins.
protected = set()
for axis in range(3):
    protected.add(tuple(min(bm.verts, key=lambda v: v.co[axis]).co))
    protected.add(tuple(max(bm.verts, key=lambda v: v.co[axis]).co))
protected.update(tuple(v.co) for v in bm.verts if np.hypot(v.co.x, v.co.z) >= limit - 1e-7)
quality_removed = 0
while True:
    candidates = []
    for face in bm.faces:
        vertices = list(face.verts)
        points = np.asarray([tuple(v.co) for v in vertices])
        a, b = np.roll(points, -1, axis=0) - points, np.roll(points, 1, axis=0) - points
        cosine = np.einsum('ij,ij->i', a, b) / (np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1))
        angles = np.arccos(np.clip(cosine, -1, 1))
        if not np.isfinite(angles).all():
            raise RuntimeError('wheel low-poly cleanup produced a degenerate face')
        if angles.min() < np.radians(.1):
            candidates.append((float(angles.min()), vertices[int(angles.argmax())]))
    if not candidates:
        break
    _, vertex = min(candidates, key=lambda row: row[0])
    if tuple(vertex.co) in protected:
        raise RuntimeError('wheel minimum-angle cleanup would remove a diameter/bounds pin: ' + str(tuple(vertex.co)))
    target = min((edge.other_vert(vertex) for edge in vertex.link_edges), key=lambda other: (other.co - vertex.co).length_squared)
    before = len(bm.verts)
    bmesh.ops.pointmerge(bm, verts=[target, vertex], merge_co=target.co.copy())
    if len(bm.verts) >= before:
        raise RuntimeError('wheel minimum-angle cleanup made no progress')
    quality_removed += before - len(bm.verts)
    bmesh.ops.triangulate(bm, faces=list(bm.faces), quad_method='BEAUTY', ngon_method='BEAUTY')
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
bm.to_mesh(obj.data)
bm.free()
p = np.asarray([tuple((CINV @ v.co.to_4d())[:3]) for v in obj.data.vertices]) + center
f = np.asarray([tuple(face.vertices) for face in obj.data.polygons])
used, remap = np.unique(f, return_inverse=True)
p, f = p[used], remap.reshape(-1, 3)
np.savez_compressed(OUT/'wheel-low.npz',vertices=p,faces=f)

print('FINAL_CLEANUP',len(f),'quality_removed',quality_removed,flush=True)

# Refresh the measured support consumed by the exporter and parked-box derivation.
def convex_profile(points):
    points=np.unique(points,axis=0).tolist()
    def turn(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    halves=[]
    for sequence in [points,points[::-1]]:
        half=[]
        for point in sequence:
            while len(half)>=2 and turn(half[-2],half[-1],point)<=0:half.pop()
            half.append(point)
        halves.extend(half[:-1])
    return halves
SOURCE=Path(__file__).resolve().parents[1]
record=json.loads((SOURCE/'wheel-fit.json').read_text())
record.update(size=np.ptp(p,axis=0).tolist(),center=((p.min(0)+p.max(0))/2).tolist(),profile_rz=convex_profile(np.c_[np.linalg.norm(p[:,:2],axis=1),p[:,2]]),radial_bound_m=float(np.linalg.norm(p[:,:2],axis=1).max()),triangles=len(f))
(OUT/'wheel-fit.json').write_text(json.dumps(record,indent=2)+chr(10))
