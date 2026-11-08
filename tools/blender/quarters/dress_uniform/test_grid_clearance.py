"""Two-millimetre contacts require four-millimetre altitudes on the evaluated grid."""
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import load_source
from aging_geometry import refine, cut_tunic, detach_fallen, pressed_sleeve
from rest_carrier import add_rest_carrier
from grid_clearance import resolve_grid_contacts
from cloth_contacts import validate_rest_faces
from cloth_stage import configure

body = load_source()
refine(body)
cut_tunic(body)
detach_fallen(body)
pressed_sleeve(body)
count = len(body.data.vertices)
add_rest_carrier(body)
report = resolve_grid_contacts(body)
assert len(body.data.vertices) == count
assert report['maximum_source_motion_m'] <= .002, report
mod = configure(body, dict(stiffness=25., bending=.015, mass=.003, frames=2,
                           self_collision=True, self_distance=.002), count,
                rest_shape=body.data.shape_keys.key_blocks['Empty pressed left sleeve'])
quality = validate_rest_faces(body, mod)
assert quality['minimum_rest_altitude_m'] >= .004
assert quality['exclusion_vertices'] == 0
print('PASS: unchanged source grid resolves every 2 mm contact, without contact exclusions', report, quality)
