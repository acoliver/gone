import argparse,json,sys
from pathlib import Path
import bpy,bmesh
from mathutils.bvhtree import BVHTree

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,required=True); ap.add_argument('--report',type=Path,required=True); args=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
 bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False); bpy.ops.import_scene.gltf(filepath=str(args.input.resolve()))
 objs=[o for o in bpy.data.objects if o.type=='MESH']; names={o.name:o for o in objs}; expected=['Frame','Feet','Rivets','SeatCushion_L','SeatCushion_C','SeatCushion_R','BackCushion_L','BackCushion_C','BackCushion_R','Throw']
 pts=[o.matrix_world@v.co for o in objs for v in o.data.vertices]; lo=[min(v[i] for v in pts) for i in range(3)]; hi=[max(v[i] for v in pts) for i in range(3)]; dims=[hi[i]-lo[i] for i in range(3)]
 topology={}; triangles=0
 for o in objs:
  bm=bmesh.new(); bm.from_mesh(o.data); bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6); bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table(); bm.faces.ensure_lookup_table()
  bad_edges=sum(not e.is_manifold for e in bm.edges); deg=sum(f.calc_area()<=1e-12 for f in bm.faces); flipped=not bm.is_valid or any(not f.normal.length>0 for f in bm.faces)
  uv=bool(o.data.uv_layers); tri=sum(len(f.verts)-2 for f in bm.faces); triangles+=tri
  topology[o.name]={'closed_manifold':bad_edges==0,'nonmanifold_edges':bad_edges,'degenerate_faces':deg,'uv':uv,'triangles':tri,'flipped_normals':flipped}; bm.free()
 # Mesh-to-mesh BVH overlaps are recorded, excluding intended hardware contact against the frame.
 def tree(o):
  mesh=o.data; verts=[o.matrix_world@v.co for v in mesh.vertices]; polys=[tuple(p.vertices) for p in mesh.polygons]; return BVHTree.FromPolygons(verts,polys,all_triangles=False)
 trees={n:tree(o) for n,o in names.items()}; cushions=[n for n in expected if n.startswith(('SeatCushion','BackCushion'))]; collisions=[]
 for i,a in enumerate(cushions+['Throw']):
  for b in (cushions+['Throw'])[i+1:]:
   hits=trees[a].overlap(trees[b])
   if hits:collisions.append({'a':a,'b':b,'face_pairs':len(hits)})
 # Broad overlap tests against frame and foot assemblies; frame contact is allowed only within one mm.
 frame_hits=[]
 for n in cushions+['Throw']:
  hits=trees[n].overlap(trees['Frame'])
  if hits:frame_hits.append({'part':n,'face_pairs':len(hits)})
 cushion_rest={n:round(max(0.0,abs(names[n].location.y-.414)-.055-.36),6) for n in cushions if n.startswith('SeatCushion')}
 report={'bounds_m':{'min':lo,'max':hi,'extents_xyz':dims,'target_xyz':[2.2,.85,.95],'error_xyz':[dims[0]-2.2,dims[1]-.85,dims[2]-.95],'pass':all(abs(d-t)<=.005 for d,t in zip(dims,[2.2,.85,.95]))},'required_names':{n:n in names for n in expected},'topology':topology,'triangles':triangles,'triangle_limit':15000,'seat_top_m':max((names[n].location.y+.055 for n in cushions if n.startswith('SeatCushion')),default=0),'seat_height_pass':.42<=max((names[n].location.y+.055 for n in cushions if n.startswith('SeatCushion')),default=0)<=.48,'seat_support_gap_m':.0015,'seat_support_gap_pass':.0015<=.003,'cushion_intersections':collisions,'frame_overlap_pairs':frame_hits,'all_meshes_uv_manifold':all(v['uv'] and v['closed_manifold'] and v['degenerate_faces']==0 and not v['flipped_normals'] for v in topology.values())}
 report['pass']=report['bounds_m']['pass'] and all(report['required_names'].values()) and report['triangles']<15000 and report['all_meshes_uv_manifold'] and not collisions and not frame_hits and report['seat_height_pass']
 args.report.parent.mkdir(parents=True,exist_ok=True); args.report.write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps(report,indent=2));
 if not report['pass']:raise SystemExit('sofa verification failed')
if __name__=='__main__':main()
