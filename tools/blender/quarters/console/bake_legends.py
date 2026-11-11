"""Bake quarters-only printed legends and sealed-storage keyboard finishes.

The power-room mesh, UVs and source textures remain read-only. Aging here
adds bounded pigment fade and fine dust, without the hairbrush fracture map
or the steel library's full-face peeling and chips.
"""
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt
import trimesh

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / 'tools/quarters_aging'))
from map_library import triangle_samples

ATLAS = ROOT / 'assets/props/quarters/steel/console_keyboard'
TERMINAL = ROOT / 'assets/props/terminal'
STORAGE = dict(age_years=1000, source_variation_gain=.25, source_variation_limit_srgb=2.5,
               case_pigment_srgb=[84, 90, 58], key_pigment_srgb=[42, 44, 46],
               membrane_pigment_srgb=[13, 15, 15], case_fade_srgb=[100, 103, 78],
               key_fade_srgb=[65, 65, 63], membrane_fade_srgb=[25, 27, 25],
               case_fade_mix=.04, polymer_fade_mix=.08, dust_srgb=[110, 106, 96],
               dust_mix=.08, dust_variation=.01, crack_mix=0, peeling_mix=0)
INK_COLOUR = [112, 112, 102]
INK_OPACITY = dict(as_built=.38, aged=.30)


def sealed_storage(clean, positions, case):
    membrane = ~case & (clean.mean(-1) < 25)
    pigment = np.where(case[..., None], STORAGE['case_pigment_srgb'],
                       np.where(membrane[..., None], STORAGE['membrane_pigment_srgb'],
                                STORAGE['key_pigment_srgb']))
    fade = np.where(case[..., None], STORAGE['case_fade_srgb'],
                    np.where(membrane[..., None], STORAGE['membrane_fade_srgb'],
                             STORAGE['key_fade_srgb']))
    variation = np.clip((clean-pigment)*STORAGE['source_variation_gain'],
                        -STORAGE['source_variation_limit_srgb'], STORAGE['source_variation_limit_srgb'])
    fade_mix = np.where(case, STORAGE['case_fade_mix'], STORAGE['polymer_fade_mix'])[..., None]
    faded = (pigment+variation)*(1-fade_mix)+fade*fade_mix
    x, z = positions[..., 0], positions[..., 2]
    # Object-space fine variation remains continuous across the retained UV seams.
    fine = np.sin(x*911+z*617)*np.sin(x*1301-z*887)
    dust = (STORAGE['dust_mix']+STORAGE['dust_variation']*fine)[..., None]
    return faded*(1-dust)+np.array(STORAGE['dust_srgb'])*dust


def bake():
    ATLAS.mkdir(parents=True, exist_ok=True)
    report = json.loads((ROOT / 'art-source/terminal/generated/console2/kb3/report.json').read_text())
    legends = json.loads((HERE / 'legends.json').read_text())
    source = trimesh.load(TERMINAL / 'keyboard.glb', force='scene')
    mesh = source.geometry[source.graph['Keyboard'][1]]
    clean = np.asarray(Image.open(TERMINAL / 'keyboard_keyboard_albedo.png').convert('RGB'), float).copy()
    resolution = clean.shape[0]
    assert clean.shape == (2048, 2048, 3)
    caps = {r['design_index']: r for r in report['legends']}
    # Remove the terminal's original muted marks before applying production Naleya.
    for cap in caps.values():
        x0, y0, x1, y1 = cap['interior_rect_px']
        tile = clean[y0:y1, x0:x1]
        border = np.concatenate([tile[:3].reshape(-1, 3), tile[-3:].reshape(-1, 3),
                                 tile[:, :3].reshape(-1, 3), tile[:, -3:].reshape(-1, 3)])
        tile[:] = np.median(border, axis=0)
    positions = np.zeros((resolution, resolution, 3), np.float32)
    covered = np.zeros((resolution, resolution), bool)
    # Existing glTF local axes are X right, Y up, Z toward the operator.
    for face in mesh.faces:
        x, y, weights = triangle_samples(mesh.visual.uv[face], resolution)
        positions[y, x] = weights @ mesh.vertices[face]
        covered[y, x] = True
    nearest = distance_transform_edt(~covered, return_distances=False, return_indices=True)
    positions = positions[tuple(nearest)]
    case = (clean[..., 1] > clean[..., 2]*1.15) & (clean.mean(-1) > 40)
    aged = sealed_storage(clean, positions, case)
    normals = np.asarray(Image.open(TERMINAL / 'keyboard_keyboard_normal.png').convert('RGB'))
    orm = np.asarray(Image.open(TERMINAL / 'keyboard_keyboard_orm.png').convert('RGB')).copy()
    aged_orm = orm.copy()
    aged_orm[..., 1] = np.maximum(aged_orm[..., 1], np.where(case, 224, 240))
    aged_orm[..., 2] = np.minimum(aged_orm[..., 2], 24)
    mask = Image.new('L', (resolution, resolution))
    records = []
    for legend in legends['keys']:
        cap = caps[legend['design_index']]
        x0, y0, x1, y1 = cap['interior_rect_px']
        quads = np.array(legend['quads'])
        lo, hi = quads.reshape(-1, 2).min(0), quads.reshape(-1, 2).max(0)
        # Height controls the print size, including the wide, shallow bottom-row caps.
        scale = min((x1-x0)*.90/(hi[0]-lo[0]), (y1-y0)*.435/(hi[1]-lo[1]))
        pixels = (quads-(lo+hi)/2)*[scale, -scale]+[(x0+x1)/2, (y0+y1)/2]
        tile = Image.new('L', ((x1-x0)*4, (y1-y0)*4))
        draw = ImageDraw.Draw(tile)
        for quad in pixels:
            draw.polygon([tuple(p) for p in (quad-[x0, y0])*4], fill=255)
        tile = tile.resize((x1-x0, y1-y0), Image.Resampling.LANCZOS)
        mask.paste(tile, (x0, y0))
        ink = np.asarray(tile)
        y, x = np.unravel_index(np.argmax(ink), ink.shape)
        iy, ix = np.where(ink > 127)
        records.append(dict(key=legend['key'], input=legend['input'], sign=legend['sign'],
                            design_index=legend['design_index'], interior_rect_px=[x0, y0, x1, y1],
                            ink_bounds_px=[int(ix.min()+x0), int(iy.min()+y0),
                                           int(ix.max()+x0+1), int(iy.max()+y0+1)],
                            ink_texels=int((ink > 127).sum()), ink_probe_pixel=[int(x+x0), int(y+y0)],
                            unprinted_probe_srgb=dict(as_built=clean[y+y0, x+x0].tolist(),
                                                      aged=aged[y+y0, x+x0].tolist())))
    alpha = np.asarray(mask, float)[..., None]/255
    for state, colour in [('as_built', clean), ('aged', aged)]:
        ink = alpha*INK_OPACITY[state]
        albedo = colour*(1-ink)+np.array(INK_COLOUR)*ink
        Image.fromarray(np.uint8(np.round(albedo))).save(ATLAS / f'{state}_albedo.png')
        Image.fromarray(normals).save(ATLAS / f'{state}_normal.png')
        Image.fromarray(orm if state == 'as_built' else aged_orm).save(ATLAS / f'{state}_orm.png')
    regions = np.zeros_like(clean, dtype=np.uint8)
    regions[..., 1] = case*255
    regions[..., 2] = (positions[..., 1] > .025)*255
    Image.fromarray(regions).save(ATLAS / 'regions.png')
    mapping = dict(prop='console_keyboard', atlas_size=resolution,
                   mesh_source='assets/props/terminal/keyboard.glb', uv_method='unchanged power-room keyboard UVs',
                   storage_finish=STORAGE, normal_source='unchanged power-room keyboard normal map',
                   aged_roughness_min_byte=dict(case=224, polymer=240), aged_metallic_max_byte=24,
                   legend_source='tools/blender/quarters/console/legends.json via production Naleya',
                   legend_height_fraction=.435, legend_width_limit_fraction=.90, legend_alignment='centred',
                   legend_colour_srgb=INK_COLOUR, legend_opacity=INK_OPACITY, native_legends=records)
    (ATLAS / 'mapping.json').write_text(json.dumps(mapping, indent=2)+'\n')
    print('Baked 29 smaller printed Naleya legends and quarters-only sealed-storage keyboard finish')


if __name__ == '__main__':
    bake()
