"""Detail bindings follow the surface to which each part is actually sewn."""
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import load_source, reinforce_and_bind, fit_details, follow_points
from common import recalc

body = load_source()
bindings, _ = reinforce_and_bind(body)
assert bindings['CollarInsignia_L'].get('support') == 'Collar'
assert bindings['CollarInsignia_R'].get('support') == 'Collar'
assert not bindings['RibbonBar']['rigid'], 'Ribbon fabric must follow its sewn surface'
assert len(bindings['Medal']['groups']) == 2, 'Bonded metal and cloth ribbon need separate fits'
collar = bpy.data.objects['Collar']
entry = bindings['CollarInsignia_L']['entries']
before = follow_points(collar, entry)
for vertex in collar.data.vertices:
    vertex.co.z += .017
recalc(collar)
after = follow_points(collar, entry)
np.testing.assert_allclose(after-before, np.tile([0, 0, .017], (len(before), 1)), atol=1e-7)
fit_details(body, bindings)
print('PASS: insignia bind to collar; ribbon bar is sewn; medal pieces fit separately')
