"""Apply physical-station edge losses to the settled game and dense sheets."""
import argparse
import json
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from age_tunic import save_checkpoint
from lip_arclength import refine_physical_lips
from bake_down import boundary_hausdorff
from cloth_metrics import lip_lift


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out/'textures').mkdir(exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(a.base.resolve()/'baked.blend'))
    record = json.loads(bpy.context.scene['tunic5_record'])
    body, dense = bpy.data.objects['TunicBody'], bpy.data.objects['TunicBody_Dense']
    record['pass12']['physical_lips'] = dict(game=refine_physical_lips(body), dense=refine_physical_lips(dense))
    record['reduction']['TunicBody']['boundary_hausdorff_upper_m'] = boundary_hausdorff(dense, body)
    record['lip_lift'] = lip_lift(body)
    save_checkpoint(a.out.resolve(), 'baked', record)
