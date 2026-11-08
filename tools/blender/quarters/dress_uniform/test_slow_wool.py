"""Co-scaling preserves spring/gravity ratios and releases only temporary holds."""
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import load_source, configure_detail_stiffness
from cloth_stage import configure
from slow_wool import MASS_SCALE, slow_wool, release_pins

body = load_source()
body.vertex_groups.new(name='DetailPatch')
mod = configure(body, dict(stiffness=500., shear=350., mass=.22, bending=.3, frames=151),
                len(body.data.vertices), {0: 1.})
configure_detail_stiffness(mod)
fields = ('mass', 'tension_stiffness', 'shear_stiffness', 'bending_stiffness',
          'tension_stiffness_max', 'compression_stiffness_max',
          'shear_stiffness_max', 'bending_stiffness_max', 'sewing_force_max')
before = {field: getattr(mod.settings, field) for field in fields}
report = slow_wool(mod)
for field in fields:
    np.testing.assert_allclose(getattr(mod.settings, field), before[field]*MASS_SCALE, rtol=1e-6)
assert mod.settings.air_damping == 10
assert abs(mod.collision_settings.self_distance_min-.002) < 1e-8
release_pins(body, mod)
body.modifiers.remove(mod)
release = body.modifiers['150 frame shoulder release']
group = body.vertex_groups['Releasing shoulder stitches']
index = next(v.index for v in body.data.vertices if any(g.group == group.index for g in v.groups))
pins = body.vertex_groups['Retained stitches'].index
for frame, expected in ((1, 1.), (76, .5), (151, 0.)):
    bpy.context.scene.frame_set(frame)
    evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    weight = next((g.weight for g in evaluated.data.vertices[index].groups if g.group == pins), 0.)
    np.testing.assert_allclose(weight, expected, atol=1e-5)
    permanent = next(g.weight for g in evaluated.data.vertices[0].groups if g.group == pins)
    np.testing.assert_allclose(permanent, 1.)
print('PASS: all springs and mass co-scale; temporary holds release across 150 frames; permanent holds stay')
