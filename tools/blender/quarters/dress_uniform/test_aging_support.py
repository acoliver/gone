"""Run in background Blender: source preservation and sewn attachment controls."""
import json
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
assert all(min(entry['weights']) == 0. for entry in bindings['Collar']['entries'])
collar_source = bpy.data.objects['Collar']
attachment = json.loads(collar_source['attachment'])
bases = np.array(attachment['base_blender_m'])
tops = np.array(attachment['top_blender_m'])
points = np.array(bindings['Collar']['original'])
axis = tops-bases
station_t = np.clip(np.einsum('ijk,jk->ij', points[:, None]-bases, axis)/np.sum(axis**2, axis=1), 0, 1)
station = np.linalg.norm(points[:, None]-bases-axis*station_t[:, :, None], axis=2).argmin(1)
body_points = np.array([v.co[:] for v in body.data.vertices])
anchors = np.array([np.array(e['weights'])@body_points[list(e['triangle'])] for e in bindings['Collar']['entries']])
for index in np.unique(station):
    assert np.max(np.ptp(anchors[station == index], axis=0)) < 1e-7, 'Collar top and sewn foot bound to different stations'
mod = configure(body, dict(stiffness=500., shear=350., bending=.3, mass=.22, frames=2),
                len(body.data.vertices))
configure_detail_stiffness(mod)
assert mod.settings.vertex_group_structural_stiffness == 'DetailPatch'
assert mod.settings.vertex_group_bending == 'DetailPatch'
assert mod.settings.bending_stiffness_max == 15.
body.modifiers.remove(mod)
fit_details(body, bindings)
original = np.array([v.co[:] for v in bpy.data.objects['Collar'].data.vertices])
for vertex in body.data.vertices:
    vertex.co.z -= .025
fit_details(body, bindings)
actual = np.array([v.co[:] for v in bpy.data.objects['Collar'].data.vertices])
assert np.max(np.linalg.norm(actual-original-[0, 0, -.025], axis=1)) < 1e-6
assert boundary_count(ribbon) == 0 and len(ribbon.data.polygons) == ribbon_faces
placket = bpy.data.objects['Placket']
old = np.asarray(bindings['Placket']['original'])
new = np.array([placket.matrix_world @ v.co for v in placket.data.vertices])
extra = np.linalg.norm((new-old-[0, 0, -.025]).mean(0))
assert extra < .003, f'Curved support was replaced by a global plane: {extra} m unwanted lift'
print('PASS: invisible form, sewn collar without lift, DetailPatch stiffness, closed rigid ribbon', patches, flush=True)
