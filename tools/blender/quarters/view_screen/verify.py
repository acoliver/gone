"""Validate wall-screen geometry, real glass aperture and separate display."""
import argparse
import json
from pathlib import Path
import struct
import sys

import numpy as np
import trimesh

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'wardrobe'))
from verify_common import verify


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,default=HERE.parents[3]/'assets/props/quarters/view_screen.glb')
    parser.add_argument('--reexport',type=Path,required=True)
    args=parser.parse_args()
    report=verify(args.input,HERE/'construction.json',HERE/'verify.json',args.reexport)
    data=args.input.read_bytes(); length,kind=struct.unpack_from('<II',data,12)
    if kind!=0x4E4F534A:raise ValueError('Expected glTF JSON chunk')
    document=json.loads(data[20:20+length])
    glass=next(m for m in document['materials'] if m['name']=='Glass')
    transmission=glass['extensions']['KHR_materials_transmission']['transmissionFactor']
    scene=trimesh.load(args.input,force='scene'); meshes={}
    for name in scene.graph.nodes_geometry:
        transform,key=scene.graph[name]; mesh=scene.geometry[key].copy();mesh.apply_transform(transform);meshes[name]=mesh
    glass_mesh=meshes['Glass']; display=meshes['Display']
    glass_thickness=float(glass_mesh.extents[2]); emission=np.asarray(display.visual.material.emissiveFactor)
    # Ignore the physically transparent cover when testing the housing aperture.
    housing=trimesh.util.concatenate([m for n,m in meshes.items() if n not in {'Glass','Display','ScreenBacking'}])
    origin=np.array([[0,.525,.5]]); direction=np.array([[0,0,-1]])
    locations,_,_=housing.ray.intersects_location(origin,direction,multiple_hits=False)
    first_z=float(locations[0,2])
    aperture_clear=first_z<display.bounds[0,2]
    report['screen_assembly']={'glass_thickness_m':glass_thickness,'glass_transmission':transmission,
        'glass_front_z_m':float(glass_mesh.bounds[1,2]),'display_front_z_m':float(display.bounds[1,2]),
        'display_emissive_factor':emission.tolist(),'housing_centre_first_hit_z_m':first_z,
        'pass':.0039<glass_thickness<.0041 and transmission>=.9 and aperture_clear and
               float(glass_mesh.bounds[0,2])>float(display.bounds[1,2]) and bool(np.any(emission>0))}
    report['pass']=report['pass'] and report['screen_assembly']['pass']
    (HERE/'verify.json').write_text(json.dumps(report,indent=2)+'\n')
    if not report['pass']:raise SystemExit('Glass, display or housing aperture contract failed')
    print('Separate glass, emissive display and open housing aperture PASS')


if __name__=='__main__':main()
