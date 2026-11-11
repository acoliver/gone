"""Independently inspect exported glTF coordinates, materials and frozen triangles."""
import argparse
import json
from pathlib import Path
import struct
import sys

import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tunic_contacts import triangle_signature
from export_detail_metrics import material_signature, medal_metrics


def document(path):
    raw = path.read_bytes()
    size = struct.unpack_from('<I', raw, 12)[0]
    return json.loads(raw[20:20 + size]), raw, size + 28


def accessor(doc, raw, binary, index):
    source = doc['accessors'][index]
    view = doc['bufferViews'][source['bufferView']]
    dtype = np.dtype({5121: 'u1', 5123: '<u2', 5125: '<u4', 5126: '<f4'}[source['componentType']])
    dimensions = 1 if source['type'] == 'SCALAR' else int(source['type'][-1])
    return np.ndarray((source['count'], dimensions), dtype=dtype, buffer=raw,
                      offset=binary + view.get('byteOffset', 0) + source.get('byteOffset', 0),
                      strides=(view.get('byteStride', dimensions * dtype.itemsize), dtype.itemsize))


def meshes(path):
    scene = trimesh.load(path, force='scene', process=False, merge_primitives=True)
    result = {}
    for name in scene.graph.nodes_geometry:
        transform, geometry = scene.graph[name]
        result[name] = scene.geometry[geometry].copy()
        result[name].apply_transform(transform)
    return result


def inspect(directory, baseline, repeats):
    result = {}
    for state, suffix in [('remembered', ''), ('present', '_aged')]:
        filename = f'dress_uniform{suffix}.glb'
        path = directory / filename
        doc, raw, binary = document(path)
        before, after = meshes(baseline / filename), meshes(path)
        assert set(before) == set(after), 'Node hierarchy changed'
        old_doc, old_raw, old_binary = document(baseline / filename)
        old_nodes = {node['name']: node for node in old_doc['nodes']}
        for node in doc['nodes']:
            for field in ['translation', 'rotation', 'scale', 'matrix']:
                assert node.get(field) == old_nodes[node['name']].get(field), (node['name'], 'Pivot changed')
        for name in before:
            if name not in ['Buttons', 'Placket', 'Medal']:
                np.testing.assert_array_equal(triangle_signature(before[name].triangles), triangle_signature(after[name].triangles))
                old_node = next(node for node in old_doc['nodes'] if node['name'] == name)
                new_node = next(node for node in doc['nodes'] if node['name'] == name)
                old_primitives = old_doc['meshes'][old_node['mesh']]['primitives']
                new_primitives = doc['meshes'][new_node['mesh']]['primitives']
                assert len(old_primitives) == len(new_primitives)
                for old, new in zip(old_primitives, new_primitives):
                    assert set(old['attributes']) == set(new['attributes']), (name, 'Vertex channels changed')
                    for channel, index in old['attributes'].items():
                        np.testing.assert_array_equal(accessor(old_doc, old_raw, old_binary, index),
                                                      accessor(doc, raw, binary, new['attributes'][channel]),
                                                      err_msg=f'{name}: frozen {channel} changed')
                    expected = material_signature(old_doc, old_raw, old_binary, old_doc['materials'][old['material']])
                    actual = material_signature(doc, raw, binary, doc['materials'][new['material']])
                    assert expected == actual, (name, 'Unrelated material or texture changed')
        for name in ['Placket', 'Buttons']:
            old_node = next(node for node in old_doc['nodes'] if node['name'] == name)
            new_node = next(node for node in doc['nodes'] if node['name'] == name)
            old, = old_doc['meshes'][old_node['mesh']]['primitives']
            new, = doc['meshes'][new_node['mesh']]['primitives']
            expected = material_signature(old_doc, old_raw, old_binary, old_doc['materials'][old['material']])
            actual = material_signature(doc, raw, binary, doc['materials'][new['material']])
            if suffix:
                # Only the rebuilt row's base-colour atlases are intentionally rebaked.
                for signature in [expected, actual]:
                    signature.pop('name')
                    signature['pbrMetallicRoughness'].pop('baseColorTexture')
            assert expected == actual, (state, name, 'Non-bake material properties changed')
        geometry = np.vstack([mesh.vertices for mesh in after.values()])
        count = sum(len(mesh.faces) for mesh in after.values())
        assert count <= (20652 if suffix else 14999)
        assert np.ptp(geometry[:, 1]) > np.ptp(geometry[:, 2])
        assert abs(after['Hanger'].bounds[1, 1]) < .001
        assert all(after[name].vertices[:, 2].mean() > 0 for name in ['Buttons', 'Medal', 'RibbonBar'])
        button_mesh = after['Buttons'].copy()
        button_mesh.merge_vertices(merge_tex=True, merge_norm=True)
        buttons = sorted(button_mesh.split(only_watertight=False), key=lambda m: -m.vertices[:, 1].mean())
        assert len(buttons) == 8
        centers = np.array([mesh.vertices.mean(0) for mesh in buttons])
        np.testing.assert_allclose(centers[:, 1], np.linspace(-.180, -.850, 8), atol=.0001)
        diameters = [float(np.linalg.norm(mesh.vertices[:, None] - mesh.vertices[None, :], axis=2).max()) for mesh in buttons]
        assert all(abs(diameter - .014) < .0001 for diameter in diameters)
        metal = next(mesh for mesh in doc['meshes'] if mesh['name'] == 'Medal')
        assert len(metal['primitives']) == 3
        material_names = []
        for primitive in metal['primitives']:
            material = doc['materials'][primitive['material']]
            material_names.append(material['name'])
            attributes = primitive['attributes']
            colours = accessor(doc, raw, binary, attributes['COLOR_0'])
            if material['name'] == 'RibbonFabric':
                np.testing.assert_allclose(colours[:, :3], np.tile([.4, .025, .045], (len(colours), 1)), atol=1e-7)
            else:
                np.testing.assert_array_equal(colours, np.ones_like(colours))
            for key, index in attributes.items():
                if key.startswith('TEXCOORD'):
                    uv = accessor(doc, raw, binary, index)
                    assert np.isfinite(uv).all() and uv.min() >= -1e-6 and uv.max() <= 1 + 1e-6, (state, material['name'], key)
            pbr = material['pbrMetallicRoughness']
            if material['name'].startswith('MedalEnamel'):
                red, green, blue = pbr['baseColorFactor'][:3]
                assert blue > green > red and blue > red * 4
                assert abs(pbr['roughnessFactor'] - (.38 if suffix else .22)) < 1e-6
                assert abs(pbr.get('metallicFactor', 1)) < 1e-6
        repeat = repeats / filename
        assert raw == repeat.read_bytes(), (state, 'Saved source export is not byte-identical')
        result[state] = dict(triangles=count, button_diameters_m=diameters,
                             body_bounds_game_xyz_m=after['TunicBody'].bounds.tolist(),
                             overall_bounds_game_xyz_m=[geometry.min(0).tolist(), geometry.max(0).tolist()],
                             up='+Y', front='+Z', medal_materials=material_names, medal=medal_metrics(after['Medal']),
                             unrelated_materials_and_embedded_textures_exact=True, unrelated_vertex_channels_exact=True,
                             unchanged_pivots_and_other_triangles=True, byte_identical_saved_source_export=True)
    return result


def finish_preservation(directory, before):
    result = {}
    for filename in ['dress_uniform.glb', 'dress_uniform_aged.glb']:
        old, old_raw, old_binary = document(before / filename)
        new, new_raw, new_binary = document(directory / filename)
        if filename == 'dress_uniform.glb':
            assert old_raw == new_raw, 'Remembered export changed'
        else:
            brass, = [mat for mat in old['materials'] if mat['name'] == 'Medal_DullBrownBrass']
            pbr = brass['pbrMetallicRoughness']
            np.testing.assert_allclose([pbr['metallicFactor'], pbr['roughnessFactor']], [.15, .94], atol=1e-7)
            pbr.update(metallicFactor=float(np.float32(.55)), roughnessFactor=float(np.float32(.58)))
            assert old == new, 'Change outside the two Present medal brass finish factors'
            assert old_raw[old_binary:] == new_raw[new_binary:], 'Geometry, vertex channels or image bytes changed'
        result[filename] = dict(all_geometry_vertex_channels_and_images_exact=True,
                                every_other_material_property_exact=True,
                                remembered_bytes_exact=filename == 'dress_uniform.glb')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exports', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--repeats', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--finish-baseline', type=Path)
    args = parser.parse_args()
    result = inspect(args.exports, args.baseline, args.repeats)
    if args.finish_baseline:
        result['finish_preservation'] = finish_preservation(args.exports, args.finish_baseline)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print('PASS: independent trimesh/glTF dimensions, orientation, budgets, materials, UVs, colours and repeat bytes')
