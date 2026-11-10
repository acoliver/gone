"""Validate the fitted console and its separately exported emissive display."""
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
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,default=HERE.parents[3]/'assets/props/quarters/console.glb')
    parser.add_argument('--reexport',type=Path,required=True)
    args=parser.parse_args()
    report=verify(args.input,HERE/'construction.json',HERE/'verify.json',args.reexport)
    scene=trimesh.load(args.input,force='scene')
    frame,key=scene.graph['Display']; screen=scene.geometry[key]
    size=screen.extents
    lower_edge=(frame @ np.array([0,-size[1]/2,0,1]))[:3]
    # #129 pins the taller active glass and its unchanged lower edge and tilt.
    report['display_fit']={'size_m':size.tolist(),'aspect':float(size[0]/size[1]),
        'lower_edge_gltf_m':lower_edge.tolist(),'front_normal_gltf':frame[:3,2].tolist(),
        'pass':bool(np.allclose(size,[.874,.54625,.004],atol=1e-6) and
                    np.allclose(lower_edge,[0,.454878712,.062092286],atol=1e-6) and
                    np.allclose(frame[:3,2],[0,.514495756,.857492925],atol=1e-6))}
    emission=np.asarray(screen.visual.material.emissiveFactor)
    keys=sorted(n for n in scene.graph.nodes_geometry if n.startswith('Key_'))
    toggles=sorted(n for n in scene.graph.nodes_geometry if n.startswith('Toggle_'))
    report['console_parts']={'display_material':screen.visual.material.name,'display_emissive_factor':emission.tolist(),
        'key_count':len(keys),'toggle_count':len(toggles),
        'single_shared_asset_states':['remembered','present'],
        'pass':screen.visual.material.name=='Display' and bool(np.any(emission>0)) and len(keys)==24 and len(toggles)==3}
    report['pass']=report['pass'] and report['console_parts']['pass'] and report['display_fit']['pass']
    (HERE/'verify.json').write_text(json.dumps(report,indent=2)+'\n')
    if not report['pass']:raise SystemExit('Console display or controls contract failed')
    print('Console display emission and separate controls PASS')


if __name__=='__main__':main()
