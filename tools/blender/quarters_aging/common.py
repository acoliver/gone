"""Shared baked-mesh and cloth operations, in Blender's native Z-up frame."""
import json
from pathlib import Path

import bpy
import bmesh
import numpy as np
from mathutils.bvhtree import BVHTree

FIBRE_THICKNESS_FACTOR = .04


def activate(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def apply(obj, modifier):
    activate(obj)
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def surface_tree(obj):
    obj.data.calc_loop_triangles()
    return BVHTree.FromPolygons([obj.matrix_world @ v.co for v in obj.data.vertices],
                               [tuple(t.vertices) for t in obj.data.loop_triangles], all_triangles=True)


def recalc(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def midsurface(obj):
    """Undo the baked Solidify layout while keeping pattern UVs and object pivots."""
    mesh = obj.data
    n = len(mesh.vertices) // 2
    if len(mesh.vertices) % 2:
        raise ValueError(f'{obj.name}: expected paired Solidify vertices')
    positions = [(mesh.vertices[i].co + mesh.vertices[i + n].co) / 2 for i in range(n)]
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=list(bm.verts)[n:], context='VERTS')
    bm.verts.ensure_lookup_table()
    for i, point in enumerate(positions):
        bm.verts[i].co = point
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()


def solidify(obj, thickness):
    mod = obj.modifiers.new('Brittle fabric thickness', 'SOLIDIFY')
    mod.thickness = thickness
    mod.offset = 0
    mod.use_even_offset = False
    if obj.vertex_groups.get('Aging thickness'):
        mod.vertex_group = 'Aging thickness'
        mod.thickness_vertex_group = FIBRE_THICKNESS_FACTOR
    apply(obj, mod)
    recalc(obj)


def collision(obj, distance=.001):
    mod = obj.modifiers.new('Aging collision', 'COLLISION')
    obj.collision.thickness_outer = distance
    obj.collision.thickness_inner = .0005
    obj.collision.cloth_friction = 15
    return mod


def settle(obj, settings, pins, pressure=None):
    scene = bpy.context.scene
    scene.frame_set(1)
    obj.vertex_groups.clear()
    group = obj.vertex_groups.new(name='Retained aging stitches')
    for index, weight in pins.items():
        group.add([index], float(weight), 'REPLACE')
    mod = obj.modifiers.new('Aging gravity settle', 'CLOTH')
    s = mod.settings
    s.quality = settings['quality']
    s.time_scale = settings['time_scale']
    s.mass = settings['mass']
    s.tension_stiffness = settings['stiffness']
    s.compression_stiffness = settings['stiffness']
    s.shear_stiffness = settings['stiffness'] * .7
    s.bending_stiffness = settings['bending']
    s.tension_damping = 12
    s.compression_damping = 12
    s.shear_damping = 12
    s.bending_damping = 3
    s.air_damping = 5
    s.vertex_group_mass = group.name
    if pressure is not None:
        s.use_pressure = True
        s.uniform_pressure_force = pressure
        s.pressure_factor = 1
    c = mod.collision_settings
    c.use_self_collision = settings.get('self_collision', True)
    c.self_distance_min = settings.get('self_distance_m', .003)
    c.distance_min = settings.get('collision_distance_m', .002)
    c.collision_quality = settings.get('collision_quality', 8)
    frames = settings['frames']
    mod.point_cache.frame_start = 1
    mod.point_cache.frame_end = frames
    previous = None
    movement = None
    for frame in range(1, frames + 1):
        scene.frame_set(frame)
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        if frame in (frames - 5, frames):
            positions = np.array([v.co[:] for v in evaluated.data.vertices])
            if previous is not None:
                movement = float(np.linalg.norm(positions - previous, axis=1).max())
            previous = positions
        if frame % 10 == 0:
            print(obj.name, 'frame', frame, flush=True)
    apply(obj, mod)
    return {'frames': frames, 'retained_pins': len(pins), 'last_five_frames_motion_m': movement}


def export(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    bpy.ops.object.select_all(action='DESELECT')
    meshes = sorted((o for o in bpy.context.scene.objects if o.type == 'MESH' and o.get('aged_export', False)), key=lambda o: o.name)
    if not meshes or any(o.modifiers for o in meshes):
        raise ValueError('Export requires baked, explicitly selected aged meshes')
    for obj in meshes:
        obj.hide_set(False)
        obj.data.name = obj.name
        obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
                              export_yup=True, export_apply=False, export_materials='EXPORT',
                              export_cameras=False, export_lights=False, export_all_vertex_colors=True)


def save(path, record):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    for obj in bpy.context.scene.objects:
        for mod in list(obj.modifiers):
            if mod.type == 'COLLISION':
                obj.modifiers.remove(mod)
    bpy.context.scene.frame_set(1)
    bpy.context.scene['aging_record'] = json.dumps(record)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
