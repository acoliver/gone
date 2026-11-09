"""Check the wardrobe GLB, UV atlas, clear interior and exported door sweep."""
import argparse
import json
from pathlib import Path
import subprocess

import numpy as np
import trimesh

from verify_common import verify

HERE=Path(__file__).resolve().parent
BLENDER='/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender'


def main():
    root=HERE.parents[3]
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,default=root/'assets/props/quarters/wardrobe.glb')
    parser.add_argument('--reexport',type=Path,required=True)
    args=parser.parse_args()
    report=verify(args.input,HERE/'construction.json',HERE/'verify.json',args.reexport)
    report['pass']=False
    report['door_sweep']={'pass':False,'status':'not yet completed'}
    (HERE/'verify.json').write_text(json.dumps(report,indent=2)+chr(10))
    subprocess.run([BLENDER,'--background','--factory-startup','--python-exit-code','1',
                    '--python',str(HERE/'sweep.py'),'--',str(args.input)],check=True)
    sweep_path=args.input.with_suffix('.sweep.json')
    report['door_sweep']=json.loads(sweep_path.read_text())
    sweep_path.unlink()
    scene=trimesh.load(args.input,force='scene')
    meshes=[]; ids=[]
    for node in sorted(scene.graph.nodes_geometry):
        matrix,key=scene.graph[node]; mesh=scene.geometry[key].copy(); mesh.apply_transform(matrix)
        meshes.append(mesh); ids.extend([node]*len(mesh.faces))
    combined=trimesh.util.concatenate(meshes)
    spec=json.loads((HERE/'construction.json').read_text())
    body_meshes=[mesh for node,mesh in zip(sorted(scene.graph.nodes_geometry),meshes) if node not in spec['bounds_exclude']]
    body=trimesh.util.concatenate(body_meshes)
    lo=np.array([-.5,.145,-.325]); hi=np.array([.5,2.2,.325]); centre=np.array([0,1.1,0])
    probes=[]
    for axis_index in range(3):
        other=[i for i in range(3) if i!=axis_index]
        for side in (0,1):
            if axis_index==2 and side==1:continue
            for a in np.arange(lo[other[0]]+.025,hi[other[0]],.05):
                for b in np.arange(lo[other[1]]+.025,hi[other[1]],.05):
                    point=centre.copy(); point[axis_index]=(-.001 if axis_index==1 else lo[axis_index]-.001) if side==0 else hi[axis_index]+.001
                    point[other[0]]=a; point[other[1]]=b; probes.append(point)
    probes=np.array(probes); directions=centre-probes; limits=np.linalg.norm(directions,axis=1)
    directions/=limits[:,None]
    locations,rays,_=body.ray.intersects_location(probes,directions,multiple_hits=False)
    valid=np.unique(rays[np.linalg.norm(locations-probes[rays],axis=1)<limits[rays]])
    report['closed_carcass']={'face_count':5,'intentionally_open_front':True,
        'ray_count':len(probes),'misses':len(probes)-len(valid),'pass':len(probes)==len(valid)}
    origins=np.array([[x,y,.8] for x in np.linspace(-.41,.41,15) for y in np.linspace(.4,1.7,25)])
    hit=combined.ray.intersects_first(origins,np.tile([0,0,-1],(len(origins),1)))
    obstruction=[ids[i] if i>=0 else 'miss' for i in hit if i<0 or ids[i]!='BackPanel']
    report['hanging_envelope']={'width_m':.82,'sample_height_range_m':[.4,1.7],
        'first_hit_back_panel_rays':len(origins)-len(obstruction),'ray_count':len(origins),
        'obstructions':sorted(set(obstruction)),'rail_height_m':float(scene.graph['Rail'][0][1,3]),
        'pass':not obstruction}
    door_matrix,_=scene.graph['Door']
    axis=door_matrix[:3,:3]@np.array([0,1,0])
    report['parked_leaf_axis']={'native_up_in_gltf':axis.tolist(),'pass':bool(abs(axis[1]-1)<1e-6)}
    forward=door_matrix[:3,:3]@np.array([0,0,1])
    expected_forward=np.array([np.sin(np.deg2rad(100)),0,np.cos(np.deg2rad(100))])
    report['front_and_park_angle']={'closed_front_axis':[0,0,1],
        'parked_front_normal':forward.tolist(),'expected':expected_forward.tolist(),
        'pass':bool(np.max(np.abs(forward-expected_forward))<1e-6)}
    report['pass']=(report['closed_carcass']['pass'] and report['door_sweep']['pass'] and report['front_and_park_angle']['pass'] and
                    report['hanging_envelope']['pass'] and report['parked_leaf_axis']['pass'])
    (HERE/'verify.json').write_text(json.dumps(report,indent=2)+'\n')
    if not report['pass']:raise SystemExit('Wardrobe contract failed')
    print('Wardrobe GLB, clear hanging envelope and sweep PASS')


if __name__=='__main__':main()
