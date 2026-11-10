"""Integration controls for reusable dense/split/decimate/bake/card stages."""
import json
from pathlib import Path
import struct
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bake_down import bake, decimate, material_maps
from common import export, save
from densify import densify
from fabric_mesh import material, new_object
from fringe_cards import cards, fringe_material, strand_atlas
from grain_paths import surface_walk
from powder_cards import powder_card
from opacity_bake import opacity_bake
from tear_paths import split_polyline

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT/'tmp/age/pass4/module-controls'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
vertices = [(i*.025, j*.025, .01*np.sin(i/8*np.pi)) for j in range(9) for i in range(9)]
faces = [(j*9+i, j*9+i+1, (j+1)*9+i+1, (j+1)*9+i) for j in range(8) for i in range(8)]
source = new_object('BakeSource', vertices, faces, material('Upholstery', (.12, .14, .12)))
source['aged_export'] = False
for loop in source.data.loops:
    p = source.data.vertices[loop.vertex_index].co
    source.data.uv_layers[0].data[loop.index].uv = (p.x/.2, p.y/.2)
before = len(source.data.vertices)
density = densify(source, 1)
assert len(source.data.vertices) > before
assert density['mass_multiplier'] < 1
walk = surface_walk(source, (.05, .05, .005), .06, 95)
assert len(walk) > 10
cut = split_polyline(source, [(.05, .10, .01), (.1, .1, .01), (.1, .15, .01)])
assert abs(cut['removed_area_m2']) < 1e-10
assert cut['split_length_m'] > .05
low, reduction = decimate(source, 350)
assert reduction['triangles'] <= 350
assert reduction['boundary_hausdorff_upper_m'] <= .0015, reduction
mat, maps = bake(source, low, OUT, size=256, samples=4)
opacity, opacity_report = opacity_bake(low, OUT/'opacity.png', size=256)
assert opacity_report['transparent_texels'] > 0
material_maps(mat, (.12, .14, .12), opacity_image=opacity)
for name in ['NORMAL', 'AO']:
    image = mat.node_tree.nodes[name].image
    assert image.packed_file
    pixels = np.array(image.pixels[:]).reshape((-1, 4))
    assert np.isfinite(pixels).all()
    assert pixels[:, 2].max() > .9 if name == 'NORMAL' else pixels[:, :3].max() > .1
atlas, normal = strand_atlas(95)
assert atlas.shape == (2048, 1024, 4)
assert np.count_nonzero(atlas[:, :, 3]) > 10000
assert 0 < atlas[:, :, 3].mean() < 1
fringe, report = cards(low, fringe_material(OUT, 95), 95)
assert report['authored_coverage'] == 1
assert report['cards'] > 10
powder_card('PowderControl', (0, -.2, .0005), (.1, .08), OUT, 95)
bpy.data.objects.remove(source, do_unlink=True)
low['aged_export'] = True
baked_material_name = mat.name
save(OUT/'controls.blend', {'test': 'soft stages'})
export(OUT/'controls.glb')
bpy.ops.wm.open_mainfile(filepath=str(OUT/'controls.blend'))
export(OUT/'controls-repeat.glb')
assert (OUT/'controls.glb').read_bytes() == (OUT/'controls-repeat.glb').read_bytes()
data = (OUT/'controls.glb').read_bytes()
length = struct.unpack_from('<I', data, 12)[0]
doc = json.loads(data[20:20+length])
modes = {m['name']: m.get('alphaMode', 'OPAQUE') for m in doc['materials']}
assert modes['UpholsteryFringe'] == 'MASK', modes
assert modes['FloorDust_PowderControl'] == 'MASK', modes
assert modes[baked_material_name] == 'MASK', modes
(OUT/'controls.json').write_text(json.dumps({'density': density, 'split': cut,
    'decimation': reduction, 'fringe': report, 'alpha_modes': modes,
    'byte_identical_reexport': True, 'pass': True}, indent=2)+'\n')
print('SOFT MODULE CONTROLS PASS', flush=True)
