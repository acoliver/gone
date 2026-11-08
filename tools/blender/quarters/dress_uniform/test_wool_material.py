"""Headless Blender control: navy PBR channels, persisted stitches and repeat bytes."""
import json
from pathlib import Path
import struct
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from aging_cards import stitch_holes, wool_fringe
from bake_down import material_maps
from common import export
from fabric_mesh import material, new_object
from fringe_cards import image_from_array, strand_atlas
from wool_material import wool_material

out = ROOT/'tmp/age/tunic5/material-control'
out.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
fringe = wool_fringe(out)
image = bpy.data.images['Tunic wool fibres']
alpha = np.array(image.pixels[:]).reshape(1024, 1024, 4)[:, :, 3]
def root_visibility(alpha):
    filtered = alpha.reshape(8, 128, 32, 32).mean(3)[:, :16]
    return float((filtered >= .5).mean())
original, _ = strand_atlas(9521, wool=True, strip_height=128)
assert root_visibility(original[:, :, 3]) < .10
assert root_visibility(alpha) >= .25, root_visibility(alpha)
print('PASS: minified wool roots remain visible', root_visibility(alpha), flush=True)
mat = material('Test wool', (.025, .043, .08))
obj = new_object('TunicBody', [(0, 0, .1), (.06, 0, .1), (.06, .06, .1), (0, .06, .1)], [(0, 1, 2, 3)], mat)
obj.data.uv_layers.active.name = 'BakeUV'
for loop in obj.data.loops:
    p = obj.data.vertices[loop.vertex_index].co
    obj.data.uv_layers.active.data[loop.index].uv = (p.x/.06, p.y/.06)
group = obj.vertex_groups.new(name='Seam allowance')
group.add(list(range(4)), 1., 'REPLACE')
rgba = np.ones((128, 128, 4), np.float32)
mask = image_from_array('Control opacity', rgba, out/'opacity.png', True)
for name, data in [('AO', rgba), ('NORMAL', np.tile([.5, .5, 1., 1.], (128, 128, 1)).astype(np.float32))]:
    node = mat.node_tree.nodes.new('ShaderNodeTexImage')
    node.name = name
    node.image = image_from_array(name, data, out/(name+'.png'), True)
report = stitch_holes(obj, mask)
assert report['transparent_stitch_texels'] > 0, report
pixels = np.array(mask.pixels[:]).reshape(128, 128, 4)
transparent = int((pixels[:, :, 0] < .5).sum())
material_maps(mat, (.025, .043, .08), opacity_image=mask)
base = wool_material(obj, out, mask)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(out/'control.blend'))
export(out/'first.glb')
bpy.ops.wm.open_mainfile(filepath=str(out/'control.blend'))
loaded = bpy.data.images['Control opacity']
actual = np.array(loaded.pixels[:]).reshape(128, 128, 4)
assert int((actual[:, :, 0] < .5).sum()) == transparent
export(out/'repeat.glb')
a, b = (out/'first.glb').read_bytes(), (out/'repeat.glb').read_bytes()
assert a == b, 'Persisted PBR material changed export bytes'
document = json.loads(a[20:20+struct.unpack_from('<I', a, 12)[0]])
mat = document['materials'][0]
assert mat['normalTexture'] and mat['pbrMetallicRoughness']['baseColorTexture']
assert mat['alphaMode'] == 'MASK'
image = bpy.data.images.load(base['path'], check_existing=False)
color = np.array(image.pixels[:]).reshape(128, 128, 4)
assert np.all(color[:, :, 2] > color[:, :, 0])
print('PASS: persisted stitch mask, navy texture, glTF normal/alpha channels and byte-identical repeat', transparent, flush=True)
