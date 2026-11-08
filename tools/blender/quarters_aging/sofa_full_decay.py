"""Ordered dense-cloth sofa aging, with restartable per-cushion checkpoints.

All covers begin at the fitted pose. Only previously settled game surfaces
are neighbour colliders. This script never reads the sofa-k comparison bake.
"""
import argparse
import json
from pathlib import Path
import sys
import time

import bmesh
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bake_down import decimate
from cloth_metrics import lip_lift, save_surface, surface_metrics
from cloth_stage import calibrated_config, configure
from common import assert_collision_clear, collision, recalc, surface_tree
from densify import densify
from fabric_mesh import material, new_object
from foam_collapse import largest_shell
from sofa_partitions import clear_partitions, fitted_bounds, install_partitions
from sofa_decay_policy import DECK, FOAM, ORDER, UPHOLSTERY, cushion_plan

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT/'tools/blender/quarters/sofa/sofa-working.blend'


def checkpoint(out, record, name):
    bpy.context.scene['sofa_decay_record'] = json.dumps(record)
    (out/'simulation.json').write_text(json.dumps(record, indent=2)+'\n')
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(out/name))


def initialize():
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    for obj in bpy.context.scene.objects:
        obj.modifiers.clear()
        obj['aged_export'] = obj.type == 'MESH'
        if obj.name in {'Frame', 'Feet', 'Rivets'}:
            collision(obj, .001)
    bpy.ops.mesh.primitive_plane_add(size=8)
    floor = bpy.context.object
    floor.name = 'DecayFloor'
    floor['aged_export'] = False
    floor.hide_render = True
    collision(floor, .001)
    floor.collision.cloth_friction = 8
    return {'method': 'ordered, partitioned fitted source; each cover against final predecessor game meshes',
            'partition_fitted_bounds': {n: [p.min(0).tolist(), p.max(0).tolist()]
                                        for n, p in fitted_bounds().items()},
            'order': list(ORDER), 'cushions': {}, 'source': str(SOURCE),
            'production_calibrated': True, 'upholstery_albedo': UPHOLSTERY}


def residue_pair(obj, plan, source):
    data = np.load(source)
    cx = obj.matrix_world.translation.x
    scale = np.array([.93, .23, 2.5])*plan['residue_height_scale'] if plan['back'] else np.array([.93, .94, plan['residue_height_scale']])
    # Back filling collects in the lower third, on top of the settled seats.
    offset = np.array([cx, .245 if plan['back'] else -.035, .429 if plan['back'] else .391])
    def rippled(points):
        points = points*scale+offset
        local = points-offset
        phase = plan['seed']*.137
        if plan.get('residue_warp', True):
            points[:, 2] += .0045+.004*np.sin(local[:, 0]*240+phase)*np.sin(local[:, 1]*270)
        return points
    dense = new_object(obj.name+'_DenseResidue', rippled(data['vertices']),
                       data['faces'], material('Foam_Decay', FOAM))
    dense['aged_export'] = False
    dense.hide_render = True
    from residue_grid import balanced_grid
    proxy = new_object(obj.name+'_ResidueProxy', data['game_vertices']*scale+offset,
                       data['game_faces'], dense.data.materials[0])
    tree = surface_tree(proxy)
    bounds = np.array([v.co[:] for v in proxy.data.vertices])
    width, depth = np.ptp(bounds, axis=0)[:2]*.92
    def height(points):
        result = []
        for x, y in points:
            hit, _, _, _ = tree.ray_cast(Vector((x+offset[0], y+offset[1], 1.2)), Vector((0, 0, -1)))
            if hit is None:
                raise ValueError('Stable residue roof does not cover grid sample')
            result.append(hit.z-offset[2])
        return np.array(result)
    vertices, faces = balanced_grid(width, depth, height, plan['seed'], plan['back'])
    low = new_object(obj.name+'_Residue', vertices+offset, faces, dense.data.materials[0])
    report = {'method': 'balanced roof and underside sampled from stable residue control',
              'triangles': len(faces), 'target_triangles': 400 if plan['back'] else 700,
              'pass': len(faces) <= (400 if plan['back'] else 700)}
    low['aged_export'] = False
    low.hide_render = True
    bpy.data.objects.remove(proxy, do_unlink=True)
    collision(low, .0008)
    return dense, low, report


def envelope_for(obj, residue, plan):
    envelope = obj.copy()
    envelope.data = obj.data.copy()
    envelope.modifiers.clear()
    bpy.context.collection.objects.link(envelope)
    envelope.name = obj.name+'_Envelope'
    envelope['aged_export'] = False
    envelope.hide_render = True
    basis = envelope.shape_key_add(name='Fitted filling')
    collapsed = envelope.shape_key_add(name='Powder filling')
    tree = surface_tree(residue)
    points = np.array([obj.matrix_world@v.co for v in obj.data.vertices])
    bottom, top = points[:, 2].min(), points[:, 2].max()
    lo, hi = np.array([residue.matrix_world@v.co for v in residue.data.vertices]).min(0), np.array([residue.matrix_world@v.co for v in residue.data.vertices]).max(0)
    inverse = obj.matrix_world.inverted()
    for i, p in enumerate(points):
        basis.data[i].co -= obj.data.vertices[i].normal*.008
        fraction = float(np.clip((p[2]-bottom)/(top-bottom), 0, 1))
        if plan['back']:
            q = p.copy()
            q[1] = .245+(p[1]-.275)*.65
            hit, _, _, _ = tree.ray_cast(Vector((q[0], q[1], .8)), Vector((0, 0, -1)))
            height = hit.z if hit else lo[2]
            q[2] = lo[2]+fraction*(height-lo[2])
        else:
            hit, _, _, _ = tree.ray_cast(Vector((p[0], p[1], .8)), Vector((0, 0, -1)))
            height = hit.z if hit else .392
            q = np.array([p[0], p[1], .391+fraction*(height-.391)])
        collapsed.data[i].co = inverse@Vector(q)
    collapsed.value = 0
    collapsed.keyframe_insert(data_path='value', frame=1)
    collapsed.value = 1
    collapsed.keyframe_insert(data_path='value', frame=plan['collapse_frames'])
    for curve in envelope.data.shape_keys.animation_data.action.fcurves:
        for key in curve.keyframe_points:
            key.interpolation = 'LINEAR'
    collision(envelope, .0008)
    return envelope


def back_splits(obj, seed):
    from grain_paths import surface_walk
    from tear_paths import split_polyline
    cx = obj.matrix_world.translation.x
    paths = []
    for i, (z, y) in enumerate([(.81, .25), (.65, .18)]):
        paths.append(surface_walk(obj, (cx-.12, y, z), .16, seed+i*11,
                                  step=.004, direction=(1, 0, 0)))
    records = [split_polyline(obj, path) for path in paths]
    return {'method': 'two zero-area grain-gradient back splits', 'paths': records}


def open_cover_bottom(obj, back):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    if back:
        # The fitted front bulge has downward normals as far up as 650 mm.
        # A normal-based bottom cut removes that panel, so use the actual hem.
        remove = [f for f in bm.faces if max((obj.matrix_world@v.co).z for v in f.verts) < .432]
    else:
        remove = [f for f in bm.faces if f.normal.z < -.2 or
                  min((obj.matrix_world@v.co).z for v in f.verts) < .392]
    bmesh.ops.delete(bm, geom=remove, context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(obj.data)
    bm.free()


def prepare_cover(obj, plan, source):
    obj.modifiers.clear()
    largest_shell(obj)
    reference = len(obj.data.vertices)
    dense_residue, residue, reduction = residue_pair(obj, plan, source)
    envelope = envelope_for(obj, residue, plan)
    open_cover_bottom(obj, plan['back'])
    dense_report = densify(obj, levels=2)
    from sofa_contact_mesh import resolve_elements
    dense_report['contact_resolution'] = resolve_elements(obj)
    if plan['back']:
        tears = back_splits(obj, plan['seed'])
    else:
        from seat_tears import author
        tears = author(obj, obj.matrix_world.translation.x, plan['seed'])
    welt = obj.vertex_groups.new(name='Welt')
    exclusion = obj.vertex_groups.new(name='Self collision exclusion')
    for vertex in obj.data.vertices:
        p = obj.matrix_world@vertex.co
        wall = abs(vertex.normal.z) < .5
        welt.add([vertex.index], 1. if wall and p.z > (.80 if plan['back'] else .555) else .02 if wall else .5, 'REPLACE')
        if not wall and not plan['back'] and not plan.get('joint'):
            exclusion.add([vertex.index], 1., 'REPLACE')
    from split_contacts import exclude_split_contacts
    split_report = exclude_split_contacts(obj)
    rest = empty_rest(obj, plan)
    return {'reference_vertices': reference, 'dense': dense_report, 'tears': tears,
            'residue_decimation': reduction, 'split_contacts': split_report}, rest, envelope


def empty_rest(obj, plan):
    obj.shape_key_add(name='Fitted cover')
    rest = obj.shape_key_add(name='Empty cover rest angles')
    inverse = obj.matrix_world.inverted()
    for vertex in rest.data:
        p = obj.matrix_world@vertex.co
        if plan['back']:
            if p.z > .56:
                p.y = .32+(p.y-.32)*plan['rest_depth_scale']
        elif plan.get('rest_mode') == 'unroll':
            cx = obj.matrix_world.translation.x
            radial = Vector((p.x-cx, p.y+.035, 0))
            if radial.length:
                radial.normalize()
            extension = max(.555-p.z, 0)
            p += radial*extension
            p.z = .4
        elif plan.get('rest_mode') == 'compressed':
            p.z = .395+(p.z-.395)*plan['rest_height_scale']
        vertex.co = inverse@p
    if not plan['back'] and plan.get('rest_mode') == 'fitted':
        obj.shape_key_clear()
        rest = None
    return rest


def freeze_simulation(obj, mod, frames):
    durations, samples = [], {}
    start = time.perf_counter()
    previous = None
    for frame in range(1, frames+1):
        tick = time.perf_counter()
        bpy.context.scene.frame_set(frame)
        deps = bpy.context.evaluated_depsgraph_get()
        evaluated = obj.evaluated_get(deps)
        positions = np.array([v.co[:] for v in evaluated.data.vertices])
        durations.append(time.perf_counter()-tick)
        if frame == frames-5:
            previous = positions.copy()
        if frame == 1 or frame % 20 == 0 or frame == frames:
            samples[str(frame)] = surface_metrics(evaluated)
            print(obj.name, 'frame', frame, 'seconds', durations[-1], samples[str(frame)], flush=True)
    frozen = bpy.data.meshes.new_from_object(evaluated, depsgraph=deps)
    mass = float(mod.settings.mass)
    obj.modifiers.clear()
    obj.shape_key_clear()
    obj.data = frozen
    return {'frames': frames, 'elapsed_s': time.perf_counter()-start,
            'seconds_per_frame': float(np.mean(durations[1:])), 'vertex_mass_kg': mass,
            'last_five_frames_motion_m': float(np.linalg.norm(positions-previous, axis=1).max()),
            'surface_samples': samples}


def simulate_cushions(out, residue_source, resume=None, only=None, rest_mode='fitted', settings=None):
    if resume:
        bpy.ops.wm.open_mainfile(filepath=str(resume))
        record = json.loads(bpy.context.scene['sofa_decay_record'])
    else:
        record = initialize()
    start = time.perf_counter()
    for name in ORDER:
        if name in record['cushions']:
            continue
        plan = cushion_plan(name)
        plan['rest_mode'] = rest_mode
        if settings:
            for key in ['frames', 'collapse_frames', 'residue_height_scale', 'residue_warp']:
                if key in settings:
                    plan[key] = settings[key]
        bpy.context.scene.frame_set(1)
        for obj in bpy.context.scene.objects:
            if obj.name in ORDER or obj.name.endswith('_GameContact'):
                for mod in list(obj.modifiers):
                    if mod.type == 'COLLISION':
                        obj.modifiers.remove(mod)
        for previous in plan['settled_contacts']:
            collision(bpy.data.objects[previous+'_GameContact'], .001)
        obj = bpy.data.objects[name]
        detail, rest, envelope = prepare_cover(obj, plan, residue_source)
        detail['partitions'] = install_partitions(
            {n: np.array(p) for n, p in record['partition_fitted_bounds'].items()}, plan['back'])
        if not plan['back']:
            from sofa_partitions import fitted_back_barriers
            detail['fitted_back_barriers'] = fitted_back_barriers()
        if plan['back']:
            from sofa_decay_joint import carrier_surface
            rest, carrier_report = carrier_surface(obj, plan)
            detail['rest_carrier'] = carrier_report
            carrier = obj.modifiers.new('Empty cover rest carrier', 'SUBSURF')
            carrier.levels = carrier.render_levels = 1
            carrier.subdivision_type = 'SIMPLE'
            carrier.uv_smooth = 'PRESERVE_BOUNDARIES'
        bpy.context.scene.frame_set(1)
        bpy.context.view_layer.update()
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        assert_collision_clear(evaluated)
        evaluated_count = len(evaluated.data.vertices)
        config = calibrated_config('upholstery', .2/34, .2/9, plan['frames'])
        config.update(self_collision=True, shrink=.05, quality=16, collision_quality=4,
                      distance=.0015, time_scale=.5, welt_bending=3.2, self_distance=.001)
        if settings:
            config.update({k: v for k, v in settings.items() if k not in {'collapse_frames', 'residue_height_scale', 'residue_warp'}})
        mod = configure(obj, config, detail['reference_vertices'], rest_shape=rest)
        if obj.vertex_groups.get('Lip relaxation'):
            mod.settings.vertex_group_shrink = 'Lip relaxation'
        mod.settings.mass = config['mass']*detail['reference_vertices']/evaluated_count
        checkpoint(out, record, name+'-prepared.blend')
        result = freeze_simulation(obj, mod, plan['frames'])
        detail.update(plan=plan, settings=config, simulation=result, dense_metrics=surface_metrics(obj), G5=lip_lift(obj))
        save_surface(obj, out/(name+'-dense.npz'))
        save_surface(bpy.data.objects[name+'_DenseResidue'], out/(name+'-dense-residue.npz'))
        save_surface(bpy.data.objects[name+'_Residue'], out/(name+'-game-residue.npz'))
        low, report = decimate(obj, 2000 if plan['back'] else 2400)
        low.name = name+'_GameContact'
        low['aged_export'] = False
        low.hide_render = True
        detail['cover_decimation'] = report
        detail['game_metrics'] = surface_metrics(low)
        save_surface(low, out/(name+'-game.npz'))
        bpy.data.objects.remove(envelope, do_unlink=True)
        record['cushions'][name] = detail
        if name == 'SeatCushion_C':
            from sofa_partitions import pair_crossings
            count = pair_crossings(bpy.data.objects['SeatCushion_R'], low)
            if count:
                raise ValueError(f'Partition control: fitted right crosses settled centre {count} times')
            record['partition_control'] = {
                'centre_settled_right_fitted_initial_SAT_crossings': count}
            print('PARTITION_CONTROL centre settled/right fitted: zero initial SAT crossings', flush=True)
        clear_partitions()
        record['elapsed_s_this_invocation'] = time.perf_counter()-start
        checkpoint(out, record, name+'-settled.blend')
        print('CUSHION_COMPLETE', name, result['elapsed_s'], flush=True)
        if only == name:
            break
    checkpoint(out, record, 'cushions.blend')
    return record


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, default=ROOT/'tmp/age/pass6')
    p.add_argument('--residue', type=Path, default=ROOT/'tmp/age/pass5/residue-stable/seat-residue.npz')
    p.add_argument('--resume', type=Path)
    p.add_argument('--only', choices=ORDER)
    p.add_argument('--rest-mode', choices=['fitted', 'unroll', 'compressed'], default='fitted')
    p.add_argument('--settings', type=Path)
    args = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    args.out.mkdir(parents=True, exist_ok=True)
    settings = json.loads(args.settings.read_text()) if args.settings else None
    simulate_cushions(args.out, args.residue, args.resume, args.only, args.rest_mode, settings)


if __name__ == '__main__':
    main()
