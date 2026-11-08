"""Dense-cloth setup with explicit groups, per-vertex mass and measured frame costs."""
import json
from pathlib import Path
import time

import bpy
import numpy as np

from common import apply


def calibrated_config(fabric, edge, reference_edge, frames):
    """Fit q(h) = q(reference) * (h/reference_edge)**p from measured swatches.

    At h/reference_edge = 9/34, upholstery exponents are 0.857274446
    structural and 1.378776541 shear/bending; wool spring exponents are zero.
    Both damping and air use p=1.595219466. Vertex mass still uses Nref/N.
    These are empirical Blender 4.5.11 coefficients, not continuum scaling
    laws. The fit is measured at 22.222 and 5.882 mm over 150 frames.
    """
    if min(edge, reference_edge) <= 0:
        raise ValueError('Calibration needs positive physical edge lengths')
    path = Path(__file__).resolve().parents[1]/'quarters/sofa/cloth-trials.json'
    record = json.loads(path.read_text())['pass5_calibration']
    if not record['pass']:
        raise ValueError('Dense fabric calibration failed')
    data = record['fabrics'][fabric]
    reference = record['references'][fabric]
    ratio = edge/reference_edge
    factors = {key: ratio**p for key, p in data['empirical_exponents'].items()}
    config = {key: reference[key]*factors[key] for key in ['mass', 'stiffness', 'shear', 'bending']}
    config.update(frames=frames, damping_factor=factors['damping'], air_factor=factors['air'])
    return config


def configure(obj, config, reference_vertices, pins=None, rest_shape=None):
    if reference_vertices <= 0:
        raise ValueError('A positive unaged vertex count is required for mass scaling')
    mod = obj.modifiers.new('Dense aging cloth', 'CLOTH')
    s = mod.settings
    s.quality = config.get('quality', 10)
    s.time_scale = config.get('time_scale', 1.)
    s.mass = config['mass'] * reference_vertices / len(obj.data.vertices)
    s.tension_stiffness = config['stiffness']
    s.compression_stiffness = config['stiffness']
    s.shear_stiffness = config.get('shear', config['stiffness']*.7)
    s.bending_stiffness = config['bending']
    damping = config.get('damping_factor', 1.)
    s.tension_damping = 12*damping
    s.compression_damping = 12*damping
    s.shear_damping = 12*damping
    s.bending_damping = 3*damping
    s.air_damping = 5*config.get('air_factor', 1.)
    s.use_pressure = False
    if pins:
        group = obj.vertex_groups.new(name='Retained stitches')
        for index, weight in pins.items():
            group.add([index], weight, 'REPLACE')
        s.vertex_group_mass = group.name
    if obj.vertex_groups.get('Lip shrink'):
        s.vertex_group_shrink = 'Lip shrink'
        s.shrink_min = 0.
        s.shrink_max = config.get('shrink', .04)
    if obj.vertex_groups.get('Welt'):
        s.vertex_group_bending = 'Welt'
        s.bending_stiffness_max = config.get('welt_bending', 4.)
    if rest_shape is not None:
        s.rest_shape_key = rest_shape
    c = mod.collision_settings
    c.collision_quality = config.get('collision_quality', 4)
    c.distance_min = config.get('distance', .0015)
    c.use_self_collision = config.get('self_collision', False)
    c.self_distance_min = config.get('self_distance', .001)
    # Blender excludes triangles whose vertices all belong to this group.
    if obj.vertex_groups.get('Self collision exclusion'):
        c.vertex_group_self_collisions = 'Self collision exclusion'
    mod.point_cache.frame_start = 1
    mod.point_cache.frame_end = config['frames']
    return mod


def simulate(obj, mod, frames, sample=None):
    durations = []
    samples = {}
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
        if sample is not None and (frame == 1 or frame % 20 == 0 or frame == frames):
            samples[str(frame)] = sample(evaluated)
            print('SURFACE', frame, samples[str(frame)], flush=True)
    elapsed = time.perf_counter()-start
    final = np.asarray([v.co[:] for v in evaluated.data.vertices])
    mass = float(mod.settings.mass)
    apply(obj, mod)
    return {'frames': frames, 'elapsed_s': elapsed,
            'seconds_per_frame': float(np.mean(durations[1:])),
            'frame_seconds': durations, 'vertex_mass_kg': mass, 'surface_samples': samples,
            'bounds_local_m': [final.min(0).tolist(), final.max(0).tolist()]}
