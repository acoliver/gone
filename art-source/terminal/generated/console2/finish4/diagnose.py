import bpy, json, numpy as np, bmesh
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'finish3/console.blend'))
b=bpy.data.objects['ConsoleBody']; mesh=b.data
bv=BVHTree.FromPolygons([b.matrix_world@v.co for v in mesh.vertices],[p.vertices[:] for p in mesh.polygons])
print('OBJECT',b.matrix_world[:],len(mesh.vertices),len(mesh.polygons),flush=True)
images={n.image.name:n.image for n in b.active_material.node_tree.nodes if n.type=='TEX_IMAGE'}
print('IMAGES',list(images),flush=True)
def rgb(hit,face):
 p=mesh.polygons[face];ids=p.vertices;v=[b.matrix_world@mesh.vertices[i].co for i in ids];from mathutils.geometry import barycentric_transform
 uv=mesh.uv_layers.active.data
 coords=[Vector((*uv[i].uv,0)) for i in p.loop_indices]
 q=barycentric_transform(hit,v[0],v[1],v[2],coords[0],coords[1],coords[2]);u=int(q.x*2048)%2048;w=int(q.y*2048)%2048
 return {name:[round(float(c),4) for c in arr[w,u,:3]] for name,arr in pixels.items()}
pixels={name:np.array(im.pixels[:],np.float32).reshape(im.size[1],im.size[0],4) for name,im in images.items()}
rows=[]
for x in np.round(np.arange(-.4,.401,.05),4):
 front=[];oblique=[]
 for z in np.linspace(.60,.78,181):
  h,n,f,d=bv.ray_cast(Vector((x,-2,z)),Vector((0,1,0)))
  if h:front.append([round(float(z),5),round(h.y,6),rgb(h,f)])
  origin=Vector((x,-2,z+1.2));direction=Vector((0,1,-.8)).normalized();h,n,f,d=bv.ray_cast(origin,direction)
  if h:oblique.append([round(float(z),5),*[round(float(v),6) for v in h]])
 rows.append({'x':float(x),'front':front,'above_front':oblique})
 # Print depth profiles every 5 mm for the contact diagnosis.
 print('PROFILE',x,[(r[0],r[1]) for r in front[::5]],flush=True)
bm=bmesh.new();bm.from_mesh(mesh)
report={'rays':rows,'sockets':{n:[list(r) for r in bpy.data.objects[n].matrix_world] for n in ['ScreenSocket','KeyboardSocket']},'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges)}
bm.free();(O/'diagnosis-rays.json').write_text(json.dumps(report))
print('TOPOLOGY',report['boundary_edges'],report['nonmanifold_edges'],flush=True)
# Dump source images metadata and geometry samples of the right junction.
for n,im in images.items():print('TEXTURE',n,im.filepath,flush=True)
for x in [.35,.4,.425,.45,.475]:
 samples=[]
 for z in np.arange(.62,.731,.005):
  hit=bv.ray_cast(Vector((x,-2,z)),Vector((0,1,0)))[0]
  samples.append((round(z,3),round(hit.y,5) if hit is not None else None))
 print('RIGHT',x,samples,flush=True)
