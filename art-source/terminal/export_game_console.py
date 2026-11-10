"""Reduce the supplied standing console to the game's prop budget.

Run with Blender --background --factory-startup --python this_file -- SOURCE.glb.
The placement JSON and standalone keyboard remain unchanged.
"""
from pathlib import Path
import sys
import json

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree


def check_closed(mesh):
    topology = bmesh.new()
    topology.from_mesh(mesh)
    nonmanifold_edges = sum(not edge.is_manifold for edge in topology.edges)
    topology.free()
    assert nonmanifold_edges == 0, f'Console shell has {nonmanifold_edges} nonmanifold edges'


def fit_display(body, display):
    vertices = [body.matrix_world @ vertex.co for vertex in body.data.vertices]
    surface = BVHTree.FromPolygons(vertices, [list(p.vertices) for p in body.data.polygons])
    corners = np.array([list(display.matrix_world @ v.co) for v in display.data.vertices])
    low, high = corners.min(axis=0), corners.max(axis=0)
    # The old rectangle includes the curved side returns. Keep the glass on
    # the flat recess, with a further 4 mm inset at its top and bottom.
    low += np.array([0.030, 0, 0.004])
    high -= np.array([0.030, 0, 0.004])
    samples = []
    for z in np.linspace(low[2], high[2], 7):
        for x in np.linspace(low[0], high[0], 9):
            hit, _, _, _ = surface.ray_cast(Vector((x, low[1] - 0.2, z)), Vector((0, 1, 0)))
            assert hit is not None, 'Screen fit ray missed the console'
            samples.append(list(hit))
    points = np.array(samples)
    design = np.column_stack((points[:, 0], points[:, 2], np.ones(len(points))))
    a, b, c = np.linalg.lstsq(design, points[:, 1], rcond=None)[0]
    normal = Vector((a, -1, b)).normalized()
    right = Vector((0, 0, 1)).cross(normal).normalized()
    up = normal.cross(right).normalized()
    x, z = (low[0] + high[0]) / 2, (low[2] + high[2]) / 2
    center = Vector((x, a * x + b * z + c, z))
    width = float(high[0] - low[0]) / right.x
    height = float(high[2] - low[2]) / up.z
    # Verify the actual tilted rectangle along its normal, not just the
    # initial front-facing projection used to fit it.
    residuals = []
    for v in np.linspace(-0.5, 0.5, 7):
        for u in np.linspace(-0.5, 0.5, 9):
            point = center + right * (u * width) + up * (v * height)
            hit, _, _, _ = surface.ray_cast(point + normal * 0.1, -normal)
            assert hit is not None, 'Tilted screen ray missed the console'
            residuals.append((hit - point).dot(normal))
    residuals = np.array(residuals)
    maximum = float(np.max(np.abs(residuals)))
    offset = maximum + 0.001
    gaps = offset - residuals
    assert np.min(gaps) >= 0.001 - 1e-7 and np.max(gaps) <= 0.004
    # Blender's local display is X/Z with outward -Y; glTF converts it to
    # X/Y with outward +Z. DisplayPlane denotes the finished glass front.
    rotation = Matrix((right, -normal, up)).transposed().to_4x4()
    rotation.translation = center + normal * offset
    display.matrix_world = rotation
    display.data.clear_geometry()
    display.data.from_pydata([
        (-width / 2, 0, -height / 2), (width / 2, 0, -height / 2),
        (width / 2, 0, height / 2), (-width / 2, 0, height / 2),
    ], [], [(0, 1, 2, 3)])
    display.data.update()
    uv = display.data.uv_layers.new(name='UVMap')
    for loop, value in zip(uv.data, [(0, 0), (1, 0), (1, 1), (0, 1)]):
        loop.uv = value
    report = {
        'grid': [9, 7], 'tilt_degrees': float(np.degrees(np.arccos(-normal.y))),
        'rms_residual_mm': float(np.sqrt(np.mean(residuals ** 2)) * 1000),
        'max_residual_mm': maximum * 1000, 'glass_front_offset_mm': offset * 1000,
        'normal_gap_mm': [float(np.min(gaps) * 1000), float(np.max(gaps) * 1000)],
        'glass_size_m': [width, height], 'source_rectangle_inset_mm': [30, 4],
        'body_plane_blender_y_from_x_z': [float(a), float(b), float(c)],
    }
    (ROOT / 'art-source/terminal/screen-fit.json').write_text(json.dumps(report, indent=2) + '\n')
    print('SCREEN_FIT', json.dumps(report))


ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
OUTPUT = ROOT / 'assets/props/terminal/console.glb'
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
body = bpy.data.objects['ConsoleBody']
bpy.context.view_layer.objects.active = body
# glTF splits vertices at normal and UV boundaries. Decimating those disconnected
# faces punches holes in the shell, so restore connectivity before reduction.
topology = bmesh.new()
topology.from_mesh(body.data)
bmesh.ops.remove_doubles(topology, verts=list(topology.verts), dist=1e-7)
topology.to_mesh(body.data)
topology.free()
check_closed(body.data)
# High weights steer collapses away from the deck and its rounded lip.
weights = body.vertex_groups.new(name='Preserve deck contact')
for vertex in body.data.vertices:
    p = body.matrix_world @ vertex.co
    deck = p.y < -0.535 and 0.93 < p.z < 1.075
    weights.add([vertex.index], 0.0 if deck else 1.0, 'REPLACE')
modifier = body.modifiers.new('Game triangle budget', 'DECIMATE')
modifier.ratio = 48000 / len(body.data.polygons)
modifier.vertex_group = weights.name
modifier.vertex_group_factor = 1000.0
bpy.ops.object.modifier_apply(modifier=modifier.name)
check_closed(body.data)
body.data.calc_loop_triangles()
assert len(body.data.loop_triangles) <= 49998
fit_display(body, bpy.data.objects['DisplayPlane'])
# The runtime checks exercise support and screen rays on the imported result.
objects = [bpy.data.objects[name] for name in
           ['ConsoleBody', 'DisplayPlane', 'ScreenSocket', 'KeyboardSocket']]
bpy.ops.object.select_all(action='DESELECT')
for obj in objects:
    obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUTPUT), export_format='GLB',
                          use_selection=True, export_apply=True, export_yup=True)
print('GAME_CONSOLE_TRIANGLES', len(body.data.loop_triangles) + 2)
