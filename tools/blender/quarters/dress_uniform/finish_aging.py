"""Finish tunic cards and export a scratch candidate, never the game asset."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from aging_cards import finish_cards
from age_tunic import save_checkpoint
from common import export


def finish(out):
    bpy.ops.wm.open_mainfile(filepath=str(out / 'baked.blend'))
    record = json.loads(bpy.context.scene['tunic5_record'])
    body = bpy.data.objects['TunicBody']
    body.data.calc_loop_triangles()
    np.savez_compressed(out / 'game-sheet.npz',
                        vertices=np.array([body.matrix_world @ v.co for v in body.data.vertices]),
                        faces=np.array([t.vertices[:] for t in body.data.loop_triangles]),
                        uv=np.array([[body.data.uv_layers[0].data[i].uv[:] for i in t.loops]
                                     for t in body.data.loop_triangles]))
    record = finish_cards(out, record)
    for obj in bpy.context.scene.objects:
        for modifier in list(obj.modifiers):
            if modifier.type == 'COLLISION':
                obj.modifiers.remove(modifier)
    save_checkpoint(out, 'finished', record)
    export(out / 'candidate.glb')
    bpy.ops.wm.open_mainfile(filepath=str(out / 'finished.blend'))
    export(out / 'repeat.glb')
    identical = (out / 'candidate.glb').read_bytes() == (out / 'repeat.glb').read_bytes()
    (out / 'repeat.json').write_text(json.dumps({'byte_identical': identical})+'\n')
    if not identical:
        raise ValueError('Saved blend re-export changed GLB bytes')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, default=ROOT / 'tmp/age/tunic6/main')
    a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    finish(a.out.resolve())
