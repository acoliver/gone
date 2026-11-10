"""Shoulder fibre shortening preserves roots, coverage width and other regions."""
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from fringe_drape import shorten_shoulder_cards


def verify():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mesh = bpy.data.meshes.new('Fibre projection test')
    points = [(.20, 0, -.20), (.21, 0, -.20), (.21, -.008, -.20), (.20, -.008, -.20),
              (.05, 0, -.20), (.06, 0, -.20), (.06, -.008, -.20), (.05, -.008, -.20)]
    mesh.from_pydata(points, [], [(0, 1, 2, 3), (4, 5, 6, 7)])
    layer = mesh.uv_layers.new()
    for face in mesh.polygons:
        for loop, uv in zip(face.loop_indices, [(0, 0), (1, 0), (1, 1), (0, 1)]):
            layer.data[loop].uv = uv
    obj = bpy.data.objects.new(mesh.name, mesh)
    bpy.context.collection.objects.link(obj)
    before = np.array([v.co[:] for v in mesh.vertices])
    report = shorten_shoulder_cards([obj.name])[obj.name]
    after = np.array([v.co[:] for v in mesh.vertices])
    np.testing.assert_array_equal(after[[0, 1, 4, 5, 6, 7]], before[[0, 1, 4, 5, 6, 7]])
    np.testing.assert_array_equal(after[:, [0, 2]], before[:, [0, 2]])
    np.testing.assert_allclose(after[[2, 3], 1], -.0012, atol=1e-9)
    assert report['cards'] == 1 and report['root_vertices_unchanged']
    assert abs(report['previous_maximum_m']-.008) < 1e-8
    assert len(mesh.polygons) == 2 and len(mesh.vertices) == 8
    print('PASS: 1.2 mm fibre projection; exact root width, topology and non-shoulder vertices')


if __name__ == '__main__':
    verify()
