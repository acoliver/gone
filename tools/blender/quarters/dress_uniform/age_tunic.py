"""Dense split-seam tunic aging. Stages remain in scratch until all gates pass."""
import argparse
import json
from pathlib import Path
import sys
import time
import subprocess

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import (HERE, ROOT, configure_detail_stiffness, fit_details,
                           load_source, reinforce_and_bind)
from aging_geometry import cut_tunic, detach_fallen, pressed_sleeve, refine
from bake_down import bake, decimate, material_maps
from cloth_metrics import lip_lift, save_surface, surface_metrics
from cloth_stage import configure
from cloth_contacts import exclude_small_rest_faces
from reduce_aging import reduce_game
from common import activate, apply, assert_collision_clear, assert_surface_clear, collision, recalc
from fabric_mesh import material


def save_checkpoint(out, name, record):
    bpy.context.scene['tunic5_record'] = json.dumps(record)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(out / f'{name}.blend'))
    (out / f'{name}.json').write_text(json.dumps(record, indent=2)+'\n')


def floor():
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, -1.))
    obj = bpy.context.object
    obj.name = 'AgingFloorCollider'
    obj.scale = (3, 3, .1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.hide_render = True
    obj['aged_export'] = False
    collision(obj, .001)
    obj.collision.cloth_friction = 8.
    return obj


def prepare(out):
    body = load_source()
    floor()
    record = {'source': 'tunic-working.blend', 'seed': 9521,
              'calibration': 'aging-calibration.json', 'floor_z_m': -.95}
    record['density'] = refine(body)
    print('DENSITY', record['density'], flush=True)
    record['splits'] = cut_tunic(body)
    record['fallen'] = detach_fallen(body)
    print('SPLITS', record['splits'], 'FALLEN', record['fallen'], flush=True)
    wire = bpy.data.objects['Hanger']
    from common import surface_tree
    tree = surface_tree(wire)
    pins = {}
    for vertex in body.data.vertices:
        p = vertex.co
        if -.245 < p.x < -.10 and p.z > -.22 and abs(p.y) < .003:
            point, _, _, _ = tree.ray_cast(Vector((p.x, p.y, .1)), Vector((0, 0, -1)))
            if point is None:
                raise ValueError('Retained shoulder strip misses hanger wire')
            p.z = max(p.z, point.z+.004)
            pins[vertex.index] = 1.
    record['pins'] = pins
    record['bindings'], record['detail_patches'] = reinforce_and_bind(body)
    pressed_sleeve(body)
    recalc(body)
    assert_surface_clear(body)
    assert_collision_clear(body)
    record['initial_metrics'] = surface_metrics(body)
    save_checkpoint(out, 'prepared', record)
    return record


def wool_config(frames):
    calibration = json.loads((HERE / 'aging-calibration.json').read_text())
    if not calibration['pass']:
        raise ValueError('Wool calibration has not passed')
    config = calibration['selected']['0.003']['settings'].copy()
    config.update(frames=frames, quality=12, self_collision=True, collision_quality=4,
                  distance=.0015, self_distance=.001, shrink=.04)
    return config


def bake_simulation(obj, mod, frames):
    """Cloth with a rest key must be frozen from evaluated data, not modifier_apply."""
    durations = []
    samples = []
    previous = None
    for frame in range(1, frames+1):
        start = time.perf_counter()
        bpy.context.scene.frame_set(frame)
        deps = bpy.context.evaluated_depsgraph_get()
        evaluated = obj.evaluated_get(deps)
        positions = np.array([v.co[:] for v in evaluated.data.vertices])
        durations.append(time.perf_counter()-start)
        if frame == frames-5:
            previous = positions.copy()
        if frame % 10 == 0:
            print(obj.name, 'frame', frame, 'seconds', durations[-1],
                  'bounds', positions.min(0), positions.max(0), flush=True)
        if frame % 25 == 0:
            samples.append(dict(frame=frame, bounds=[positions.min(0).tolist(), positions.max(0).tolist()]))
    frozen = bpy.data.meshes.new_from_object(evaluated, depsgraph=deps)
    obj.modifiers.remove(mod)
    obj.shape_key_clear()
    obj.data = frozen
    return dict(frames=frames, seconds_per_frame=float(np.mean(durations[1:])),
                last_five_frames_motion_m=float(np.linalg.norm(positions-previous, axis=1).max()),
                samples=samples)


def simulate(out, frames):
    bpy.ops.wm.open_mainfile(filepath=str(out / 'prepared.blend'))
    record = json.loads(bpy.context.scene['tunic5_record'])
    body = bpy.data.objects['TunicBody']
    config = wool_config(frames)
    # Broad front/back panels do not fold onto themselves. Keep sleeve/tear contacts.
    exclusion = body.vertex_groups.new(name='Self collision exclusion')
    ids = [v.index for v in body.data.vertices if abs(v.co.x) < .20 and -.80 < v.co.z < -.37]
    exclusion.add(ids, 1., 'REPLACE')
    pins = {int(i): w for i, w in record['pins'].items()}
    mod = configure(body, config, record['density']['unaged_vertices'], pins,
                    body.data.shape_keys.key_blocks['Empty pressed left sleeve'])
    configure_detail_stiffness(mod)
    s = mod.settings
    damping = config['damping_multiplier']
    s.tension_damping = s.compression_damping = s.shear_damping = 5*damping
    s.bending_damping = .5*damping
    s.air_damping = 10*damping
    record['simulation_config'] = config
    record['rest_contact_policy'] = exclude_small_rest_faces(body, mod)
    record['simulation'] = bake_simulation(body, mod, frames)
    record['dense_metrics'] = surface_metrics(body)
    record['lip_lift'] = lip_lift(body)
    record['details_fit'] = fit_details(body, record['bindings'])
    save_surface(body, out / 'dense-body.npz')
    # The mound is a collider before the allowances fall onto it.
    lost_area = sum(p['lost_area_m2'] for p in record['fallen'])
    subprocess.run(['/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python',
                    str(HERE / 'build_fibre_heap.py'), '--lost-area', str(lost_area),
                    '--out', str(out / 'heap.npz')], check=True)
    heap_data = np.load(out / 'heap.npz')
    from fabric_mesh import new_object
    heap = new_object('FibreDust_Dense', heap_data['vertices'], heap_data['faces'],
                      material('Loose wool dust', (.19, .18, .16)))
    heap.location.z = -.9495
    mound, record['heap_reduction'] = decimate(heap, 500, protect=0.)
    mound.name = 'FibreDust'
    mound['aged_export'] = True
    heap['aged_export'] = False
    heap.hide_render = True
    heap.hide_set(True)
    record['heap'] = json.loads((out / 'heap.json').read_text())
    collision(mound, .001)
    # Fall detached allowances against the settled body and the original floor.
    collision(body, .0015)
    record['fallen_simulations'] = {}
    for piece in record['fallen']:
        obj = bpy.data.objects[piece['name']]
        bpy.context.scene.frame_set(1)
        mod = configure(obj, config, max(4, int(piece['vertices']*record['density']['mass_multiplier'])))
        mod.settings.bending_stiffness = .3
        mod.settings.tension_damping = 5*damping
        mod.settings.compression_damping = 5*damping
        mod.settings.shear_damping = 5*damping
        mod.settings.bending_damping = .5*damping
        mod.settings.air_damping = 10*damping
        piece['rest_contact_policy'] = exclude_small_rest_faces(obj, mod)
        record['fallen_simulations'][obj.name] = bake_simulation(obj, mod, frames)
        collision(obj, .001)
    for obj in bpy.context.scene.objects:
        for m in list(obj.modifiers):
            if m.type == 'COLLISION' and obj.get('aged_export'):
                obj.modifiers.remove(m)
    save_checkpoint(out, 'simulated', record)
    return record


def reduce_and_bake(out):
    bpy.ops.wm.open_mainfile(filepath=str(out / 'simulated.blend'))
    record = json.loads(bpy.context.scene['tunic5_record'])
    body = bpy.data.objects['TunicBody']
    record['details_fit'] = fit_details(body, record['bindings'])
    record['reduction'] = {}
    record['bakes'] = {}
    names = ['TunicBody']+[p['name'] for p in record['fallen']]
    for name in names:
        dense = bpy.data.objects[name]
        low, report = reduce_game(dense, 9800 if name == 'TunicBody' else 350)
        if not report['pass']:
            raise ValueError(f'{name}: boundary fidelity failed: {report}')
        mat, paths = bake(dense, low, out / 'textures', size=2048 if name == 'TunicBody' else 512)
        material_maps(mat, (.025, .043, .08))
        dense['aged_export'] = False
        dense.hide_render = True
        dense.hide_set(True)
        dense.name = name+'_Dense'
        low.name = name
        low['aged_export'] = True
        record['reduction'][name] = report
        record['bakes'][name] = paths
        if name == 'TunicBody':
            record['game_sheet_metrics'] = surface_metrics(low)
    save_checkpoint(out, 'baked', record)
    return record


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage', choices=['prepare', 'simulate', 'bake', 'all'], default='all')
    p.add_argument('--out', type=Path, default=ROOT / 'tmp/age/tunic5/main')
    p.add_argument('--frames', type=int, default=600)
    a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    a.out = a.out.resolve()
    a.out.mkdir(parents=True, exist_ok=True)
    if a.stage in ['prepare', 'all']:
        prepare(a.out)
    if a.stage in ['simulate', 'all']:
        simulate(a.out, a.frames)
    if a.stage in ['bake', 'all']:
        reduce_and_bake(a.out)


if __name__ == '__main__':
    main()
