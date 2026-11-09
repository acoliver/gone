"""Linear fringe colour and independent, higher-resolution opacity controls."""
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from aging_cards import wool_fringe
from fabric_mesh import material, new_object
from fringe_cards import image_from_array
from wool_material import wool_material

out = ROOT/'tmp/age/tunic9/material-control'
out.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
wool_fringe(out)
pixels = np.array(bpy.data.images['Tunic wool fibres'].pixels[:]).reshape(-1, 4)
color = np.median(pixels[pixels[:, 3] > .5, :3], axis=0)
linear = np.where(color <= .04045, color/12.92, ((color+.055)/1.055)**2.4)
body = np.array([.025, .043, .08])
assert np.all(linear > body), (linear, body)
assert np.all(linear < body*1.6), (linear, body)
mat = material('Density control', (.025, .043, .08))
obj = new_object('DensityWool', [(0, 0, 0), (1, 0, 0), (0, 1, 0)], [(0, 1, 2)], mat)
obj.data.uv_layers.active.name = 'BakeUV'
node = mat.node_tree.nodes.new('ShaderNodeTexImage')
node.name = 'AO'
node.image = image_from_array('Small AO', np.ones((32, 32, 4), np.float32), out/'ao.png', True)
mask = np.ones((128, 128, 4), np.float32)
mask[::2, :, :3] = 0
opacity = image_from_array('Large opacity', mask, out/'opacity.png', True)
report = wool_material(obj, out, opacity)
base = bpy.data.images.load(report['path'], check_existing=False)
assert tuple(base.size) == (128, 128), tuple(base.size)
result = np.array(base.pixels[:]).reshape(128, 128, 4)
np.testing.assert_array_equal(result[:, :, 3], mask[:, :, 0])
print('PASS: fringe is slightly lighter than wool in linear light; opacity retains independent texel density')
