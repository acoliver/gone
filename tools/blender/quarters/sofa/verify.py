import argparse,json,subprocess,sys
from pathlib import Path
import bpy

CHECK = r'''import json,sys,trimesh,numpy as np
p=sys.argv[1]; s=trimesh.load(p); names=list(s.graph.nodes_geometry); expected=['Frame','Feet','Rivets','SeatCushion_L','SeatCushion_C','SeatCushion_R','BackCushion_L','BackCushion_C','BackCushion_R','Throw']; bounds=s.bounds; target=np.array([[-1.1,0,-.475],[1.1,.85,.475]]); err=np.abs(bounds-target); dims={}; seat_top={}; tris=0
for n in names:
 t,g=s.graph.get(n); m=s.geometry[g].copy(); m.apply_transform(t); tris+=len(m.faces)
 if n.startswith('SeatCushion_') or n.startswith('BackCushion_'):
  dims[n]=np.ptp(m.vertices,axis=0).tolist()
 if n.startswith('SeatCushion_'):
  top=m.bounds[1,1]; mask=(m.triangles_center[:,1]>top-.006)&(m.face_normals[:,1]>.9); seat_top[n]={'top_y':float(top),'upward_faces':int(mask.sum()),'max_top_normal_y':float(m.face_normals[mask,1].max()) if mask.any() else -1}
unique_geometry=len(set(id(g) for g in s.geometry.values())); pass_bounds=bool(np.all(err<=.005)); pass_normals=all(v['upward_faces']>0 and v['max_top_normal_y']>.99 for v in seat_top.values()); r={'bounds_m':bounds.tolist(),'target_bounds_m':target.tolist(),'max_bound_error_m':err.tolist(),'bounds_pass':pass_bounds,'nodes':names,'required_nodes_pass':sorted(names)==sorted(expected),'geometry_count':len(s.geometry),'unique_geometry_count':unique_geometry,'duplicate_geometry_pass':unique_geometry==len(s.geometry)==len(expected),'cushion_extents_xyz_m':dims,'seat_top_faces':seat_top,'seat_top_normals_pass':pass_normals,'triangles':tris,'triangle_limit':15000,'pass':pass_bounds and sorted(names)==sorted(expected) and unique_geometry==len(s.geometry)==len(expected) and pass_normals and tris<15000}; print(json.dumps(r)); sys.exit(0 if r['pass'] else 1)'''

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,required=True); ap.add_argument('--report',type=Path,required=True); args=ap.parse_args(sys.argv[sys.argv.index('--')+1:]); path=args.input.resolve(); result=subprocess.run(['/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python','-c',CHECK,str(path)],check=False,text=True,capture_output=True)
 if result.returncode: print(result.stdout); print(result.stderr,file=sys.stderr); raise SystemExit('trimesh export verification failed')
 report=json.loads(result.stdout); report['pass']=report['pass'] and report['bounds_pass'] and report['required_nodes_pass'] and report['duplicate_geometry_pass'] and report['seat_top_normals_pass']; args.report.parent.mkdir(parents=True,exist_ok=True); args.report.write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps(report,indent=2))
 if not report['pass']:raise SystemExit('sofa verification failed')
if __name__=='__main__':main()
