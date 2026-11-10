"""Bake production Naleya quads onto key tops in both steel finish atlases.

Run map_library.py first against the refitted saved source, then this script.
No new material role or runtime overlay is needed: these are pale inlaid marks
in the existing keycap UVs, with flat dielectric ink in both state textures.
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
import trimesh

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ATLAS = ROOT / 'assets/props/quarters/steel/console'


def bake():
    document = json.loads((ROOT / 'tmp/mat2/console/faces.json').read_text())
    legends = json.loads((HERE / 'legends.json').read_text())
    mapping = json.loads((ATLAS / 'mapping.json').read_text())
    scene = trimesh.load(ROOT / 'assets/props/quarters/console.glb', force='scene')
    resolution = mapping['atlas_size']
    masks = Image.new('L', (resolution, resolution))
    records = []
    for legend in legends['keys']:
        key = legend['key']
        faces = [face for face in document['faces'] if face['part'] == key and face['normal'][2] > .9]
        def area(face):
            triangles = np.array(face['triangles'])
            return np.linalg.norm(np.cross(triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0]), axis=1).sum()/2
        face = max(faces, key=area)
        points = np.array(face['triangles']).reshape(-1, 3)
        frame, _ = scene.graph[key]
        gltf = points[:, [0, 2, 1]] * [1, 1, -1]
        local = trimesh.transform_points(gltf, np.linalg.inv(frame))
        xy = local[:, [0, 2]] * [1, -1]
        tex = np.array(face['uv']).reshape(-1, 2)
        affine = np.linalg.lstsq(np.column_stack([xy, np.ones(len(xy))]), tex, rcond=None)[0]
        assert np.max(np.abs(np.column_stack([xy, np.ones(len(xy))]) @ affine - tex)) < 1e-6
        quads = np.array(legend['quads'])
        low, high = quads.reshape(-1, 2).min(0), quads.reshape(-1, 2).max(0)
        physical = (quads - (low + high)/2) * (.024 / (high[1] - low[1]))
        assert np.max(np.abs(physical[..., 0])) < .073/2 - .004
        assert np.max(np.abs(physical[..., 1])) < .034/2 - .004
        uv = np.column_stack([physical.reshape(-1, 2), np.ones(physical.size//2)]) @ affine
        pixels = uv * [resolution, -resolution] + [0, resolution]
        low = np.floor(pixels.min(0)).astype(int) - 2
        high = np.ceil(pixels.max(0)).astype(int) + 2
        size = high - low + 1
        mask = Image.new('L', tuple(size*4))
        draw = ImageDraw.Draw(mask)
        for quad in pixels.reshape(-1, 4, 2):
            draw.polygon([tuple(p) for p in (quad - low)*4], fill=255)
        mask = mask.resize(tuple(size), Image.Resampling.LANCZOS)
        masks.paste(mask, tuple(low))
        ink = np.asarray(mask)
        y, x = np.unravel_index(np.argmax(ink), ink.shape)
        records.append(dict(key=key, input=legend['input'], sign=legend['sign'],
                            key_top_face=face['id'], height_m=.024, ink_texels=int((ink > 127).sum()),
                            ink_probe_pixel=[int(x + low[0]), int(y + low[1])]))
    alpha = np.asarray(masks, float)[..., None]/255
    for state in ('as_built', 'aged'):
        for kind, colour in [('albedo', [228, 233, 222] if state == 'as_built' else [194, 200, 184]),
                             ('normal', [128, 128, 255]), ('orm', [255, 185, 0])]:
            path = ATLAS / f'{state}_{kind}.png'
            values = np.asarray(Image.open(path).convert('RGB'), float)
            Image.fromarray(np.uint8(np.round(values*(1-alpha)+np.array(colour)*alpha))).save(path)
    mapping['native_legends'] = records
    mapping['legend_source'] = 'tools/blender/quarters/console/legends.json via production Naleya'
    (ATLAS / 'mapping.json').write_text(json.dumps(mapping, indent=2)+'\n')
    print('Baked native legends on 24 key tops in both state albedo/normal/ORM atlases')


if __name__ == '__main__':
    bake()
