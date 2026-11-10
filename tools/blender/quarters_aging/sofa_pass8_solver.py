"""Slow coarse cloth settings with per-frame area and tunnelling aborts."""
from collections import deque
import json
import time

import bpy
import numpy as np

from cloth_stage import calibrated_config, configure
from cloth_metrics import surface_metrics


def settings_for(obj, reference, fabric='upholstery', frames=900, quality=20):
    lengths = [(obj.data.vertices[e.vertices[0]].co-obj.data.vertices[e.vertices[1]].co).length for e in obj.data.edges]
    config = calibrated_config(fabric, float(np.median(lengths)), .2/9, frames)
    mass = config['mass']*reference/len(obj.data.vertices)
    scale = min(1., (.3*10/(2.4*9.81))/mass)
    for key in ['mass', 'stiffness', 'shear', 'bending']:
        config[key] *= scale
    config.update(quality=quality, time_scale=.5, self_collision=True, distance=.003,
                  self_distance=.003, collision_quality=6, shrink=0., shrink_min=0.,
                  damping_factor=5/12, air_factor=2., welt_bending=config['bending'],
                  mass_stiffness_scale=scale, terminal_speed_m_s=.3)
    return config


def cloth(obj, reference, fabric='upholstery', frames=900, quality=20, pins=None):
    config = settings_for(obj, reference, fabric, frames, quality)
    mod = configure(obj, config, reference, pins=pins)
    s = mod.settings
    s.tension_damping = s.compression_damping = s.shear_damping = 5
    s.bending_damping = .3
    # C2 measured v_terminal = 2.4*m*g/air at 24 fps and time_scale=0.5.
    # The proposed coefficient 100 is not the RNA setting's observed units.
    s.air_damping = 2.4*s.mass*9.81/.3
    s.bending_model = 'ANGULAR'
    if obj.vertex_groups.get('Welt'):
        s.bending_stiffness = 0.
        s.bending_stiffness_max = config['bending']
        config['weighted_bending_min'] = 0.
        config['weighted_bending_max'] = config['bending']
    config['bending_model'] = s.bending_model
    config['air_terminal_coefficient'] = 2.4
    config['structural_damping'] = 5.
    config['bending_damping'] = .3
    config['actual_air_damping'] = float(s.air_damping)
    config['actual_vertex_mass_kg'] = float(s.mass)
    if obj.vertex_groups.get('Self collision exclusion'):
        raise ValueError('Pass 8 forbids self-collision exclusion groups')
    return mod, config


def solve(obj, mod, out, label, frames=900, collapse_frames=180, settle=True):
    start = time.perf_counter()
    recent = deque(maxlen=6)
    samples = {}
    previous = None
    initial_area = None
    still = 0
    dt = mod.settings.time_scale/bpy.context.scene.render.fps
    substep = dt/mod.settings.quality
    result = {'frames': 0, 'settled': False, 'surface_samples': samples, 'controls': []}
    parts, initial_parts, initial_heights = {}, {}, {}
    for group in obj.vertex_groups:
        if group.name.startswith('Part '):
            parts[group.name[5:]] = np.array([any(g.group == group.index and g.weight > .5 for g in v.groups)
                                              for v in obj.data.vertices])
    try:
        for frame in range(1, frames+1):
            bpy.context.scene.frame_set(frame)
            deps = bpy.context.evaluated_depsgraph_get()
            evaluated = obj.evaluated_get(deps)
            p = np.array([evaluated.matrix_world@v.co for v in evaluated.data.vertices])
            if not np.isfinite(p).all():
                raise ValueError(f'{label} nonfinite vertices at {frame}')
            speed = 0. if previous is None else float(np.linalg.norm(p-previous, axis=1).max()/dt)
            recent.append(p.copy())
            motion = float(np.linalg.norm(p-recent[0], axis=1).max())
            if frame == 1 or frame % 20 == 0 or frame == frames:
                metrics = surface_metrics(evaluated)
                evaluated.data.calc_loop_triangles()
                face_ids = np.array([t.vertices[:] for t in evaluated.data.loop_triangles])
                t = p[face_ids]
                areas = np.linalg.norm(np.cross(t[:, 1]-t[:, 0], t[:, 2]-t[:, 0]), axis=1)/2
                metrics['area_m2'] = float(areas.sum())
                per_part = {}
                for name, mask in parts.items():
                    selected = mask[face_ids].all(1)
                    area = float(areas[selected].sum())
                    initial_parts.setdefault(name, area)
                    value = {'area_ratio': area/initial_parts[name],
                             'last_five_frames_motion_m': float(np.linalg.norm(p[mask]-recent[0][mask], axis=1).max())}
                    if name.startswith('Seat'):
                        from mathutils import Vector
                        from mathutils.bvhtree import BVHTree
                        tree = BVHTree.FromPolygons(p.tolist(), face_ids[selected].tolist(), all_triangles=True)
                        cx = (p[mask, 0].min()+p[mask, 0].max())/2 if frame == 1 else initial_heights[name]['cx']
                        heights = []
                        for x in np.linspace(cx-.08, cx+.08, 7):
                            for y in np.linspace(-.17, -.02, 7):
                                hit, _, _, _ = tree.ray_cast(Vector((x, y, 1.5)), Vector((0, 0, -1)))
                                if hit is not None:
                                    heights.append(hit.z-.3898)
                        height = float(np.median(heights)) if heights else None
                        initial_heights.setdefault(name, {'height': height, 'cx': cx})
                        value['centre_height_retained'] = height/initial_heights[name]['height'] if height is not None else None
                    per_part[name] = value
                metrics['parts'] = per_part
                if initial_area is None:
                    initial_area = metrics['area_m2']
                ratio = metrics['area_m2']/initial_area
                motion_index = int(np.linalg.norm(p-recent[0], axis=1).argmax())
                samples[str(frame)] = dict(metrics, max_speed_m_s=speed, substep_motion_m=speed*substep,
                                           area_ratio=ratio, last_five_frames_motion_m=motion,
                                           max_motion_vertex=motion_index, max_motion_world_m=p[motion_index].tolist(),
                                           max_motion_groups=[obj.vertex_groups[g.group].name for g in obj.data.vertices[motion_index].groups if g.weight > .5])
                check = {'frame': frame, 'C3_area_ratio': ratio, 'C3_part_ratios': {n: v['area_ratio'] for n, v in per_part.items()},
                         'C3_pass': abs(ratio-1) <= .03 and all(abs(v['area_ratio']-1) <= .03 for v in per_part.values()),
                         'C4_motion_per_substep_m': speed*substep, 'C4_pass': speed*substep <= .0015}
                result['controls'].append(check)
                print(label, frame, samples[str(frame)], flush=True)
                result['frames'] = frame
                if not check['C3_pass'] or not check['C4_pass']:
                    raise ValueError(f'{label} early control failed: {check}')
                if frame == 200 and label == 'seats':
                    high = {n: v['centre_height_retained'] for n, v in per_part.items()
                            if v['centre_height_retained'] is None or v['centre_height_retained'] > .45}
                    if high:
                        raise ValueError(f'Seat welt release needs lengthening at frame 200: {high}')
            result.update(frames=frame, last_five_frames_motion_m=motion, elapsed_s=time.perf_counter()-start)
            if settle and frame > collapse_frames and frame % 25 == 0:
                still = still+1 if motion < .001 else 0
                if still >= 3:
                    result['settled'] = True
                    break
            previous = p
        frozen = bpy.data.meshes.new_from_object(evaluated, depsgraph=deps)
        result['vertex_mass_kg'] = float(mod.settings.mass)
        obj.modifiers.clear()
        obj.shape_key_clear()
        obj.data = frozen
        result['pass'] = not settle or result['settled']
    except ValueError as error:
        result.update(error=str(error), **{'pass': False})
        raise
    finally:
        result['elapsed_s'] = time.perf_counter()-start
        (out/(label+'-solve.json')).write_text(json.dumps(result, indent=2)+'\n')
    return result
