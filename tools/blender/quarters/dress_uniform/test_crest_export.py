"""Crest-only rebaking preserves all geometry, alpha and other material images."""
import argparse
from io import BytesIO
from pathlib import Path
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_shoulder_export import load, meshes, base_images
from tunic_contacts import triangle_signature


def image_bytes(gltf, binary):
    result = {}
    for image in gltf['images']:
        view = gltf['bufferViews'][image['bufferView']]
        start = view.get('byteOffset', 0)
        result[image['name']] = binary[start:start+view['byteLength']]
    return result


def verify(out, baseline):
    old, old_bin = load(baseline)
    new, new_bin = load(out/'candidate.glb')
    assert old['nodes'] == new['nodes'], 'Names, pivots or hierarchy changed'
    before, after = meshes(baseline), meshes(out/'candidate.glb')
    assert before.keys() == after.keys()
    for name in before:
        assert np.array_equal(triangle_signature(before[name].triangles), triangle_signature(after[name].triangles)), name
    old_base, new_base = base_images(old, old_bin), base_images(new, new_bin)
    for name in old_base:
        if name != 'TunicBody':
            assert old_base[name] == new_base[name], (name, 'unrelated base colour changed')
    old_images, new_images = image_bytes(old, old_bin), image_bytes(new, new_bin)
    changed = set(old_images.values())-set(new_images.values())
    added = set(new_images.values())-set(old_images.values())
    assert len(changed) == len(added) == 1, 'Only the body base texture may change'
    a = np.array(Image.open(BytesIO(changed.pop())).convert('RGBA'))
    b = np.array(Image.open(BytesIO(added.pop())).convert('RGBA'))
    assert a.shape == b.shape == (4096, 4096, 4)
    np.testing.assert_array_equal(a[:, :, 3], b[:, :, 3])
    assert old['materials'] == new['materials'], 'Material roles or parameters changed'
    assert (out/'candidate.glb').read_bytes() == (out/'repeat.glb').read_bytes()
    np.testing.assert_array_equal(np.concatenate([m.bounds for m in before.values()]),
                                  np.concatenate([m.bounds for m in after.values()]))
    print('PASS: exact geometry, names, pivots, bounds, alpha, normal maps, material roles and all non-body textures; repeat bytes')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    args = parser.parse_args()
    verify(args.out.resolve(), args.baseline.resolve())
