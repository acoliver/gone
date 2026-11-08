"""Derive two steel atlas sets from the shared quarters geometry masks."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

from colour import linear, srgb
from finish_fields import noise, corrosion_field, gravity_runs
from streak_sources import write_sources

ROOT = Path(__file__).resolve().parents[2]
DESIGN_ROI = (460, 440, 550, 600)
DUST = np.array([.64, .61, .55], np.float32)


def design_paint():
    image = Image.open(ROOT / 'docs/art/quarters/sheets/storage_locker_module/hero.png').convert('RGB')
    region = np.asarray(image.crop(DESIGN_ROI), np.float32) / 255
    # Median reflectance is measured in linear light, before conversion to atlas sRGB.
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
    p = arrays['position'][occupied]
    seed = metadata['seed']
    edge = -np.log(np.maximum(geometry[..., 2][occupied], 1e-8)) * .012
    fixture = np.full(len(p), 1., np.float32)
    hardware = p[:, 2] <= .105
    for source in metadata['sources']:
        lo, hi = np.array(source['bounds_blender'])
        fixture = np.minimum(fixture, np.linalg.norm(np.maximum(np.maximum(lo - p, p - hi), 0), axis=-1))
        hardware |= ((p >= lo - 1e-5) & (p <= hi + 1e-5)).all(-1)
    distance = np.minimum(edge, fixture)
    flakes = noise(p, 84, seed + 1)
    grain = noise(p, 430, seed + 2)
    corrosion = corrosion_field(p, distance, geometry[..., 1][occupied] * .15, ownership[occupied], seed)
    corridors = [dict(source, width_m=.065, start_fade_m=.010) for source in metadata['sources']]
    envelope = gravity_runs(p, arrays['normal'][occupied], corridors, seed)
    corrosion *= np.where(ownership[occupied] == 1, 1 - np.clip(envelope * 1.5, 0, 1), 1)
    corrosion[hardware] = np.maximum(corrosion[hardware], np.clip((flakes[hardware] - .50) * 9, 0, 1))
    source_count = write_sources(directory / 'streak_sources.tres', metadata['sources'], seed)
    dust = np.clip(weather[..., 0][occupied] * 3, 0, .96) * (.97 + grain * .03)
    paint = design_paint()
    steel = np.array([.72, .75, .77], np.float32)
    dark = np.array([.23, .265, .26], np.float32)
    owner = ownership[occupied]
    base = np.where((owner == 1)[:, None], paint, np.where((owner == 2)[:, None], steel, dark))
    nearest = distance_transform_edt(~occupied, return_distances=False, return_indices=True)
    region = np.zeros((*occupied.shape, 4), np.float32)
    region[occupied] = np.stack([distance <= .025, distance >= .060, owner == 2, np.ones(len(p))], -1)
    write_atlas(directory / 'region_masks.png', region, nearest)
    for state in ('as_built', 'aged'):
        rust = corrosion if state == 'aged' else np.zeros_like(corrosion)
        powder = dust if state == 'aged' else np.zeros_like(dust)
        rust_colour = np.stack([.29 + grain * .25, .095 + grain * .12, .025 + grain * .045], -1)
        colour = base.copy()
        if state == 'aged':
            vertical_paint = (owner == 1) & (arrays['normal'][occupied][:, 2] < .7)
            colour[vertical_paint] = srgb(linear(paint) * 1.6 + .02)
            colour *= .94 + flakes[:, None] * .06
        colour = colour * (1 - rust[:, None]) + rust_colour * rust[:, None]
        if state == 'aged':
            pits = np.clip((grain - .60) * 4, 0, 1) * hardware
            colour *= (1 - pits * .65)[:, None]
        roughness = np.where(owner == 2, .30 + grain * .10, np.where(owner == 1, .35 + flakes * .20, .52))
        roughness = roughness * (1 - rust) + (.86 + grain * .12) * rust
        metallic = np.where(owner == 1, .02, .45) * (1 - rust)
        # Peel is present on intact paint too; lifted rims surround each flake.
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
    document = {'method': 'two atlas sets for edge/fixture flakes; float source table for subtexel gravity trails; runtime dust with matched disabled control',
                'gravity_direction_prop': [0, -1, 0], 'gravity_source_count': source_count,
                'aged_paint_chalking_linear_gain': 1.6, 'aged_paint_chalking_linear_offset': .02,
                'age_years': {'as_built': 0, 'aged': 1000}, 'seed': seed,
                'as_built_paint_srgb': paint.tolist(), 'design_roi_xyxy': DESIGN_ROI,
                'design_median_linear': linear(paint).tolist(), 'dust_srgb': DUST.tolist(),
                'channels': {'*_albedo.png': 'RGB sRGB undusted reflectance, A oxide coverage',
                             '*_normal.png': 'RGB OpenGL tangent normal, A=1',
                             '*_orm.png': 'R AO, G undusted roughness, B undusted metallic, A dust',
                             'region_masks.png': 'R edge/fixture band <=25 mm, G broad >=60 mm, B BareSteel, A coverage'},
                'detail_scans': 'shared CC0 hatch steel/paint/oxide at 0.20 m pitch'}
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
