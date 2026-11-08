"""The sleeve retains its source bending instead of inheriting torso bending."""
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import load_source, configure_detail_stiffness
from cloth_stage import configure

body = load_source()
mod = configure(body, dict(stiffness=500, shear=350, bending=.3, mass=.22, frames=2), len(body.data.vertices))
body.vertex_groups.new(name='DetailPatch')
configure_detail_stiffness(mod)
group = body.vertex_groups[mod.settings.vertex_group_bending]
selected = {loop.vertex_index for loop in body.data.loops
            if 1.099 < body.data.uv_layers[0].data[loop.index].uv.x < 1.551}
ids = [i for i in selected if body.data.vertices[i].co.z < -.50]
assert len(ids) > 100
for i in ids:
    weight = group.weight(i)
    bending = mod.settings.bending_stiffness*(1-weight)+mod.settings.bending_stiffness_max*weight
    np.testing.assert_allclose(bending, 5., atol=1e-5)
assert mod.settings.bending_stiffness < .301
assert mod.settings.bending_stiffness_max == 15.
print('PASS: empty sleeve retains source bending 5 while torso remains at 0.3')
