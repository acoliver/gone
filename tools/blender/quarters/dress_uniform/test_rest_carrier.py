"""A folded bending rest must change the solved shape, not merely store a key."""
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from age_tunic import bake_simulation
from cloth_stage import configure
from fabric_mesh import material, new_object
from rest_carrier import add_rest_carrier

spans = []
for folded in [False, True]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.gravity = (0, 0, 0)
    points = [(x, y, 0) for y in [0, .1, .2] for x in [0, .1, .2]]
    faces = [(j*3+i, j*3+i+1, (j+1)*3+i+1, (j+1)*3+i) for j in range(2) for i in range(2)]
    obj = new_object('RestControl', points, faces, material('Control', (.025, .043, .08)))
    obj.shape_key_add(name='Basis')
    rest = obj.shape_key_add(name='Pressed rest')
    if folded:
        for vertex in rest.data:
            if vertex.co.x > .1:
                vertex.co.z = vertex.co.x-.1
                vertex.co.x = .1
    add_rest_carrier(obj)
    mod = configure(obj, dict(frames=60, quality=12, mass=.01, stiffness=150,
                              bending=2, air_factor=.1), 9, rest_shape=rest)
    mod.settings.mass = .01*9/25
    bake_simulation(obj, mod, 60)
    assert len(obj.data.vertices) == 25
    assert not obj.modifiers
    assert obj.data.shape_keys is None
    spans.append(float(np.ptp([v.co.z for v in obj.data.vertices])))
assert spans[0] < .001, spans
assert spans[1] > .02, spans
print('PASS: actual SIMPLE subdivision transmits cloth rest angles and freezes only once', spans, flush=True)
