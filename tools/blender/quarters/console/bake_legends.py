"""Bake quarters-only printed legends and sealed-storage keyboard finishes.

Present copies the power-room housing maps unchanged; Remembered reduces
its chip/oxide masks. Only caps and membrane receive sealed-storage aging.
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
               applies_to='caps and membrane only', key_pigment_srgb=[42, 44, 46],
               membrane_pigment_srgb=[13, 15, 15], olive_pigment_srgb=[84, 90, 58],
               key_fade_srgb=[65, 67, 69], membrane_fade_srgb=[25, 27, 25],
               olive_fade_srgb=[100, 103, 78], olive_fade_mix=.04,
               polymer_fade_mix=.08, dust_srgb=[110, 110, 110],
               olive_dust_srgb=[110, 106, 96],
               dust_mix=.08, dust_variation=.01, crack_mix=0, peeling_mix=0)
INK_COLOUR = [150, 146, 128]
INK_OPACITY = dict(as_built=.45, aged=.45)
LEGEND_HEIGHT = .70
LEGEND_STROKE = .055
HOUSING_PAINT_METAL = int(.18*255)
REMEMBERED_WEAR_MIX = .25


def cleaner_housing(colour, orm):
    housing = orm[..., 2] > 0
    intact = orm[..., 2] == HOUSING_PAINT_METAL
    worn = housing & ~intact
    # Use neighbouring authored paint while retaining each texel's AO/normal.
    nearest = distance_transform_edt(~intact, return_distances=False, return_indices=True)
    colour = colour.copy()
    material = orm.copy()
    colour[worn] = colour[tuple(nearest[:, worn])]*(1-REMEMBERED_WEAR_MIX) + colour[worn]*REMEMBERED_WEAR_MIX
    material[worn, 1:] = np.round(orm[tuple(nearest[:, worn])][:, 1:]*(1-REMEMBERED_WEAR_MIX)
                                  + orm[worn, 1:]*REMEMBERED_WEAR_MIX).astype(np.uint8)
    return colour, material


def sealed_storage(clean, positions, case):
    # Retain d203221's colour treatment on olive-tinted polymer texels too.
    olive = (clean[..., 1] > clean[..., 2]*1.15) & (clean.mean(-1) > 40)
    membrane = ~olive & (clean.mean(-1) < 25)
    pigment = np.where(olive[..., None], STORAGE['olive_pigment_srgb'],
                       np.where(membrane[..., None], STORAGE['membrane_pigment_srgb'], STORAGE['key_pigment_srgb']))
    fade = np.where(olive[..., None], STORAGE['olive_fade_srgb'],
                    np.where(membrane[..., None], STORAGE['membrane_fade_srgb'], STORAGE['key_fade_srgb']))
    variation = np.clip((clean-pigment)*STORAGE['source_variation_gain'],
                        -STORAGE['source_variation_limit_srgb'], STORAGE['source_variation_limit_srgb'])
    fade_mix = np.where(olive, STORAGE['olive_fade_mix'], STORAGE['polymer_fade_mix'])[..., None]
    faded = (pigment+variation)*(1-fade_mix)+fade*fade_mix
    x, z = positions[..., 0], positions[..., 2]
    # Object-space fine variation remains continuous across the retained UV seams.
    fine = np.sin(x*911+z*617)*np.sin(x*1301-z*887)
    dust = (STORAGE['dust_mix']+STORAGE['dust_variation']*fine)[..., None]
    dust_colour = np.where(olive[..., None], STORAGE['olive_dust_srgb'], STORAGE['dust_srgb'])
    polymer = faded*(1-dust)+dust_colour*dust
    return np.where(case[..., None], clean, polymer)


def legend_pixels(quads, rect, native_stroke):
    x0, y0, x1, y1 = rect
    lo, hi = quads.reshape(-1, 2).min(0), quads.reshape(-1, 2).max(0)
    stroke = max(2, round(min(x1-x0, y1-y0)*LEGEND_STROKE))
    # Reserve the measured print width before fitting the glyph's centre lines.
    scale = min(((x1-x0)*.90-stroke)/(hi[0]-lo[0]-native_stroke),
                ((y1-y0)*LEGEND_HEIGHT-stroke)/(hi[1]-lo[1]-native_stroke))
    pixels = (quads-(lo+hi)/2)*[scale, -scale]+[(x0+x1)/2, (y0+y1)/2]
    growth = (stroke-native_stroke*scale)/2
    centres = pixels.mean(axis=1, keepdims=True)
    pixels += np.sign(pixels-centres)*growth
    return pixels, stroke


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
    # Source cap pigment tops out below 65; its printed marks reach about 91.
    # The rectangle border samples bevel/membrane shading rather than cap pigment.
    cap_colours = {}
    for index, cap in caps.items():
        x0, y0, x1, y1 = cap['interior_rect_px']
        tile = clean[y0:y1, x0:x1]
        cap_colours[index] = np.median(tile[tile.mean(-1) <= 65], axis=0)
        tile[:] = cap_colours[index]
    positions = np.zeros((resolution, resolution, 3), np.float32)
    covered = np.zeros((resolution, resolution), bool)
    # Existing glTF local axes are X right, Y up, Z toward the operator.
    for face in mesh.faces:
        x, y, weights = triangle_samples(mesh.visual.uv[face], resolution)
        positions[y, x] = weights @ mesh.vertices[face]
        covered[y, x] = True
    nearest = distance_transform_edt(~covered, return_distances=False, return_indices=True)
    positions = positions[tuple(nearest)]
    normals = np.asarray(Image.open(TERMINAL / 'keyboard_keyboard_normal.png').convert('RGB'))
    orm = np.asarray(Image.open(TERMINAL / 'keyboard_keyboard_orm.png').convert('RGB')).copy()
    # kb3/atlas.py gives only housing nonzero metal, including chips and oxide.
    # Colour thresholds miss those exposed-metal regions and dark housing edges.
    case = orm[..., 2] > 0
    olive_polymer = ~case & (clean[..., 1] > clean[..., 2]*1.15) & (clean.mean(-1) > 40)
    aged = sealed_storage(clean, positions, case)
    clean, clean_orm = cleaner_housing(clean, orm)
    aged_orm = orm.copy()
    aged_orm[~case, 1] = np.maximum(aged_orm[~case, 1], np.where(olive_polymer[~case], 224, 240))
    aged_orm[~case, 2] = np.minimum(aged_orm[~case, 2], 24)
    mask = Image.new('L', (resolution, resolution))
    records = []
    for legend in legends['keys']:
        cap = caps[legend['design_index']]
        x0, y0, x1, y1 = cap['interior_rect_px']
        quads = np.array(legend['quads'])
        pixels, stroke = legend_pixels(quads, (x0, y0, x1, y1), legends['stroke_width'])
        tile = Image.new('L', ((x1-x0)*4, (y1-y0)*4))
        draw = ImageDraw.Draw(tile)
        for quad in pixels:
            draw.polygon([tuple(p) for p in (quad-[x0+.5, y0+.5])*4], fill=255)
        tile = tile.resize((x1-x0, y1-y0), Image.Resampling.LANCZOS)
        mask.paste(tile, (x0, y0))
        ink = np.asarray(tile)
        y, x = np.unravel_index(np.argmax(ink), ink.shape)
        iy, ix = np.where(ink > 127)
        records.append(dict(key=legend['key'], input=legend['input'], sign=legend['sign'],
                            design_index=legend['design_index'], interior_rect_px=[x0, y0, x1, y1],
                            cap_colour_srgb=cap_colours[legend['design_index']].tolist(),
                            stroke_width_px=stroke,
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
        Image.fromarray(clean_orm if state == 'as_built' else aged_orm).save(ATLAS / f'{state}_orm.png')
    regions = np.zeros_like(clean, dtype=np.uint8)
    # Leave housing outside the library shader's overrides; preserve cap regions.
    regions[..., 1] = olive_polymer*255
    regions[..., 2] = ((positions[..., 1] > .025) & ~case)*255
    Image.fromarray(regions).save(ATLAS / 'regions.png')
    mapping = dict(prop='console_keyboard', atlas_size=resolution,
                   mesh_source='assets/props/terminal/keyboard.glb', uv_method='unchanged power-room keyboard UVs',
                   storage_finish=STORAGE, normal_source='unchanged power-room keyboard normal map',
                   housing_finish=dict(source='assets/props/terminal/keyboard_keyboard_{albedo,normal,orm}.png',
                                       regions='source ORM metallic byte > 0, including chips, oxide and padding',
                                       aged='unchanged source albedo, normal and ORM',
                                       as_built='chip/oxide albedo and roughness/metal masks reduced toward nearest intact source paint',
                                       remembered_wear_mix=REMEMBERED_WEAR_MIX,
                                       intact_paint_metallic_byte=HOUSING_PAINT_METAL,
                                       normal_and_ao='unchanged in both states',
                                       shader_overrides='none: housing regions RGB zero'),
                   aged_roughness_min_byte=dict(olive_polymer=224, other_polymer=240),
                   aged_metallic_max_byte=dict(polymer=24),
                   legend_source='tools/blender/quarters/console/legends.json via production Naleya',
                   legend_height_fraction=LEGEND_HEIGHT, legend_stroke_fraction=LEGEND_STROKE,
                   legend_width_limit_fraction=.90, legend_alignment='centred',
                   legend_colour_srgb=INK_COLOUR, legend_opacity=INK_OPACITY, native_legends=records)
    (ATLAS / 'mapping.json').write_text(json.dumps(mapping, indent=2)+'\n')
    print('Baked 29 Naleya legends with power-room print weight and neutral quarters cap finishes')


if __name__ == '__main__':
    bake()
