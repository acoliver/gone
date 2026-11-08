"""Provide Blender cloth with evaluated rest coordinates at the calibrated density."""
import bpy

from bake_down import decimate
from common import assert_collision_clear, assert_surface_clear


def prepare_carrier(body, target=5000):
    carrier, report = decimate(body, target)
    mesh = carrier.data.copy()
    names = [group.name for group in carrier.vertex_groups]
    body.shape_key_clear()
    body.vertex_groups.clear()
    body.data = mesh
    for name in names:
        body.vertex_groups.new(name=name)
    bpy.data.objects.remove(carrier, do_unlink=True)
    return report


def add_rest_carrier(body):
    modifier = body.modifiers.new('Evaluated wool rest coordinates', 'SUBSURF')
    modifier.subdivision_type = 'SIMPLE'
    modifier.levels = modifier.render_levels = 1
    modifier.uv_smooth = 'PRESERVE_BOUNDARIES'
    return modifier


def evaluated_binding_surface(body):
    deps = bpy.context.evaluated_depsgraph_get()
    evaluated = body.evaluated_get(deps)
    assert_surface_clear(evaluated)
    assert_collision_clear(evaluated)
    mesh = bpy.data.meshes.new_from_object(evaluated, depsgraph=deps)
    result = bpy.data.objects.new('Tunic dense attachment surface', mesh)
    bpy.context.collection.objects.link(result)
    result.matrix_world = body.matrix_world.copy()
    for group in body.vertex_groups:
        result.vertex_groups.new(name=group.name)
    result['aged_export'] = False
    return result
