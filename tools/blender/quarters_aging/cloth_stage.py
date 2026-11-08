"""Dense-cloth setup with explicit groups, per-vertex mass and measured frame costs."""
import time

import bpy
import numpy as np

from common import apply


def configure(obj, config, reference_vertices, pins=None, rest_shape=None):
    if reference_vertices <= 0:
        raise ValueError('A positive unaged vertex count is required for mass scaling')
    mod = obj.modifiers.new('Dense aging cloth', 'CLOTH')
    s = mod.settings
    s.quality = config.get('quality', 10)
    s.time_scale = 1
    s.mass = config['mass'] * reference_vertices / len(obj.data.vertices)
    s.tension_stiffness = config['stiffness']
    s.compression_stiffness = config['stiffness']
    s.shear_stiffness = config.get('shear', config['stiffness']*.7)
    s.bending_stiffness = config['bending']
    s.tension_damping = 12
    s.compression_damping = 12
    s.shear_damping = 12
    s.bending_damping = 3
    s.air_damping = 5
    s.use_pressure = False
    if pins:
        group = obj.vertex_groups.new(name='Retained stitches')
        for index, weight in pins.items():
            group.add([index], weight, 'REPLACE')
        s.vertex_group_mass = group.name
    if obj.vertex_groups.get('Lip shrink'):
        s.vertex_group_shrink = 'Lip shrink'
        s.shrink_min = config.get('shrink', .04)
        s.shrink_max = config.get('shrink', .04)
    if obj.vertex_groups.get('Welt'):
        s.vertex_group_bending = 'Welt'
        s.bending_stiffness_max = 4
    if rest_shape is not None:
        s.rest_shape_key = rest_shape
    c = mod.collision_settings
    c.collision_quality = 4
    c.distance_min = config.get('distance', .0015)
    c.use_self_collision = config.get('self_collision', False)
    c.self_distance_min = .001
    if obj.vertex_groups.get('Fold self collision'):
        c.vertex_group_self_collisions = 'Fold self collision'
    mod.point_cache.frame_start = 1
    mod.point_cache.frame_end = config['frames']
    return mod


def simulate(obj, mod, frames):
    durations = []
    start = time.perf_counter()
    for frame in range(1, frames+1):
        t = time.perf_counter()
        bpy.context.scene.frame_set(frame)
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        # Force evaluation within the timed interval.
        _ = evaluated.data.vertices[0].co[:]
        durations.append(time.perf_counter()-t)
        if frame % 10 == 0:
            print(obj.name, 'frame', frame, 'seconds', durations[-1], flush=True)
    elapsed = time.perf_counter()-start
    final = np.asarray([v.co[:] for v in evaluated.data.vertices])
    mass = float(mod.settings.mass)
    apply(obj, mod)
    return {'frames': frames, 'elapsed_s': elapsed,
            'seconds_per_frame': float(np.mean(durations[1:])),
            'frame_seconds': durations, 'vertex_mass_kg': mass,
            'bounds_local_m': [final.min(0).tolist(), final.max(0).tolist()]}
