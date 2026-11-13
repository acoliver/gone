"""Reduce fitted atlases only when the weakest exported UV direction stays >=600 px/m."""
import argparse
import json

import numpy as np
from PIL import Image
import trimesh

from atlas_gates import uv_metrics
from map_library import PROPS, ROOT, material_role, triangle_samples


def density_after_resize(minimum, original, target):
    if target <= 0 or target > original:
        raise ValueError('target must be positive and no larger than the current atlas')
    density = minimum*target/original
    if density < 600:
        raise ValueError(f'{target} atlas would have {density:.3f} px/m, below 600')
    return density


def resize(prop, resolution):
    directory = ROOT / f'assets/props/quarters/steel/{prop}'
    metadata = json.loads((directory/'mapping.json').read_text())
    original = metadata['atlas_size']
    model = ROOT / f'assets/props/quarters/{prop}.glb'
    uv = uv_metrics(model, original)
    minimum = density_after_resize(uv['density_min'], original, resolution)
    paths = sorted(directory.glob('*.png'))
    for path in paths:
        if Image.open(path).size != (original, original):
            raise ValueError(f'atlas size disagrees with mapping: {path}')
    occupied = np.zeros((resolution, resolution), bool)
    scene = trimesh.load(model, force='scene', process=False)
    for mesh in scene.geometry.values():
        if material_role(mesh.visual.material.name) == 'preserved':
            continue
        for triangle in mesh.visual.uv[mesh.faces]:
            x, y, _ = triangle_samples(triangle, resolution)
            occupied[y, x] = True
    for path in paths:
        image = Image.open(path)
        image = image.resize((resolution, resolution), Image.Resampling.NEAREST if path.stem == 'regions' else Image.Resampling.LANCZOS)
        if path.stem.endswith('_normal'):
            normal = np.asarray(image, float)/255*2-1
            normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
            image = Image.fromarray(np.uint8(np.round((normal*.5+.5)*255)))
        image.save(path)
    scale = resolution/original
    metadata['atlas_size'] = resolution
    metadata['texels_per_metre'] *= scale
    metadata['density_range'] = [value*scale for value in metadata['density_range']]
    metadata['occupied_texels'] = int(occupied.sum())
    metadata['exported_uv_density_min'] = minimum
    metadata['resize'] = dict(from_resolution=original, to_resolution=resolution,
                              minimum_exported_pixels_per_metre=minimum,
                              geometry_and_uvs_unchanged=True)
    (directory/'mapping.json').write_text(json.dumps(metadata, indent=2)+'\n')
    print(prop, original, '->', resolution, 'minimum px/m', minimum, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prop', choices=PROPS, required=True)
    parser.add_argument('--resolution', type=int, required=True)
    args = parser.parse_args()
    resize(args.prop, args.resolution)
