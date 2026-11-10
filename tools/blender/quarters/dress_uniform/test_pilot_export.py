"""Inspect actual pilot exports for frozen geometry, pivots and all retained gates."""
import argparse
import json
from pathlib import Path
import struct
import sys

import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tunic_contacts import triangle_signature


def meshes(path):
    scene = trimesh.load(path, force='scene', process=False, merge_primitives=True)
    result = {}
    for name in scene.graph.nodes_geometry:
        transform, geometry = scene.graph[name]
        result[name] = scene.geometry[geometry].copy()
        result[name].apply_transform(transform)
    return result


def manifest(path):
    raw = path.read_bytes()
    length = struct.unpack_from('<I', raw, 12)[0]
    return json.loads(raw[20:20+length])


p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--out', type=Path, required=True)
p.add_argument('--baseline', type=Path, required=True)
a = p.parse_args()
original = manifest(a.baseline)
current = manifest(a.out/'candidate.glb')
nodes = {node['name']: node for node in original['nodes']}
assert set(nodes) == {node['name'] for node in current['nodes']}, 'Exported node names changed'
for node in current['nodes']:
    for field in ['translation', 'rotation', 'scale', 'matrix']:
        assert node.get(field) == nodes[node['name']].get(field), (node['name'], field, 'pivot changed')
before, after = meshes(a.baseline), meshes(a.out/'candidate.glb')
assert set(before) == set(after), 'Exported parts changed'
for name in before:
    old, new = before[name].triangles, after[name].triangles
    if name in ['TunicBody', 'Hemfringe']:
        def frozen(triangles):
            x, height, forward = triangles.transpose(2, 0, 1)
            strips = ((x > -.141) & (x < -.079)) | ((x > .130) & (x < .167))
            permitted = strips & (height < -.78) & (forward > -.015)
            return triangles[~permitted.any(1)]
        old, new = frozen(old), frozen(new)
    assert np.array_equal(triangle_signature(old), triangle_signature(new)), (name, 'frozen triangles changed')
r = json.loads((a.out/'finished.json').read_text())
assert r['pass13']['chest_patch']['repaired_ao'] >= .8
assert r['pass13']['hem_coverage']['authored_coverage'] >= .70
gates = json.loads((a.out/'gates.json').read_text())
assert {key for key, value in gates.items() if key.startswith('G') and not value['pass_gate']} == {'G3', 'G6'}
assert gates['G30']['value']['changed_intersections'] == 0
assert gates['armhole_opening']['pass_gap']
assert json.loads((a.out/'attachment-audit.json').read_text())['all_bases_within_2mm']
assert (a.out/'candidate.glb').read_bytes() == (a.out/'repeat.glb').read_bytes()
palette = json.loads(Path(__file__).with_name('target-colours.json').read_text())
for role, colour in palette['colours'].items():
    step = palette['calibration']['roles'][role]['steps'][-1]
    assert np.array_equal(colour['linear'], step['albedo_linear']), (role, 'recorded albedo differs')
    assert np.max(np.abs(np.array(step['displayed_srgb_bytes'])-colour['srgb_bytes'])) <= 1, (role, 'display fit differs')
    if role != 'brass_brown':
        red, green, blue = colour['linear']
        assert blue > green > red, (role, 'wool/dust lost its blue cast')
print('PASS: exact node names/pivots and frozen nonselected geometry, repaired AO, retained gates/seating and repeat bytes')
