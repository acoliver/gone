"""Changing settle damping must continue the solve, not freeze the rest mesh."""
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from cloth_stage import configure

mesh = bpy.data.meshes.new('Damping cache control')
mesh.from_pydata([(0, 0, 0), (.1, 0, 0), (.1, .1, 0), (0, .1, 0)], [], [(0, 1, 2, 3)])
obj = bpy.data.objects.new(mesh.name, mesh)
bpy.context.collection.objects.link(obj)
mod = configure(obj, dict(stiffness=500, mass=.22, bending=.3, frames=40), 4)
heights = {}
for frame in range(1, 31):
    if frame == 21:
        mod.settings.air_damping = 10.
        mod.settings.quality = 30
        mod.collision_settings.collision_quality = 6
    bpy.context.scene.frame_set(frame)
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    heights[frame] = sum(v.co.z for v in evaluated.data.vertices)/4
assert heights[20] < -.5
assert heights[21] <= heights[20]+1e-7
assert heights[30] < heights[20]-.1
print('PASS: source-damping transition preserves and continues the falling cloth state')
