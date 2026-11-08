"""Run in background Blender: source preservation and sewn attachment controls."""
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import (boundary_count, configure_detail_stiffness, fit_details,
                           load_source, reinforce_and_bind)
from cloth_stage import configure

body = load_source()
form = bpy.data.objects['ShoulderChestForm']
assert form.hide_render and not form['aged_export']
assert any(m.type == 'COLLISION' for m in form.modifiers)
ribbon = bpy.data.objects['RibbonBar']
assert boundary_count(ribbon) == 0
ribbon_faces = len(ribbon.data.polygons)
bindings, patches = reinforce_and_bind(body)
assert all(n > 0 for n in patches.values()), patches
mod = configure(body, dict(stiffness=500., shear=350., bending=.3, mass=.22, frames=2),
                len(body.data.vertices))
configure_detail_stiffness(mod)
assert mod.settings.vertex_group_structural_stiffness == 'DetailPatch'
assert mod.settings.vertex_group_bending == 'DetailPatch'
assert mod.settings.bending_stiffness_max == 15.
body.modifiers.remove(mod)
original = np.array([v.co[:] for v in bpy.data.objects['Collar'].data.vertices])
for vertex in body.data.vertices:
    vertex.co.z -= .025
fit_details(body, bindings)
actual = np.array([v.co[:] for v in bpy.data.objects['Collar'].data.vertices])
assert np.max(np.linalg.norm(actual-original-[0, 0, -.025], axis=1)) < 1e-6
assert boundary_count(ribbon) == 0 and len(ribbon.data.polygons) == ribbon_faces
print('PASS: invisible form, sewn collar without lift, DetailPatch stiffness, closed rigid ribbon', patches, flush=True)
