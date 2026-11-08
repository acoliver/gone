"""A standing collar follows its sewn curve without inheriting shoulder-face twists."""
import json
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from collar_fit import fit_standing_collar

bases = np.array([[-.1, -.02, 0], [.1, -.02, 0], [.1, .02, 0], [-.1, .02, 0]])
tops = bases+[0, 0, .043]
mesh = bpy.data.meshes.new('Twisting neckline support')
mesh.from_pydata([*bases.tolist(), [0, 0, 0]], [], [(i, (i+1)%4, 4) for i in range(4)])
body = bpy.data.objects.new(mesh.name, mesh)
bpy.context.collection.objects.link(body)
collar = bpy.data.objects.new('Standing collar', None)
bpy.context.collection.objects.link(collar)
collar['attachment'] = json.dumps({'base_blender_m': bases.tolist(), 'top_blender_m': tops.tolist()})
entries = [{'triangle': [i, (i+1)%4, 4], 'weights': [1., 0., 0.]} for i in range(4)]
binding = {'entries': entries+entries, 'original': np.vstack([bases, tops]).tolist()}
reference = fit_standing_collar(body, collar, binding)
body.data.vertices[4].co.z = .10
actual = fit_standing_collar(body, collar, binding)
np.testing.assert_allclose(actual, reference, atol=1e-7)
np.testing.assert_allclose(actual[4:]-actual[:4], np.tile([0, 0, .043], (4, 1)), atol=1e-7)
for vertex in body.data.vertices:
    vertex.co.z -= .025
translated = fit_standing_collar(body, collar, binding)
np.testing.assert_allclose(translated, actual-[0, 0, .025], atol=1e-7)
print('PASS: collar follows the sewn curve, preserves upright columns and ignores adjacent-face twisting')
