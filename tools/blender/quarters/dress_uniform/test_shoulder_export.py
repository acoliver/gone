"""Check shoulder-only geometry, unchanged pigments and the retained pilot gates."""
import argparse
import json
from pathlib import Path
import struct
import sys

import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tunic_contacts import triangle_signature


def load(path):
    raw = path.read_bytes()
    length = struct.unpack_from('<I', raw, 12)[0]
    return json.loads(raw[20:20+length]), raw[28+length:]


def base_images(gltf, binary):
    result = {}
    for material in gltf['materials']:
        pbr = material['pbrMetallicRoughness']
        if 'baseColorTexture' not in pbr:
            result[material['name']] = pbr.get('baseColorFactor')
            continue
        source = gltf['textures'][pbr['baseColorTexture']['index']]['source']
        view = gltf['bufferViews'][gltf['images'][source]['bufferView']]
        start = view.get('byteOffset', 0)
        result[material['name']] = binary[start:start+view['byteLength']]
    return {node['name']: {tuple(value) if isinstance(value, list) else value
                           for p in gltf['meshes'][node['mesh']]['primitives']
                           for value in [result[gltf['materials'][p['material']]['name']]]}
            for node in gltf['nodes'] if 'mesh' in node}


def meshes(path):
    scene = trimesh.load(path, force='scene', process=False, merge_primitives=True)
    result = {}
    for name in scene.graph.nodes_geometry:
        transform, geometry = scene.graph[name]
        mesh = scene.geometry[geometry].copy()
        mesh.apply_transform(transform)
        result[name] = mesh
    return result


def verify(out, baseline):
    old, old_binary = load(baseline)
    current, binary = load(out/'candidate.glb')
    nodes = {node['name']: node for node in old['nodes']}
    assert set(nodes) == {node['name'] for node in current['nodes']}
    for node in current['nodes']:
        for field in ['translation', 'rotation', 'scale', 'matrix']:
            assert node.get(field) == nodes[node['name']].get(field), (node['name'], field)
    assert base_images(old, old_binary) == base_images(current, binary), 'Base colour / alpha bytes changed'
    for node in current['nodes']:
        if 'mesh' not in node:
            continue
        previous = old['meshes'][nodes[node['name']]['mesh']]['primitives']
        modes = {old['materials'][p['material']]['name']: old['materials'][p['material']].get('alphaMode', 'OPAQUE')
                 for p in previous}
        for primitive in current['meshes'][node['mesh']]['primitives']:
            material = current['materials'][primitive['material']]
            mode = material.get('alphaMode', 'OPAQUE')
            soft = material['name'] in ['WoolCutEdgeShoulderSoft', 'WoolFringeShoulderSoft']
            assert mode == ('BLEND' if soft else modes[material['name']]), (node['name'], material['name'])
    assert Path(__file__).with_name('target-colours.json').read_bytes() == (out/'target-colours.json').read_bytes()
    before, after = meshes(baseline), meshes(out/'candidate.glb')
    assert set(before) == set(after)
    for name in before:
        a, b = before[name].triangles, after[name].triangles
        assert len(a) == len(b), (name, 'triangle count changed')
        if name in ['TunicBody', 'Longwoolfringe', 'Seamallowance']:
            def frozen(triangles):
                x, height, _ = triangles.transpose(2, 0, 1)
                return triangles[~((x > .14) & (height > -.35)).any(1)]
            a, b = frozen(a), frozen(b)
        assert np.array_equal(triangle_signature(a), triangle_signature(b)), (name, 'geometry changed outside shoulder')
    record = json.loads((out/'finished.json').read_text())
    assert record['pass14']['tip_droop_m'] >= .003
    assert record['pass14']['curl_height_m'] <= .004
    gates = json.loads((out/'gates.json').read_text())
    assert {k for k, v in gates.items() if k.startswith('G') and not v['pass_gate']} == {'G3', 'G6'}
    assert gates['G5']['value'] >= .30
    assert gates['G30']['value']['changed_intersections'] == 0
    assert gates['armhole_opening']['pass_gap']
    old_gates = json.loads(Path(__file__).with_name('pilot-gates.json').read_text())
    for key in [k for k in old_gates if k.startswith('G')]:
        assert gates[key]['threshold'] == old_gates[key]['threshold'], (key, 'threshold changed')
    assert json.loads((out/'attachment-audit.json').read_text())['all_bases_within_2mm']
    assert (out/'candidate.glb').read_bytes() == (out/'repeat.glb').read_bytes()
    bounds = trimesh.util.concatenate(list(after.values())).bounds
    previous_bounds = trimesh.util.concatenate(list(before.values())).bounds
    np.testing.assert_array_equal(bounds, previous_bounds)
    spans = np.ptp(bounds, axis=0)
    assert spans[1] > .94 and spans[1] > max(spans[0], spans[2]), bounds
    print('PASS: shoulder-only geometry; exact names/pivots, colour/alpha PNG bytes and palette; unchanged thresholds; G4/G5/G30/seating; Y-up and repeat bytes')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--baseline', type=Path, required=True)
    a = p.parse_args()
    verify(a.out.resolve(), a.baseline.resolve())
