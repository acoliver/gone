"""The connected allowance has bake area and uses the sheet's physical stations."""
import sys
from pathlib import Path
import bpy
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from lip_arclength import labelled_station_samples, erosion_depth

bpy.ops.wm.open_mainfile(filepath=str(ROOT/'tmp/age/tunic12/lips/baked.blend'))
body = bpy.data.objects['TunicBody']
body.data.calc_loop_triangles()
uv = body.data.uv_layers['BakeUV'].data
areas = []
for triangle in body.data.loop_triangles:
    a, b, c = np.array([uv[i].uv[:] for i in triangle.loops])
    areas.append(abs(np.linalg.det(np.array([b-a, c-a])))*.5)
assert min(areas) > 1e-12, 'Collapsed allowance BakeUV cannot carry opacity breakup'
assert all(p.material_index == 0 for p in body.data.polygons)
points, allowed, stations, lengths = labelled_station_samples(body)
assert len(points) == len(stations) == len(allowed)
assert min(lengths) > 0.
depth = erosion_depth(np.arange(0., .1, .0001), 9521)
assert np.ptp(depth) > .003
assert np.all((depth >= .00015) & (depth <= .006))
print('PASS: every allowance triangle has BakeUV area, one shared wool material, and physical-station erosion')
