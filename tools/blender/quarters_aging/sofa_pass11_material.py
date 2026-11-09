"""Broad geometric gashes receive edge fraying, not extra scattered alpha holes."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from opacity_bake import value_noise
from sofa_decay_finish import detail, throw_detail
from sofa_decay_policy import ORDER
from sofa_full_decay import ROOT, checkpoint
from sofa_pass10_material import replace_pixels, tan_residue
from sofa_pass10_opacity import opacity


def frayed_coverage(points, distances, roots, seed, opening=None):
    noise = .35*value_noise(roots, .004, seed)+.65*value_noise(roots, .0015, seed+1)
    return distances >= .0017+.0035*noise


def finish(source, out):
    detail(source, out)
    throw_detail(out/'detailed.blend', out)
    record = json.loads(bpy.context.scene['sofa_decay_record'])
    for name in [*ORDER, 'Throw']:
        obj = bpy.data.objects[name+'_GameContact']
        seed = 9967 if name == 'Throw' else record['pass11']['parts'][name]['gash']['spec']['seed']
        alpha, report = opacity(obj, out/'textures'/name.lower()/'pass11_opacity.png', seed,
                                coverage=frayed_coverage, opening_factory=lambda _: None)
        report['method'] = 'edge-only multiscale fraying around physical openings; no added interior pinholes'
        shader = obj.data.materials[0].node_tree.nodes['Principled BSDF']
        image = shader.inputs['Base Color'].links[0].from_node.image
        pixels = np.array(image.pixels[:], dtype=np.float32).reshape(image.size[1], image.size[0], 4)
        pixels[:, :, 3] = np.array(alpha.pixels[:], dtype=np.float32).reshape(image.size[1], image.size[0], 4)[:, :, 0]
        replace_pixels(image, pixels)
        if name == 'Throw':
            record['throw']['materials']['opacity'] = report
        else:
            record['materials'][name]['cover']['opacity'] = report
            dense, low = [bpy.data.objects[name+'_'+level] for level in ['DenseResidue', 'Residue']]
            record['materials'][name]['residue'] = tan_residue(dense, low, out/'textures'/name.lower()/'residue')
    checkpoint(out, record, 'throw-detailed.blend')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'tmp/age/pass11/geometry.blend')
    parser.add_argument('--out', type=Path, default=ROOT/'tmp/age/pass11')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    finish(args.source, args.out)
