import bpy,numpy as np,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
O=Path(__file__).resolve().parent
for folder in ['finish3','finish4']:
 bpy.ops.wm.open_mainfile(filepath=str(O.parent/folder/'console.blend'));b=bpy.data.objects['ConsoleBody'];me=b.data;bv=BVHTree.FromPolygons([v.co for v in me.vertices],[p.vertices[:] for p in me.polygons]);images={n.image.name:n.image for n in b.active_material.node_tree.nodes if n.type=='TEX_IMAGE'};pixels={n:np.array(im.pixels[:]).reshape(2048,2048,4) for n,im in images.items()}
 for name,origin,direction in [('roof',(0,-.2,2),(0,0,-1)),('front',(0,-2,1.23),(0,1,0)),('right',(.47,-.60,1),(0,0,-1))]:
  h,n,f,d=bv.ray_cast(Vector(origin),Vector(direction));p=me.polygons[f];v=[me.vertices[i].co for i in p.vertices];uv=[Vector((*me.uv_layers.active.data[i].uv,0)) for i in p.loop_indices];q=barycentric_transform(h,*v,*uv);u=int(q.x*2048)%2048;w=int(q.y*2048)%2048
  print('PROBE',folder,name,list(h),list(n),list(q),{n:ar[w,u,:3].tolist() for n,ar in pixels.items()},flush=True)
 if folder=='finish4':
  mat=b.active_material;ns=mat.node_tree.nodes;ls=mat.node_tree.links;o=next(n for n in ns if n.type=='OUTPUT_MATERIAL');at=next(n for n in ns if n.type=='TEX_IMAGE' and 'albedo' in n.image.name);em=ns.new('ShaderNodeEmission');ls.new(at.outputs['Color'],em.inputs[0]);ls.new(em.outputs[0],o.inputs[0]);scene=bpy.context.scene;scene.camera=bpy.data.objects['ThreeQuarter'];scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.render.filepath=str(O/'albedo-roof-probe.png');bpy.ops.render.render(write_still=True)
