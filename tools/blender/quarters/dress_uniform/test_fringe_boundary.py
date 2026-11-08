"""Headless Blender controls for physical fringe coverage and root UVs."""
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from fabric_mesh import material, new_object
from fringe_boundary import boundary_chains, measured_coverage, spaced_cards

bpy.ops.wm.read_factory_settings(use_empty=True)
mat = material('Test wool', (.02, .04, .08))
plane = new_object('Cloth control', [(0, 0, .1), (.2, 0, .1), (.2, .1, .1), (0, .1, .1)],
                   [(0, 1, 2, 3)], mat)
fringe, report = spaced_cards(plane, mat, 9521, wool=True, blockers=[plane])
assert report['authored_coverage'] >= .70, report
positions = np.array([v.co[:] for v in fringe.data.vertices]).reshape(-1, 4, 3)
extents = np.linalg.norm(positions[:, 2:].mean(1)-positions[:, :2].mean(1), axis=1)
assert .006 <= np.median(extents) <= .008, f'Wool fringe median must follow the 7 mm recipe: {np.median(extents)}'
assert extents.min() >= .0029999 and extents.max() <= .0180001
assert abs(report['boundary_length_m']-.6) < 1e-6
for loop in fringe.data.loops:
    uv = fringe.data.uv_layers.active.data[loop.index].uv
    corner = loop.vertex_index % 4
    row = int(uv.y*8+1e-5)
    if corner < 2:
        assert row <= 7
    assert uv.x == (1. if corner in [1, 2] else 0.)
# Reversing polygon winding must not turn a tip into a measured root.
before = report['authored_coverage']
for face in fringe.data.polygons:
    face.flip()
after = measured_coverage(fringe, boundary_chains(plane))['authored_coverage']
assert abs(before-after) < 1e-9
assert np.isfinite(np.array([v.co[:] for v in fringe.data.vertices])).all()
print('PASS: arclength card coverage and winding-independent root identity', report, flush=True)
