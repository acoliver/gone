"""Reduce the supplied standing console to the game's prop budget.

Run with Blender --background --factory-startup --python this_file -- SOURCE.glb.
The placement JSON and standalone keyboard remain unchanged.
"""
from pathlib import Path
import sys

import bmesh
import bpy


def check_closed(mesh):
    topology = bmesh.new()
    topology.from_mesh(mesh)
    nonmanifold_edges = sum(not edge.is_manifold for edge in topology.edges)
    topology.free()
    assert nonmanifold_edges == 0, f'Console shell has {nonmanifold_edges} nonmanifold edges'


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
# The runtime checks exercise support and screen rays on the imported result.
objects = [bpy.data.objects[name] for name in
           ['ConsoleBody', 'DisplayPlane', 'ScreenSocket', 'KeyboardSocket']]
bpy.ops.object.select_all(action='DESELECT')
for obj in objects:
    obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUTPUT), export_format='GLB',
                          use_selection=True, export_apply=True, export_yup=True)
print('GAME_CONSOLE_TRIANGLES', len(body.data.loop_triangles) + 2)
