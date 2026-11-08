"""Floor-contact swatch controls and per-frame distance/velocity traces."""
import argparse
import json
from pathlib import Path
import sys
import time

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cloth_stage import calibrated_config, configure
from common import collision
from fabric_mesh import material, new_object


def frame_trace(obj, previous, dt):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    positions = np.array([obj.matrix_world@v.co for v in evaluated.data.vertices])
    velocity = (positions-previous)/dt if previous is not None else np.zeros_like(positions)
    return positions, {'floor_distance_min_m': float(positions[:, 2].min()),
                       'floor_distance_p05_m': float(np.quantile(positions[:, 2], .05)),
                       'centroid_m': positions.mean(0).tolist(),
                       'max_speed_m_s': float(np.linalg.norm(velocity, axis=1).max()),
                       'mean_velocity_m_s': velocity.mean(0).tolist(),
                       'min_vertex_velocity_m_s': velocity[np.argmin(positions[:, 2])].tolist()}


def floor_drop(kind, out, frames=180):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = 24
    if kind == 'solid':
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, -.05))
        floor = bpy.context.object
        floor.dimensions = (8, 8, .1)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    else:
        bpy.ops.mesh.primitive_plane_add(size=8)
        floor = bpy.context.object
    floor.name = 'ControlFloor'
    collision(floor, .001)
    floor.collision.cloth_friction = 8
    n = 34
    vertices = [(i*.2/n-.1, j*.2/n-.1, .25+(i*.2/n-.1)*.7)
                for j in range(n+1) for i in range(n+1)]
    faces = [(j*(n+1)+i, j*(n+1)+i+1, (j+1)*(n+1)+i+1, (j+1)*(n+1)+i)
             for j in range(n) for i in range(n)]
    obj = new_object('DropSwatch', vertices, faces, material('ControlWool', (.56, .48, .35)))
    config = calibrated_config('wool', .006, .022222222, frames)
    config.update(stiffness=200, bending=.9, quality=16, time_scale=.6,
                  self_collision=True, self_distance=.001, distance=.0015, collision_quality=6)
    configure(obj, config, 100)
    previous = None
    samples = []
    start = time.perf_counter()
    for frame in range(1, frames+1):
        bpy.context.scene.frame_set(frame)
        previous, trace = frame_trace(obj, previous, config['time_scale']/24)
        samples.append(dict(frame=frame, **trace))
    final = samples[-1]
    result = {'floor': kind, 'settings': config, 'frames': samples,
              'elapsed_s': time.perf_counter()-start,
              'pass': -.0001 <= final['floor_distance_min_m'] < .01 and final['max_speed_m_s'] < .01}
    out.mkdir(parents=True, exist_ok=True)
    (out/(kind+'-drop.json')).write_text(json.dumps(result, indent=2)+'\n')
    print(kind, 'PASS' if result['pass'] else 'FAIL', final, flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    for kind in ['plane', 'solid']:
        floor_drop(kind, args.out)
