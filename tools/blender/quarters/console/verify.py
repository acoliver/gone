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
    _,key=scene.graph['Display']; screen=scene.geometry[key]
    emission=np.asarray(screen.visual.material.emissiveFactor)
    keys=sorted(n for n in scene.graph.nodes_geometry if n.startswith('Key_'))
    toggles=sorted(n for n in scene.graph.nodes_geometry if n.startswith('Toggle_'))
    report['console_parts']={'display_material':screen.visual.material.name,'display_emissive_factor':emission.tolist(),
        'key_count':len(keys),'toggle_count':len(toggles),
        'single_shared_asset_states':['remembered','present'],
        'pass':screen.visual.material.name=='Display' and bool(np.any(emission>0)) and len(keys)==24 and len(toggles)==3}
    report['pass']=report['pass'] and report['console_parts']['pass']
    (HERE/'verify.json').write_text(json.dumps(report,indent=2)+'\n')
    if not report['pass']:raise SystemExit('Console display or controls contract failed')
    print('Console display emission and separate controls PASS')


if __name__=='__main__':main()
