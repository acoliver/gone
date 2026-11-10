"""Hem losses must not move the seated placket's centre-front wool."""
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from shape_pass12 import torn_hem

bpy.ops.wm.open_mainfile(filepath=str(ROOT/'tmp/age/tunic11/visible/baked.blend'))
body = bpy.data.objects['TunicBody']
patch = body.vertex_groups['DetailPatch'].index
support = {tuple(v.co) for v in body.data.vertices
           if any(g.group == patch and g.weight > 0 for g in v.groups)}
centre = {tuple(v.co) for v in body.data.vertices if abs(v.co.x) < .025 and v.co.z < -.75}
assert centre and support
report = torn_hem(body)
after = {tuple(v.co) for v in body.data.vertices}
assert support <= after
assert centre <= after
assert report['removed_area_m2'] > .004
assert report['maximum_tongue_relaxation_m'] > .025
print('PASS: centre-front and fitting-support wool stays fixed while off-centre hem strips are cut and relaxed')
