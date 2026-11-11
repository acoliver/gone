"""Bake quarters-only native legends and dry-aged finishes on the reused UVs.

Case weathering uses the existing whole-face steel image library. Rubber
uses the existing small-prop dry-aging bake. The terminal asset is read-only.
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
from map_library import sample_image, triangle_samples
from steel_library import LIBRARY

ATLAS = ROOT / 'assets/props/quarters/steel/console_keyboard'
TERMINAL = ROOT / 'assets/props/terminal'


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
    coordinates = np.column_stack([(positions[..., 0].ravel()+.4)/.8,
                                   .5-positions[..., 2].ravel()/.2455715])
    manifest = json.loads((LIBRARY / 'manifest.json').read_text())
    top = next(r for r in manifest['faces'] if r['kind'] == 'top' and r['passed'])
    weather = sample_image(np.asarray(Image.open(LIBRARY / top['image']).convert('RGB'), float), coordinates).reshape(clean.shape)
    rubber_root = ROOT / 'assets/props/quarters/textures/hairbrush'
    rubber = sample_image(np.asarray(Image.open(rubber_root / 'Rubber_aged.png').convert('RGB'), float), coordinates).reshape(clean.shape)
    aged = np.where(case[..., None], weather, rubber)
    normals = np.asarray(Image.open(TERMINAL / 'keyboard_keyboard_normal.png').convert('RGB'))
    orm = np.asarray(Image.open(TERMINAL / 'keyboard_keyboard_orm.png').convert('RGB')).copy()
    aged_orm = orm.copy()
    aged_orm[..., 1] = np.maximum(aged_orm[..., 1], 232)
    aged_orm[..., 2] = 0
    mask = Image.new('L', (resolution, resolution))
    records = []
    for legend in legends['keys']:
        cap = caps[legend['design_index']]
        x0, y0, x1, y1 = cap['interior_rect_px']
        quads = np.array(legend['quads'])
        lo, hi = quads.reshape(-1, 2).min(0), quads.reshape(-1, 2).max(0)
        # Printed marks occupy at most 60% of the retained cap interior.
        scale = min((x1-x0)*.60/(hi[0]-lo[0]), (y1-y0)*.60/(hi[1]-lo[1]))
        pixels = (quads-(lo+hi)/2)*[scale, -scale]+[(x0+x1)/2, (y0+y1)/2]
        tile = Image.new('L', ((x1-x0)*4, (y1-y0)*4))
        draw = ImageDraw.Draw(tile)
        for quad in pixels:
            draw.polygon([tuple(p) for p in (quad-[x0, y0])*4], fill=255)
        tile = tile.resize((x1-x0, y1-y0), Image.Resampling.LANCZOS)
        mask.paste(tile, (x0, y0))
        ink = np.asarray(tile)
        y, x = np.unravel_index(np.argmax(ink), ink.shape)
        records.append(dict(key=legend['key'], input=legend['input'], sign=legend['sign'],
                            design_index=legend['design_index'], interior_rect_px=[x0, y0, x1, y1],
                            ink_texels=int((ink > 127).sum()), ink_probe_pixel=[int(x+x0), int(y+y0)]))
    alpha = np.asarray(mask, float)[..., None]/255
    for state, colour, opacity in [('as_built', clean, .45), ('aged', aged, .30)]:
        ink = alpha*opacity
        albedo = colour*(1-ink)+np.array([150, 146, 128])*ink
        Image.fromarray(np.uint8(np.round(albedo))).save(ATLAS / f'{state}_albedo.png')
        Image.fromarray(normals).save(ATLAS / f'{state}_normal.png')
        Image.fromarray(orm if state == 'as_built' else aged_orm).save(ATLAS / f'{state}_orm.png')
    regions = np.zeros_like(clean, dtype=np.uint8)
    regions[..., 1] = case*255
    regions[..., 2] = (positions[..., 1] > .025)*255
    Image.fromarray(regions).save(ATLAS / 'regions.png')
    mapping = dict(prop='console_keyboard', atlas_size=resolution,
                   mesh_source='assets/props/terminal/keyboard.glb', uv_method='unchanged power-room keyboard UVs',
                   steel_weather_source=str((LIBRARY / top['image']).relative_to(ROOT)),
                   rubber_weather_source=str((rubber_root / 'Rubber_aged.png').relative_to(ROOT)),
                   legend_source='tools/blender/quarters/console/legends.json via production Naleya',
                   legend_colour_srgb=[150, 146, 128], legend_opacity=dict(as_built=.45, aged=.30),
                   native_legends=records)
    (ATLAS / 'mapping.json').write_text(json.dumps(mapping, indent=2)+'\n')
    print('Baked 29 muted production Naleya legends and both dry-aged keyboard finish sets')


if __name__ == '__main__':
    bake()
