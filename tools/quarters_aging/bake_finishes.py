"""Bake clean design paint and image-derived aged steel on one shared atlas."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

from colour import linear, srgb
from finish_fields import noise
from locker_swatches import aged_colour, load_swatches, paint_field, material_colours
from streak_sources import write_sources

ROOT = Path(__file__).resolve().parents[2]
DESIGN_ROI = (460, 440, 550, 600)


def design_paint():
    image = Image.open(ROOT / 'docs/art/quarters/sheets/storage_locker_module/hero.png').convert('RGB')
    region = np.asarray(image.crop(DESIGN_ROI), np.float32) / 255
    return srgb(np.median(linear(region), axis=(0, 1)))


def write_atlas(path, data, nearest):
    data = data[tuple(nearest)]
    Image.fromarray(np.uint8(np.round(np.clip(data, 0, 1) * 255))).save(path)


def bake(directory, fields):
    metadata = json.loads((directory / 'masks.json').read_text())
    geometry = np.asarray(Image.open(directory / 'geometry_masks.png'), np.float32) / 255
    weather = np.asarray(Image.open(directory / 'weather_masks.png'), np.float32) / 255
    arrays = np.load(fields)
    occupied, ownership = arrays['occupied'], arrays['ownership']
    p, n = arrays['position'][occupied], arrays['normal'][occupied]
    seed = metadata['seed']
    edge = -np.log(np.maximum(geometry[..., 2][occupied], 1e-8)) * .012
    fixture = np.full(len(p), 1., np.float32)
    hardware = np.isin(arrays['part_names'][arrays['part_index'][occupied]],
                       ['Rivets', 'Hinges', 'DoorVents', 'Handle', 'HandlePocket', 'KickPlate'])
    for source in metadata['sources']:
        lo, hi = np.array(source['bounds_blender'])
        fixture = np.minimum(fixture, np.linalg.norm(np.maximum(np.maximum(lo - p, p - hi), 0), axis=-1))
    distance = np.minimum(edge, fixture)
    flakes = noise(p, 84, seed + 1)
    grain = noise(p, 430, seed + 2)
    aged, corrosion, dust_colour, calibration = aged_colour(p, n, distance, geometry[..., 1][occupied], hardware, metadata['sources'], seed, edge)
    source_count = write_sources(directory / 'streak_sources.tres', metadata['sources'], seed)
    up = np.clip(n[:, 2], 0, 1)
    density = .80 + noise(p, 6, seed + 33) * .15 + np.exp(-edge / .035) * .14
    # AO cavities and the perimeter lip retain powder; raised bevels shed it.
    dust = np.clip(up ** 8 * (density + geometry[..., 1][occupied] * .12), 0, .97)
    paint = design_paint()
    steel = np.array([.72, .75, .77], np.float32)
    dark = np.array([.23, .265, .26], np.float32)
    owner = ownership[occupied]
    base = np.where((owner == 1)[:, None], paint, np.where((owner == 2)[:, None], steel, dark))
    nearest = distance_transform_edt(~occupied, return_distances=False, return_indices=True)
    region = np.zeros((*occupied.shape, 4), np.float32)
    region[occupied] = np.stack([distance <= .025, distance >= .060, owner == 2, np.ones(len(p))], -1)
    write_atlas(directory / 'region_masks.png', region, nearest)
    dust_atlas = np.zeros((*occupied.shape, 3), np.float32)
    dust_atlas[occupied] = dust_colour
    write_atlas(directory / 'aged_dust.png', dust_atlas, nearest)
    images, _ = load_swatches()
    paint_layer, oxide_layer = material_colours(p, n, images)
    paint_layer[hardware] = [.49, .52, .54]
    for name, layer in [('aged_paint.png', paint_layer), ('aged_oxide.png', oxide_layer)]:
        atlas = np.zeros((*occupied.shape, 3), np.float32)
        atlas[occupied] = layer
        write_atlas(directory / name, atlas, nearest)
    nearest_rust = distance_transform_edt(paint_field(images['loss']) >= .15, return_distances=False, return_indices=True)
    runoff = images['loss'][tuple(nearest_rust)]
    Image.fromarray(np.uint8(np.round(np.clip(runoff, 0, 1) * 255))).save(directory / 'aged_rust.png')
    for state in ('as_built', 'aged'):
        rust = corrosion if state == 'aged' else np.zeros_like(corrosion)
        powder = dust if state == 'aged' else np.zeros_like(dust)
        colour = aged.copy() if state == 'aged' else base.copy()
        if state == 'aged':
            pits = np.clip((grain - .60) * 4, 0, 1) * hardware
            colour *= (1 - pits * .65)[:, None]
        roughness = np.where(owner == 2, .30 + grain * .10, np.where(owner == 1, .35 + flakes * .20, .52))
        roughness = roughness * (1 - rust) + (.86 + grain * .12) * rust
        metallic = np.where(owner == 1, .02, .45) * (1 - rust)
        height = (owner == 1) * (1 - rust) * (grain - .5) * .00045
        height += -rust * (.00035 + grain * .0010)
        height += 4 * rust * (1 - rust) * .0012
        height -= (hardware if state == 'aged' else owner == 2) * np.maximum(grain - .55, 0) * (.003 if state == 'aged' else .00005)
        atlas_height = np.zeros_like(occupied, np.float32)
        atlas_height[occupied] = height
        atlas_height = atlas_height[tuple(nearest)]
        dy, dx = np.gradient(atlas_height)
        density = metadata['texels_per_metre']
        normals = np.stack([-dx * density, dy * density, np.ones_like(dx)], -1)
        normals /= np.linalg.norm(normals, axis=-1, keepdims=True)
        albedo = np.zeros((*occupied.shape, 4), np.float32)
        albedo[occupied] = np.column_stack([colour, rust])
        orm = np.zeros_like(albedo)
        orm[occupied] = np.column_stack([geometry[..., 0][occupied], roughness, metallic, powder])
        write_atlas(directory / f'{state}_albedo.png', albedo, nearest)
        write_atlas(directory / f'{state}_normal.png', np.dstack([normals * .5 + .5, np.ones_like(dx)]), nearest)
        write_atlas(directory / f'{state}_orm.png', orm, nearest)
    document = {'method': 'generated FLUX.2-klein class-conditioned pigment layers; physical broken edge loss and small blisters; derivative-sharpened coverage and hatch detail scans',
                'colour_source': 'art-source/quarters/locker/albedo-calibration.json',
                'swatches': {name: row['candidate'] for name, row in calibration['regions'].items()},
                'swatch_pixels_per_metre': 300, 'gravity_direction_prop': [0, -1, 0], 'gravity_source_count': source_count,
                'age_years': {'as_built': 0, 'aged': 1000}, 'seed': seed,
                'as_built_paint_srgb': paint.tolist(), 'design_roi_xyxy': DESIGN_ROI,
                'design_median_linear': linear(paint).tolist(),
                'channels': {'*_albedo.png': 'RGB sRGB undusted reflectance, A oxide coverage',
                             '*_normal.png': 'RGB OpenGL tangent normal, A=1',
                             '*_orm.png': 'R AO, G undusted roughness, B undusted metallic, A dust',
                             'aged_paint.png': 'RGB class-conditioned panel pigment; grey steel on hardware',
                             'aged_oxide.png': 'RGB class-conditioned oxide pigment; no baked paint boundary',
                             'aged_dust.png': 'RGB calibrated generated dust, smoothed over 80 mm before physical projection',
                             'aged_rust.png': 'RGB calibrated heavy-loss swatch for translucent runoff colour',
                             'region_masks.png': 'R edge/fixture band <=25 mm, G broad >=60 mm, B BareSteel, A coverage'},
                'detail_scans': 'shared CC0 hatch steel/paint/oxide albedo grain, normals and ORM at 0.20 m pitch; clean finish unchanged'}
    (directory / 'finishes.json').write_text(json.dumps(document, indent=2) + '\n')
    print('Baked both steel finishes; design median', paint.tolist(), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--fields', type=Path, required=True)
    args = parser.parse_args()
    bake(args.directory, args.fields)


if __name__ == '__main__':
    main()
