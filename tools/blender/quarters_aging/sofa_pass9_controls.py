"""Forty-frame proof of the released-boxing back cover before production."""
import argparse
import json
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cloth_metrics import save_surface
from sofa_full_decay import ROOT, initialize
from sofa_pass8 import contacts
from sofa_pass8_finish import initial_contacts
from sofa_pass8_solver import cloth, solve
from sofa_pass9 import prepare_part
from sofa_pass9_physics import tune


def control(out):
    initialize()
    obj, detail, _, pins = prepare_part('BackCushion_C', out)
    initial = initial_contacts(obj, contacts())
    mod, settings = cloth(obj, detail['reference_vertices'], frames=2400, quality=30, pins=pins)
    tune(obj, mod, settings, 'backs')
    result = solve(obj, mod, out, 'C1-side-release', frames=40, settle=False)
    sample = result['surface_samples']['20']
    ratios = [v['area_ratio'] for v in result['surface_samples'].values()]
    proof = {'frame20_sharp_share': sample['dihedral_over_30_share'], 'sharp_limit': .05,
             'area_ratio_range': [min(ratios), max(ratios)], 'area_limits': [.97, 1.03],
             'initial_contacts': initial, 'settings': settings, 'side_releases': detail['side_boxing_release'],
             'pass': sample['dihedral_over_30_share'] <= .05 and all(abs(v-1) <= .03 for v in ratios) and result['pass']}
    save_surface(bpy.data.objects['BackCushion_C_Residue'], out/'control-back-residue.npz')
    previous = json.loads((ROOT/'tmp/age/pass8/controls.json').read_text())
    previous['pass9_volume_loss_control'] = proof
    previous['pass'] = previous['pass'] and proof['pass']
    (out/'controls.json').write_text(json.dumps(previous, indent=2)+'\n')
    print('PASS 9 BACK CONTROL', json.dumps(proof), flush=True)
    if not previous['pass']:
        raise ValueError('Pass-9 early back control failed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT/'tmp/age/pass9')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    args.out.mkdir(parents=True, exist_ok=True)
    control(args.out)
