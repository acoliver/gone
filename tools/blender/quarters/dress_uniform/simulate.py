"""Sew flat tunic patterns, settle them on a hanger, and retain the baked surface."""
import argparse
import json
import math
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SCRATCH = ROOT / 'tmp/fit/tunic/sim'


def mesh_object(name, vertices, faces, edges=()):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, edges, faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def activate(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def collider(obj):
    activate(obj)
    obj.modifiers.new('ClothCollision', 'COLLISION')
    obj.collision.thickness_outer = .001
    obj.collision.thickness_inner = .001
    obj.collision.cloth_friction = 15
    obj.hide_render = True
    obj['export'] = False


def tube(name, points, radius=.0035, sides=8):
    vertices, faces = [], []
    for i, p in enumerate(points):
        tangent = Vector(points[min(i + 1, len(points) - 1)]) - Vector(points[max(0, i - 1)])
        tangent.normalize()
        u = tangent.cross(Vector((0, 1, 0))).normalized()
        v = tangent.cross(u).normalized()
        for j in range(sides):
            q = Vector(p) + radius * (math.cos(2 * math.pi * j / sides) * u + math.sin(2 * math.pi * j / sides) * v)
            vertices.append(tuple(q))
        if i:
            for j in range(sides):
                a = (i - 1) * sides + j
                b = (i - 1) * sides + (j + 1) % sides
                faces.append((a, b, b + sides, a + sides))
    faces.extend([tuple(reversed(range(sides))), tuple((len(points) - 1) * sides + j for j in range(sides))])
    return mesh_object(name, vertices, faces)


def setup():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.render.fps = 24
    scene.frame_end = 180
    # Only the upper chest is supported; the waist and hem remain free.
    bpy.ops.mesh.primitive_uv_sphere_add(segments=40, ring_count=20, location=(0, 0, -.285))
    form = bpy.context.object
    form.name = 'ShoulderChestForm'
    form.scale = (.224, .050, .125)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    collider(form)
    points = [(-.25, 0, -.215), (-.20, 0, -.186), (-.10, 0, -.15), (0, 0, -.14), (.10, 0, -.15), (.20, 0, -.186), (.25, 0, -.215), (.24, 0, -.235), (-.24, 0, -.235), (-.25, 0, -.215)]
    hanger = tube('Hanger', points)
    # Hook top is precisely z=0 including the wire radius.
    hook = [(0, 0, -.14), (0, 0, -.072)]
    for i in range(25):
        a = math.pi - 1.55 * math.pi * i / 24
        hook.append((.026 + .026 * math.cos(a), 0, -.0295 + .026 * math.sin(a)))
    hook_obj = tube('Hook', hook)
    activate(hanger)
    hook_obj.select_set(True)
    bpy.ops.object.join()
    hanger.name = 'Hanger'
    hanger.data.name = 'Hanger'
    hanger['export'] = True
    collider(hanger)
    hanger['export'] = True
    hanger.hide_render = False


def pattern():
    nx, nz = 28, 30
    vertices, faces, uv, pairs, pins = [], [], [], [], []
    ids = []
    for panel in range(2):
        grid = []
        for j in range(nz + 1):
            t = j / nz
            row = []
            width = .24 + .035 * max(0, (t - .72) / .28)
            for i in range(nx + 1):
                x = width * (2 * i / nx - 1)
                ax = abs(x)
                top = -.178 if ax < .079 else -.15 - .065 * max(0, (ax - .09) / .185)
                z = -.90 + (top + .90) * t
                row.append(len(vertices))
                vertices.append((x, -.064 if panel == 0 else .064, z))
                uv.append((i / nx * .46 + panel * .51, j / nz * .94))
                if j >= nz - 1 and ax >= .09:
                    pins.append(len(vertices) - 1)
            grid.append(row)
        ids.append(grid)
        for j in range(nz):
            for i in range(nx):
                q = (grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i])
                faces.append(q if panel == 0 else tuple(reversed(q)))
    for j in range(nz + 1):
        for i in (0, nx):
            if vertices[ids[0][j][i]][2] <= -.365:
                pairs.append((ids[0][j][i], ids[1][j][i]))
    for i in range(nx + 1):
        if abs(vertices[ids[0][-1][i]][0]) >= .09:
            pairs.append((ids[0][-1][i], ids[1][-1][i]))
    obj = mesh_object('Pattern', vertices, faces, pairs)
    layer = obj.data.uv_layers.new(name='FlatPattern')
    for loop in obj.data.loops:
        layer.data[loop.index].uv = uv[loop.vertex_index]
    base = obj.shape_key_add(name='FlatCut')
    goal = obj.shape_key_add(name='ShoulderPlacement')
    top_pins = {index for grid in ids for index in grid[-1]}
    for index in pins:
        front = vertices[index][1] < 0
        if index in top_pins:
            goal.data[index].co.y = -.0005 if front else .0005
            goal.data[index].co.z += .012
        else:
            x = abs(vertices[index][0])
            top = -.15 - .065 * max(0, (x - .09) / .185)
            goal.data[index].co.y = -.014 if front else .014
            goal.data[index].co.z = top + .012 - .020
    goal.value = 0
    goal.keyframe_insert('value', frame=1)
    goal.value = 1
    goal.keyframe_insert('value', frame=25)
    group = obj.vertex_groups.new(name='HangerPins')
    group.add(pins, 1, 'REPLACE')
    interfacing = obj.vertex_groups.new(name='InterfacedPlacket')
    interfacing.add([index for row in ids[0] for index in row if abs(vertices[index][0]) < .022], 1, 'REPLACE')
    return obj, {'seams': pairs, 'hem': ids[0][0] + ids[1][0], 'grids': ids, 'pins': pins, 'uv': uv}


def cloth(obj, args, bending_group=''):
    mod = obj.modifiers.new('SewnWool', 'CLOTH')
    s = mod.settings
    s.quality = args.quality
    s.time_scale = .25
    s.mass = .22
    s.tension_stiffness = 500
    s.compression_stiffness = 500
    s.shear_stiffness = 350
    s.bending_stiffness = args.bending
    s.bending_stiffness_max = 5
    s.vertex_group_bending = bending_group
    s.tension_damping = 5
    s.compression_damping = 5
    s.shear_damping = 5
    s.bending_damping = .5
    s.air_damping = 10
    s.use_sewing_springs = True
    s.sewing_force_max = args.sewing
    s.vertex_group_mass = 'HangerPins'
    c = mod.collision_settings
    c.use_self_collision = True
    c.collision_quality = 6
    c.distance_min = .004
    c.self_distance_min = .004
    c.self_friction = 10
    seam_vertices = set()
    for edge in obj.data.edges:
        if edge.is_loose:
            seam_vertices.update(edge.vertices)
    excluded = set(seam_vertices)
    for polygon in obj.data.polygons:
        if any(i in seam_vertices for i in polygon.vertices):
            excluded.update(polygon.vertices)
    # This Blender group excludes triangles, so sewing plies can meet without repelling.
    stitch_exclusions = obj.vertex_groups.new(name='StitchCollisionExclusions')
    if excluded:
        stitch_exclusions.add(sorted(excluded), 1, 'REPLACE')
    c.vertex_group_self_collisions = stitch_exclusions.name
    mod.point_cache.frame_end = args.frames
    obj['cloth_settings'] = json.dumps({
        'quality': s.quality, 'time_scale': s.time_scale, 'mass_setting': s.mass,
        'tension_compression_shear': [s.tension_stiffness, s.compression_stiffness, s.shear_stiffness],
        'bending': s.bending_stiffness, 'interfacing_bending_max': s.bending_stiffness_max,
        'bending_group': s.vertex_group_bending, 'structural_damping': s.tension_damping,
        'bending_damping': s.bending_damping, 'air_damping': s.air_damping,
        'sewing_force_max': s.sewing_force_max, 'self_collision': c.use_self_collision,
        'collision_distance_m': c.distance_min, 'self_distance_m': c.self_distance_min,
    })
    return mod


def measure(vertices, metadata, previous):
    v = np.array(vertices)
    mins, maxs = v.min(0), v.max(0)
    chest = v[(v[:, 2] > -.45) & (v[:, 2] < -.37)]
    waist = v[(v[:, 2] > -.70) & (v[:, 2] < -.60)]
    seam = max(np.linalg.norm(v[a] - v[b]) for a, b in metadata['seams'])
    hem = v[metadata['hem'], 2]
    return {'extents_blender_m': (maxs - mins).tolist(), 'bounds_blender_m': [mins.tolist(), maxs.tolist()], 'hem_level_range_m': float(np.ptp(hem)), 'waist_chest_width_ratio': float(np.ptp(waist[:, 0]) / np.ptp(chest[:, 0])), 'sewing_spring_gap_max_m': float(seam), 'last_five_frames_displacement_m': float(np.linalg.norm(v - previous, axis=1).max())}


def body(args):
    setup()
    obj, metadata = pattern()
    mod = cloth(obj, args, 'InterfacedPlacket')
    deps = bpy.context.evaluated_depsgraph_get()
    previous = None
    for frame in range(1, args.frames + 1):
        bpy.context.scene.frame_set(frame)
        evaluated = obj.evaluated_get(deps)
        positions = [tuple(v.co) for v in evaluated.data.vertices]
        if frame == args.frames - 5:
            previous = np.array(positions)
        if frame % 10 == 0:
            print('frame', frame, flush=True)
    metrics = measure(positions, metadata, previous)
    print(json.dumps(metrics), flush=True)
    # Retain the original pattern, UVs and sewing edges as an editable source.
    source = obj.copy()
    source.data = obj.data.copy()
    bpy.context.collection.objects.link(source)
    source.name = 'FlatPatternSource'
    source.modifiers.clear()
    source.hide_viewport = True
    source.hide_render = True
    source['export'] = False
    activate(obj)
    baked = bpy.data.meshes.new_from_object(obj.evaluated_get(deps), depsgraph=deps)
    obj.modifiers.clear()
    obj.data = baked
    obj.name = 'BakedBodyPattern'
    obj['export'] = False
    (SCRATCH / f'{args.trial}-body.json').write_text(json.dumps({'metadata': metadata, 'metrics': metrics, 'positions': positions}, indent=2))
    bpy.context.scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(SCRATCH / f'{args.trial}-body.blend'))
    trials_path = HERE / 'cloth-trials.json'
    trials = json.loads(trials_path.read_text()) if trials_path.exists() else {'body': [], 'sleeves': [], 'details': []}
    trials['body'].append({'trial': args.trial, 'pattern': {'shoulder_m': .55, 'chest_half_circumference_m': .48, 'shoulder_to_hem_m': .75, 'grid_each_panel': [28, 30]}, 'settings': {**vars(args), **json.loads(obj['cloth_settings'])}, 'metrics': metrics, 'method': 'Flat front/back XZ patterns, sewing loose edges at sides and shoulders, animated shoulder placement pins; no waist support.'})
    trials_path.write_text(json.dumps(trials, indent=2) + '\n')


if __name__ == '__main__':
    SCRATCH.mkdir(parents=True, exist_ok=True)
    parser = argparse.ArgumentParser()
    parser.add_argument('--trial', default='body-p')
    parser.add_argument('--frames', type=int, default=600)
    parser.add_argument('--quality', type=int, default=30)
    parser.add_argument('--bending', type=float, default=.3)
    parser.add_argument('--sewing', type=float, default=10)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    body(args)
