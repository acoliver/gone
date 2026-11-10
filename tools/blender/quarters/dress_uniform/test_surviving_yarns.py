"""Surviving yarns anchor to the visible wool surface before fringe occupies it."""
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aging_support
from fabric_mesh import material, new_object
from polish_pass10 import add_surviving_yarns
from common import assert_surface_clear

bpy.ops.wm.read_factory_settings(use_empty=True)
points = [(-.02, -.01, -.20), (.02, -.01, -.20), (.02, -.01, -.28), (-.02, -.01, -.28),
          (.05, -.01, -.20), (.09, -.01, -.20), (.09, -.01, -.28), (.05, -.01, -.28)]
cloth = new_object('Yarn anchors', points, [(0, 1, 2, 3), (4, 5, 6, 7)], material('Wool', (.025, .043, .08)))
record = {'pass10': {'bridge_roots': [[[.015, -.01, z], [.055, -.01, z]] for z in [-.218, -.240, -.262]]}}
yarns, report = add_surviving_yarns(record, cloth, [cloth])
assert report['surviving_yarns'] == 3, report
assert len(yarns.data.polygons) == 48
assert np.isfinite(np.array([v.co[:] for v in yarns.data.vertices])).all()
assert_surface_clear(yarns)
assert yarns.data.materials[0].name.startswith('WoolFringe')
print('PASS: three anchored, curved, crossing-free yarns retain textile diagnostic classification', report)
