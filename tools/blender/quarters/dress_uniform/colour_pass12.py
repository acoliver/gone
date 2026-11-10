"""Bake tunic aging into the scratch candidate's own exported materials."""
import argparse
import json
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from age_tunic import save_checkpoint
from baked_age_colour import apply_colours
from common import export


def finish(base, out, palette):
    out.mkdir(parents=True, exist_ok=True)
    (out/'textures').mkdir(exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(base/'finished.blend'))
    record = json.loads(bpy.context.scene['tunic5_record'])
    from fallen_wear import lost_area
    opacity = bpy.data.images.load(str(base/'textures/tunic_opacity.png'), check_existing=False)
    alpha_loss = lost_area(bpy.data.objects['TunicBody'], opacity)
    previous = record['heap']['stress_wear_area_m2']
    record['heap']['sheet_opacity_loss_area_m2'] = alpha_loss
    record['heap']['previous_stress_only_area_m2'] = previous
    record['heap']['lost_area_m2'] += alpha_loss-previous
    expected = record['heap']['lost_area_m2']*.0035/record['heap']['packing_fraction']
    record['heap']['expected_volume_m3'] = expected
    record['heap']['ratio'] = record['heap']['measured_volume_m3']/expected
    record['pass12']['colour'] = apply_colours(out, record, palette)
    save_checkpoint(out, 'finished', record)
    export(out/'candidate.glb')
    bpy.ops.wm.open_mainfile(filepath=str(out/'finished.blend'))
    export(out/'repeat.glb')
    identical = (out/'candidate.glb').read_bytes() == (out/'repeat.glb').read_bytes()
    (out/'repeat.json').write_text(json.dumps(dict(byte_identical=identical))+'\n')
    if not identical:
        raise ValueError('Saved baked-colour scene does not export identical bytes')
    import shutil
    shutil.copyfile(base/'game-sheet.npz', out/'game-sheet.npz')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--palette', type=Path, default=ROOT/'tmp/age/tunic12/target-colours.json')
    a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    finish(a.base.resolve(), a.out.resolve(), a.palette.resolve())
