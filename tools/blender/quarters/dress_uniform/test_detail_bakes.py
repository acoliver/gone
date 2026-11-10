"""Check final-surface aging and the actual exported material/UV/image binding."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

import bpy
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import aging_support  # Establish the shared aging module path.
from baked_age_colour import aged_linear, raster_fields


def source_check(obj, palette):
    assert 'BakeUV' in obj.data.uv_layers, f'{obj.name}: missing bake coordinates'
    material = obj.data.materials[0]
    texture = material.node_tree.nodes['Principled BSDF'].inputs['Base Color'].links[0].from_node
    mapping = texture.inputs['Vector'].links[0].from_node
    assert mapping.type == 'UVMAP' and mapping.uv_map == 'BakeUV'
    image = texture.image
    width, height = image.size
    assert width == height
    masks = raster_fields(obj, width)
    if obj.name == 'Placket':
        rng = np.random.default_rng(9613 + sum(map(ord, obj.name)))
        masks[:, :, 4] = rng.random((width, width), dtype=np.float32)
        expected, _, _ = aged_linear(np.ones((height, width), np.float32), masks, palette)
        expected *= .995 + .01 * masks[:, :, 4:5]
    else:
        brown = np.array(palette['brass_brown']['linear'])
        expected = brown * .32 + (brown - brown * .32) * (.35 + .65 * masks[:, :, 3:4])
    expected = np.where(expected <= .0031308, expected * 12.92,
                        1.055 * expected ** (1 / 2.4) - .055)
    pixels = np.empty(width * height * 4, np.float32)
    image.pixels.foreach_get(pixels)
    actual = pixels.reshape(height, width, 4)[:, :, :3]
    # Saving the 8-bit PNG rounds each image-buffer channel to the nearest byte.
    error = float(np.max(abs(actual - expected)))
    assert error <= .5 / 255 + 1e-6, (obj.name, 'image was not baked from its final surface/UVs', error)
    return texture, error


def array(doc, raw, binary, index):
    item = doc['accessors'][index]
    view = doc['bufferViews'][item['bufferView']]
    dtype = np.dtype({5121: 'u1', 5123: '<u2', 5125: '<u4', 5126: '<f4'}[item['componentType']])
    count = 1 if item['type'] == 'SCALAR' else int(item['type'][-1])
    return np.ndarray((item['count'], count), dtype=dtype, buffer=raw,
                      offset=binary + view.get('byteOffset', 0) + item.get('byteOffset', 0),
                      strides=(view.get('byteStride', count * dtype.itemsize), dtype.itemsize))


def export_check(obj, path):
    raw = path.read_bytes()
    length = struct.unpack_from('<I', raw, 12)[0]
    doc, binary = json.loads(raw[20:20 + length]), length + 28
    node = next(node for node in doc['nodes'] if node['name'] == obj.name)
    primitive, = doc['meshes'][node['mesh']]['primitives']
    pbr = doc['materials'][primitive['material']]['pbrMetallicRoughness']
    info = pbr['baseColorTexture']
    uv_index = list(obj.data.uv_layers).index(obj.data.uv_layers['BakeUV'])
    assert info.get('texCoord', 0) == uv_index, (obj.name, 'exported material addresses wrong UV set')
    position = array(doc, raw, binary, primitive['attributes']['POSITION'])
    uv = array(doc, raw, binary, primitive['attributes'][f'TEXCOORD_{uv_index}'])
    exported = np.c_[position, uv]
    layer = obj.data.uv_layers['BakeUV']
    source = []
    for loop in obj.data.loops:
        p = obj.matrix_world @ obj.data.vertices[loop.vertex_index].co
        u, v = layer.data[loop.index].uv
        source.append([p.x, p.z, -p.y, u, 1 - v])
    source = np.unique(np.asarray(source), axis=0)
    for a, b in [(source, exported), (exported, source)]:
        for start in range(0, len(a), 128):
            distance = np.max(abs(a[start:start + 128, None] - b[None, :]), axis=2)
            assert distance.min(axis=1).max() < 1e-6, (obj.name, 'exported position/bake-UV correspondence changed')
    image = doc['images'][doc['textures'][info['index']]['source']]
    view = doc['bufferViews'][image['bufferView']]
    start = binary + view.get('byteOffset', 0)
    payload = raw[start:start + view['byteLength']]
    texture = obj.data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Base Color'].links[0].from_node
    expected = bytes(texture.image.packed_file.data)
    assert payload == expected, (obj.name, 'exported image differs from verified source bake')
    return dict(texcoord=uv_index, image_sha256=hashlib.sha256(payload).hexdigest(),
                uv_min=uv.min(0).tolist(), uv_max=uv.max(0).tolist(), source_corner_correspondence=True)


def check(source, exported, export_only=False):
    bpy.ops.wm.open_mainfile(filepath=str(source))
    palette = json.loads((HERE / 'target-colours.json').read_text())['colours']
    result = {}
    for name in ['Placket', 'Buttons']:
        obj = bpy.data.objects[name]
        result[name] = {}
        if not export_only:
            _, error = source_check(obj, palette)
            result[name]['max_linear_png_error'] = error
        result[name].update(export_check(obj, exported))
    print(json.dumps(result, indent=2))
    print('PASS: final-surface bake pixels and actual GLB material/UV/image correspondence')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=HERE / 'tunic-pilot.blend')
    parser.add_argument('--export', dest='exported', type=Path,
                        default=aging_support.ROOT / 'assets/props/quarters/dress_uniform_aged.glb')
    parser.add_argument('--export-only', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    result = check(args.source, args.exported, args.export_only)
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + '\n')
