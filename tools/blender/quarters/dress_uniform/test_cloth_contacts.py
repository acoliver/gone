"""Reject unresolved rest faces; resolved cloth falls without collision exclusions."""
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from age_tunic import bake_simulation, wool_config
from cloth_contacts import validate_rest_faces
from cloth_stage import configure
from fabric_mesh import material, new_object


def fall(self_contact, spacing):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = 24
    nx, ny = 50, 15
    vertices = [(x*spacing, y*spacing, .25) for y in range(ny+1) for x in range(nx+1)]
    faces = []
    for y in range(ny):
        for x in range(nx):
            a = y*(nx+1)+x
            faces += [(a, a+1, a+nx+2), (a, a+nx+2, a+nx+1)]
    obj = new_object('Strip', vertices, faces, material('Wool', (.025, .043, .08)))
    config = wool_config(25, spacing)
    config['self_collision'] = self_contact
    mod = configure(obj, config, 80)
    mod.settings.air_damping = 0.
    report = validate_rest_faces(obj, mod)
    assert report['exclusion_vertices'] == 0
    assert report['sub_diameter_faces'] == 0
    assert mod.collision_settings.use_self_collision == self_contact
    bake_simulation(obj, mod, 25)
    points = np.array([v.co[:] for v in obj.data.vertices])
    assert points[:, 2].mean() < .20, points.mean(0)
    assert np.isfinite(points).all()
    return points


try:
    fall(True, .002)
except ValueError as error:
    assert 'unresolved rest faces' in str(error)
else:
    raise AssertionError('Sub-diameter rest faces were accepted')
reference = fall(False, .004)
actual = fall(True, .004)
error = float(np.linalg.norm(actual-reference, axis=1).max())
assert error < 1e-6, error
print('PASS: unresolved rest faces fail fast; no-exclusion resolved fall matches control', error, flush=True)
