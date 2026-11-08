"""Collapse all six fitted covers in one dense self-colliding cloth system."""
import argparse
from pathlib import Path
import sys

import bmesh
import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bake_down import decimate
from cloth_metrics import lip_lift, save_surface, surface_metrics
from cloth_stage import calibrated_config, configure
from common import assert_collision_clear, assert_surface_clear, recalc
from fabric_mesh import new_object
from sofa_decay_policy import ORDER, cushion_plan
from sofa_full_decay import ROOT, checkpoint, empty_rest, freeze_simulation, initialize, prepare_cover


def carrier_surface(obj, plan):
    obj.data.calc_loop_triangles()
    source_count = len(obj.data.loop_triangles)
    # A subdivided triangle produces six solved triangles. Reduce the base
    # first so the real modifier does not multiply the calibrated density.
    carrier, report = decimate(obj, max(100, source_count//6))
    obj.shape_key_clear()
    obj.data = carrier.data.copy()
    bpy.data.objects.remove(carrier, do_unlink=True)
    return empty_rest(obj, plan), report


def restore_part(joint, obj):
    bpy.context.view_layer.update()
    group = joint.vertex_groups['Part '+obj.name].index
    bm = bmesh.new()
    bm.from_mesh(joint.data)
    deform = bm.verts.layers.deform.active
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v[deform].get(group, 0) < .5], context='VERTS')
    inverse = obj.matrix_world.inverted()
    for vertex in bm.verts:
        vertex.co = inverse@vertex.co
    obj.shape_key_clear()
    obj.vertex_groups.clear()
    names = [source_group.name for source_group in joint.vertex_groups]
    mesh = bpy.data.meshes.new(obj.name+'_Solved')
    bm.to_mesh(mesh)
    bm.free()
    obj.data = mesh
    for name in names:
        obj.vertex_groups.new(name=name)
    obj.data.materials.append(joint.data.materials[0])
    recalc(obj)


def run(out, residue, frames=420, collapse_frames=300, rest_mode='fitted'):
    out.mkdir(parents=True, exist_ok=True)
    record = initialize()
    record['method'] = 'joint six-cover cloth; full inter-cover self collision; all fitted at frame one'
    record['order'] = None
    states = []
    for index, name in enumerate(ORDER):
        plan = cushion_plan(name)
        plan.update(joint=True, rest_mode=rest_mode, residue_warp=False,
                    frames=frames, collapse_frames=collapse_frames, settled_contacts=[])
        if not plan['back']:
            plan['residue_height_scale'] = (1., .85, 1.10)[index]
        obj = bpy.data.objects[name]
        detail, rest, envelope = prepare_cover(obj, plan, residue)
        rest, reduction = carrier_surface(obj, plan)
        detail['carrier_reduction'] = reduction
        # A settled back residue intersects an inflated seat. Its animated
        # filling envelope supplies that contact until both have collapsed.
        for modifier in list(bpy.data.objects[name+'_Residue'].modifiers):
            if modifier.type == 'COLLISION':
                bpy.data.objects[name+'_Residue'].modifiers.remove(modifier)
        detail['filling_contact'] = 'animated fitted-to-residue envelope; no prematurely settled back collider'
        states.append((obj, detail, rest, envelope, plan))
    vertices, faces, patterns, slices = [], [], [], {}
    weights = {name: {} for name in ['Welt', 'Lip shrink', 'Self collision exclusion']}
    reference = 0
    rest_points = []
    for obj, detail, rest, _, plan in states:
        start = len(vertices)
        vertices.extend(tuple(obj.matrix_world@v.co) for v in obj.data.vertices)
        rest_points.extend(tuple(obj.matrix_world@v.co) for v in (rest.data if rest else obj.data.vertices))
        slices[obj.name] = (start, len(vertices))
        for face in obj.data.polygons:
            faces.append(tuple(start+i for i in face.vertices))
            patterns.append([tuple(obj.data.uv_layers.active.data[i].uv) for i in face.loop_indices])
        for group_name in weights:
            group = obj.vertex_groups.get(group_name)
            if group:
                for vertex in obj.data.vertices:
                    values = [g.weight for g in vertex.groups if g.group == group.index]
                    if values:
                        weights[group_name][start+vertex.index] = values[0]
        reference += detail['reference_vertices']
        obj.hide_render = True
        obj['aged_export'] = False
    joint = new_object('JointDenseCushionCovers', vertices, faces, states[0][0].data.materials[0])
    joint['aged_export'] = False
    for face, pattern in zip(joint.data.polygons, patterns):
        for index, uv in zip(face.loop_indices, pattern):
            joint.data.uv_layers.active.data[index].uv = uv
    for name, values in weights.items():
        group = joint.vertex_groups.new(name=name)
        for index, weight in values.items():
            group.add([index], weight, 'REPLACE')
    for name, (start, end) in slices.items():
        joint.vertex_groups.new(name='Part '+name).add(list(range(start, end)), 1., 'REPLACE')
    joint.shape_key_add(name='Fitted covers')
    rest = joint.shape_key_add(name='Empty cover rest')
    for vertex, p in zip(rest.data, rest_points):
        vertex.co = p
    joint.data.calc_loop_triangles()
    shapes = [np.array(vertices), np.array(rest_points)]
    unresolved = set()
    for triangle in joint.data.loop_triangles:
        ids = np.array(triangle.vertices)
        for shape in shapes:
            p = shape[ids]
            lengths = np.linalg.norm(p-np.roll(p, 1, axis=0), axis=1)
            altitude = np.linalg.norm(np.cross(p[1]-p[0], p[2]-p[0]))/lengths.max()
            if altitude < .004:
                unresolved.update(ids.tolist())
    if unresolved:
        joint.vertex_groups['Self collision exclusion'].add(sorted(unresolved), 1., 'REPLACE')
    carrier = joint.modifiers.new('Rest coordinates to cloth', 'SUBSURF')
    carrier.levels = carrier.render_levels = 1
    # The covers were smoothed before splitting. Smoothing their coincident
    # lips independently here can make opposite sides cross at frame one.
    carrier.subdivision_type = 'SIMPLE'
    carrier.quality = 3
    carrier.uv_smooth = 'PRESERVE_BOUNDARIES'
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    evaluated = joint.evaluated_get(bpy.context.evaluated_depsgraph_get())
    evaluated_count = len(evaluated.data.vertices)
    evaluated.data.calc_loop_triangles()
    evaluated_triangles = len(evaluated.data.loop_triangles)
    assert_surface_clear(evaluated)
    assert_collision_clear(evaluated)
    config = calibrated_config('upholstery', .2/34, .2/9, frames)
    config.update(self_collision=True, shrink=.04, quality=16, collision_quality=4,
                  distance=.0015, time_scale=.5, welt_bending=3.2, self_distance=.001)
    mod = configure(joint, config, reference, rest_shape=rest)
    mod.settings.mass = config['mass']*reference/evaluated_count
    record['joint_setup'] = {'base_vertices': len(vertices), 'evaluated_vertices': evaluated_count,
                             'evaluated_triangles': evaluated_triangles, 'reference_vertices': reference,
                             'parts': list(ORDER), 'self_collision': 'all panels except split bands and sub-diameter faces',
                             'sub_diameter_base_vertices': len(unresolved), 'base_altitude_threshold_m': .004,
                             'rest_key_carrier': 'real level-1 Subdivision before Cloth; folded-rest control verified',
                             'vertex_mass_kg': float(mod.settings.mass), 'settings': config}
    record['prepared_cushions'] = {obj.name: dict(detail, plan=plan) for obj, detail, _, _, plan in states}
    checkpoint(out, record, 'joint-prepared.blend')
    result = freeze_simulation(joint, mod, frames)
    record['joint_simulation'] = result
    checkpoint(out, record, 'joint-solved.blend')
    return finish(out, record)


def finish(out, record):
    joint = bpy.data.objects['JointDenseCushionCovers']
    config = record['joint_setup']['settings']
    result = record['joint_simulation']
    for name in ORDER:
        obj = bpy.data.objects[name]
        detail = record['prepared_cushions'][name]
        plan = detail['plan']
        restore_part(joint, obj)
        detail.update(plan=plan, settings=config, simulation={'shared_joint': True, 'frames': result['frames'], 'elapsed_s': result['elapsed_s']},
                      dense_metrics=surface_metrics(obj), G5=lip_lift(obj))
        save_surface(obj, out/(name+'-dense.npz'))
        save_surface(bpy.data.objects[name+'_DenseResidue'], out/(name+'-dense-residue.npz'))
        save_surface(bpy.data.objects[name+'_Residue'], out/(name+'-game-residue.npz'))
        low, reduction = decimate(obj, 2000 if plan['back'] else 2400)
        low.name = name+'_GameContact'
        low['aged_export'] = False
        low.hide_render = True
        detail['cover_decimation'] = reduction
        detail['game_metrics'] = surface_metrics(low)
        save_surface(low, out/(name+'-game.npz'))
        bpy.data.objects.remove(bpy.data.objects[name+'_Envelope'], do_unlink=True)
        record['cushions'][name] = detail
    bpy.data.objects.remove(joint, do_unlink=True)
    checkpoint(out, record, 'cushions.blend')
    return record


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, default=ROOT/'tmp/age/pass6/joint')
    p.add_argument('--residue', type=Path, default=ROOT/'tmp/age/pass5/residue-stable/seat-residue.npz')
    p.add_argument('--frames', type=int, default=420)
    p.add_argument('--collapse-frames', type=int, default=300)
    p.add_argument('--finish', type=Path)
    p.add_argument('--rest-mode', choices=['fitted', 'unroll', 'compressed'], default='fitted')
    a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    if a.finish:
        import json
        bpy.ops.wm.open_mainfile(filepath=str(a.finish))
        finish(a.out, json.loads(bpy.context.scene['sofa_decay_record']))
    else:
        run(a.out, a.residue, a.frames, a.collapse_frames, a.rest_mode)
