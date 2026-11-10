"""The released cap must not retain a sewn bridge across its highest point."""
from pathlib import Path
import sys

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import load_source
from aging_geometry import seam_edges, cut_tunic

body = load_source()
bm = bmesh.new()
bm.from_mesh(body.data)
edges = seam_edges(bm, 'armhole')
top = max((v.co.z for e in edges for v in e.verts))
bm.free()
report = cut_tunic(body)['armhole']
bm = bmesh.new()
bm.from_mesh(body.data)
retained = seam_edges(bm, 'armhole')
assert report['retained_fraction'] >= .35
assert max(v.co.z for e in retained for v in e.verts) < top-.025, (top, report)
assert report['released_fraction'] >= .59, report
bm.free()
print('PASS: upper front and back cap released, lower bridge retains at least 35%')
