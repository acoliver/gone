"""Inspect the real saved-scene exports, including wool alpha-scissor semantics."""
import argparse
import io
import json
from pathlib import Path
import struct

import numpy as np
from PIL import Image

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--out', type=Path, required=True)
a = p.parse_args()
record = json.loads((a.out/'finished.json').read_text())
assert record['opacity']['stress_wear']['through_texels'] == 0, 'Pass12 must not perforate the broad torso'
raw = (a.out/'candidate.glb').read_bytes()
assert raw == (a.out/'repeat.glb').read_bytes(), 'Reloaded scene changes exported bytes'
length = struct.unpack_from('<I', raw, 12)[0]
gltf = json.loads(raw[20:20+length])
base = 20+length+8


def texture(material):
    index = material['pbrMetallicRoughness']['baseColorTexture']['index']
    source = gltf['textures'][index]['source']
    view = gltf['bufferViews'][gltf['images'][source]['bufferView']]
    start = base+view.get('byteOffset', 0)
    return np.array(Image.open(io.BytesIO(raw[start:start+view['byteLength']])).convert('RGBA'))


body = next(m for m in gltf['materials'] if m['name'].startswith('TunicBody_Baked'))
assert body['alphaMode'] == 'MASK', 'Baked wool must retain alpha scissoring, not stochastic blending'
assert body['normalTexture']['texCoord'] == body['pbrMetallicRoughness']['baseColorTexture']['texCoord']
wool = texture(body)
opaque = wool[:, :, 3] >= 128
assert opaque.any() and (~opaque).any(), 'The body must retain both cloth and its broken edge mask'
colour = wool[:, :, :3][opaque]
assert np.all(colour[:, 2] >= colour[:, 1]) and np.all(colour[:, 1] >= colour[:, 0]), 'Wool acquired a green hue'
for material in gltf['materials']:
    fine_fringe = material['name'].startswith('WoolFringe') and 'SurvivingYarn' not in material['name']
    if fine_fringe or material['name'].startswith('Loose pale wool'):
        assert material['alphaMode'] == 'MASK', 'Fine wool tufts must preserve scissor semantics'
        pixels = texture(material)
        assert np.sum((pixels[:, :, 3] > 0) & (pixels[:, :, 3] < 255)) > 1000
        if material['name'].startswith('Loose pale wool'):
            root = pixels[-9, :, 3] >= 128
            edges = np.flatnonzero(np.diff(np.r_[False, root, False]))
            assert len(edges) == 8, 'The actual mound material must export four resolved bundles, not the fine edge atlas'
    if 'DullBrownBrass' in material['name']:
        pixels = texture(material)[:, :, :3]
        assert np.mean(pixels[:, :, 0]) > np.mean(pixels[:, :, 2]), 'Brass must be brown, not blue wool'
print('PASS: byte-identical reload export, baked grey-blue wool, matching normal UVs, scissored fine tufts and brown brass')
