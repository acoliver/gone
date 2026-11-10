"""A physical fold must not fade differently when its tessellation changes."""
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from baked_age_colour import surface_fields


def cylinder_crest(step, radius=.1):
    points = [(radius, 0, 0), (radius*np.cos(step), radius*np.sin(step), 0),
              (radius, 0, radius*step), (radius*np.cos(step), -radius*np.sin(step), 0),
              (radius, 0, -radius*step)]
    mesh = bpy.data.meshes.new('Constant-radius fold')
    mesh.from_pydata(points, [], [(0, 1, 2), (0, 2, 3), (0, 3, 4), (0, 4, 1)])
    mesh.update()
    obj = bpy.data.objects.new(mesh.name, mesh)
    bpy.context.collection.objects.link(obj)
    result = float(surface_fields(obj)[0, 1])
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.meshes.remove(mesh)
    return result


bpy.ops.wm.read_factory_settings(use_empty=True)
values = [cylinder_crest(step) for step in [.025, .05, .1, .2]]
assert np.ptp(values) < .002, f'Identical 100 mm radius fades with mesh spacing: {values}'
assert .49 < np.mean(values) < .51, 'Cylindrical mean curvature is 1/(2R), scaled at 10/m'
assert cylinder_crest(.05, radius=-.1) == 0, 'Recesses must not acquire a convex-crest fade'
print('PASS: physical crest fade is independent of 2.5..20 mm tessellation and excludes recesses')
