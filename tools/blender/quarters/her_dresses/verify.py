"""Run shared clothing gates and fixed-doorway visibility with dress-local scratch."""
import argparse
import json
from pathlib import Path
import sys

import trimesh

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'her_jacket'))
import verify as shared
from dress_visibility import doorway_fractions,MINIMUM_VISIBLE_AREA


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prop',choices=['her_dresses'])
    parser.add_argument('--state',choices=['remembered','aged'])
    args=parser.parse_args()
    shared.SCRATCH=HERE.parents[3]/'tmp/clothes2'
    _,supports=shared.load(shared.ASSETS/'wardrobe.glb')
    wardrobe=trimesh.util.concatenate(list(supports.values()))
    result={}
    for state in [args.state] if args.state else ['remembered','aged']:
        record=shared.state_report(args.prop,state)
        _,parts=shared.load(shared.ASSETS/f'her_dresses{"_aged" if state=="aged" else ""}.glb')
        fractions=doorway_fractions(parts,wardrobe,shared.tunic(state))
        record['doorway_visible_projected_area']=fractions
        record['doorway_visible_area_minimum']=MINIMUM_VISIBLE_AREA
        record['pass']=record['pass'] and all(f>=MINIMUM_VISIBLE_AREA for f in fractions.values())
        result[state]=record
    result['pass']=all(record['pass'] for record in result.values())
    output=json.dumps(result,indent=2)+'\n'
    (HERE/'verify.json').write_text(output)
    print(output,flush=True)
    if not result['pass']:raise SystemExit('Clothing gates failed')


if __name__=='__main__':main()
