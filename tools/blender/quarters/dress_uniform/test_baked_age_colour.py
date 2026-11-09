"""Exposure-derived wool fade remains blue-grey and dust is independently visible."""
import json
import sys
from pathlib import Path
import bpy
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from baked_age_colour import aged_linear, raster_fields

palette = json.loads((ROOT/'tmp/age/tunic12/target-colours.json').read_text())['colours']
ao = np.array([[1., .18], [1., 1.]])
masks = np.array([[[1., 1., 1., .7, .5], [0., 0., 0., .4, .5]],
                  [[0., .8, .5, .5, .4], [0., 0., .5, .5, .4]]])
colour, fade, dust = aged_linear(ao, masks, palette)
control, _, _ = aged_linear(ao, masks, palette, dust=False)
assert colour[0, 0].mean() > colour[0, 1].mean()*3
assert np.mean(abs(colour[0, 0]-control[0, 0])) > .03
assert dust[0, 0] > .4 and dust[0, 1] == 0
assert fade[0, 0] > fade[0, 1]
assert colour[1, 0].mean() > colour[1, 1].mean(), 'Convex fold crests must fade more than flat wool'
assert (colour[:, :, 2] >= colour[:, :, 1]).all() and (colour[:, :, 1] >= colour[:, :, 0]).all()
exposure, _, exposure_dust = aged_linear(ao, masks, palette, crest_fade=False)
changed = masks.copy()
changed[:, :, 1] = 1-masks[:, :, 1]
control, _, control_dust = aged_linear(ao, changed, palette, crest_fade=False)
np.testing.assert_array_equal(exposure, control)
np.testing.assert_array_equal(exposure_dust, control_dust)
assert exposure[0, 0].mean() > exposure[0, 1].mean()*3, 'Exposed wool must remain lighter than AO recesses'
bpy.ops.wm.read_factory_settings(use_empty=True)
mesh = bpy.data.meshes.new('MaskTest')
mesh.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
obj = bpy.data.objects.new('MaskTest', mesh)
bpy.context.collection.objects.link(obj)
uv = mesh.uv_layers.new(name='BakeUV')
for loop, coordinate in zip(uv.data, [(0, 0), (1, 0), (0, 1)]):
    loop.uv = coordinate
mesh.update()
fields = raster_fields(obj, 32)
assert np.isfinite(fields).all(), 'Baked masks contain invalid samples'
assert (fields >= 0).all() and (fields <= 1).all(), 'Exposure masks must remain bounded'
assert fields[4, 4, 0] > .99, 'Up-facing mask must use physical normals in Blender Z-up'
print('PASS: baked exposure masks, independent visible dust contrast, blue-grey palette and crest-weighted fading')
