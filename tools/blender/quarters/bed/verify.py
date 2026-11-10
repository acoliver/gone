"""Verify the exported bare bed frame and the exposed mattress platform."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
import trimesh

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'wardrobe'))
from verify_common import verify


def main():
    root=HERE.parents[3]
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,default=root/'assets/props/quarters/bed.glb')
    parser.add_argument('--reexport',type=Path,required=True)
    args=parser.parse_args()
    report=verify(args.input,HERE/'construction.json',HERE/'verify.json',args.reexport)
    scene=trimesh.load(args.input,force='scene')
    frame_parts=[]
    platform=None
    for name in scene.graph.nodes_geometry:
        matrix,key=scene.graph[name]
        mesh=scene.geometry[key].copy();mesh.apply_transform(matrix)
        if name=='MattressPlatform':platform=mesh
        if name.startswith('Frame'):frame_parts.append(mesh)
    frame=trimesh.util.concatenate(frame_parts)
    frame_top=float(frame.bounds[1,1])
    body_height_pass=abs(frame_top-.55)<=.01
    platform_height=float(platform.bounds[1,1])
    platform_low,platform_high=json.loads((HERE/'construction.json').read_text())['platform_range_m']
    origins=np.array([[x,1.5,z] for x in np.linspace(-.6,.6,15) for z in np.linspace(-.85,.85,21)])
    hits=platform.ray.intersects_any(origins,np.tile([0,-1,0],(len(origins),1)))
    soft_nodes=sorted({'Mattress','Quilt','Pillow_L','Pillow_R','HeadboardPad'}&set(scene.graph.nodes))
    report['frame_and_platform']={'frame_top_m':frame_top,'layout_frame_top_m':.55,
        'platform_height_m':platform_height,'platform_probe_count':len(origins),
        'platform_ray_misses':int((~hits).sum()),'soft_part_nodes':soft_nodes,
        'platform_design':'A continuous solid exposed steel support plate follows the approved source; crossmembers reinforce its underside.',
        'platform_design_range_m':[platform_low,platform_high],
        'pass':body_height_pass and platform_low-.001<=platform_height<=platform_high+.001 and bool(hits.all()) and not soft_nodes}
    report['pass']=report['pass'] and report['frame_and_platform']['pass']
    (HERE/'verify.json').write_text(json.dumps(report,indent=2)+'\n')
    if not report['pass']:raise SystemExit('Bed frame contract failed')
    print('Bed frame and exposed platform PASS')


if __name__=='__main__':main()
