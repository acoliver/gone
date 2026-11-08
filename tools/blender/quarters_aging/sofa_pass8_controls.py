"""Early mesh, free-fall, cantilever, area, speed and initial-contact controls."""
import json
from pathlib import Path
import sys
import time

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import assert_collision_clear
from fabric_mesh import material, new_object
from foam_collapse import largest_shell
from sofa_full_decay import ROOT, initialize, open_cover_bottom, residue_pair, envelope_for
from sofa_decay_policy import cushion_plan
from sofa_pass8_mesh import clean_mesh, mesh_quality
from sofa_pass8_solver import cloth, solve
from cloth_stage import configure

OUT = ROOT/'tmp/age/pass8'
OUT.mkdir(parents=True, exist_ok=True)
START = time.perf_counter()
RECORD = {'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'controls': {}}


def save():
    RECORD['elapsed_s'] = time.perf_counter()-START
    (OUT/'controls.json').write_text(json.dumps(RECORD, indent=2)+'\n')


def back_control(label, contacts):
    initialize()
    obj = bpy.data.objects['BackCushion_C']
    largest_shell(obj)
    reference = len(obj.data.vertices)
    plan = cushion_plan(obj.name)
    if contacts == 'fixed':
        from sofa_pass8 import back_residue, envelope
        dense, residue, reduction = back_residue(obj, plan)
        envelope(obj, residue, plan)
    elif contacts:
        dense, residue, reduction = residue_pair(obj, plan, ROOT/'tmp/age/pass5/residue-stable/seat-residue.npz')
        envelope_for(obj, residue, plan)
    else:
        for other in bpy.context.scene.objects:
            if other.name != 'Frame':
                for mod in list(other.modifiers):
                    if mod.type == 'COLLISION':
                        other.modifiers.remove(mod)
    open_cover_bottom(obj, True)
    density = clean_mesh(obj)
    initial = None
    try:
        assert_collision_clear(obj)
        from sofa_pass8_finish import initial_contacts
        supports = [o for o in bpy.context.scene.objects if o.type == 'MESH' and
                    any(m.type == 'COLLISION' for m in o.modifiers)]
        initial_contacts(obj, supports)
    except ValueError as error:
        initial = str(error)
    mod, settings = cloth(obj, reference, frames=40)
    try:
        result = solve(obj, mod, OUT, label, frames=40, settle=False)
    except ValueError:
        result = json.loads((OUT/(label+'-solve.json')).read_text())
    sharp = result['surface_samples']['20']['dihedral_over_30_share']
    RECORD['controls'][label] = {'density': density, 'settings': settings, 'frame20_sharp_share': sharp,
                                'threshold': .05, 'pass': sharp <= .05 and result['pass'],
                                'initial_contact_error': initial, 'solve': result}
    save()


def swatch(label, scale=1., pins=False, frames=60):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = 24
    n = 12
    vertices = [(x*.2/n, y*.2/n, 2.) for y in range(n+1) for x in range(n+1)]
    faces = [(y*(n+1)+x, y*(n+1)+x+1, (y+1)*(n+1)+x+1, (y+1)*(n+1)+x)
             for y in range(n) for x in range(n)]
    obj = new_object(label, vertices, faces, material('Control', (.3, .3, .3)))
    config = dict(mass=.006*scale, stiffness=150*scale, shear=80*scale, bending=.25*scale,
                  frames=frames, quality=20, time_scale=.5, damping_factor=5/12, air_factor=2.)
    pinned = {v.index: 1. for v in obj.data.vertices if v.co.y < .00001} if pins else None
    mod = configure(obj, config, len(vertices), pins=pinned)
    mod.settings.air_damping = 2.4*.006*9.81/.3
    mod.settings.bending_model = 'ANGULAR'
    mod.settings.bending_damping = .3
    mass = float(mod.settings.mass)
    # A co-scaled fixture also needs its viscous terms scaled; otherwise this
    # compares different transients rather than the force ratios.
    if pins:
        mod.settings.air_damping *= scale
        mod.settings.tension_damping = mod.settings.compression_damping = 5*scale
        mod.settings.shear_damping = 5*scale
        mod.settings.bending_damping = .3*scale
    positions, history = [], []
    for frame in range(1, frames+1):
        scene.frame_set(frame)
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        p = np.array([v.co[:] for v in evaluated.data.vertices])
        positions.append(p)
        if frame > 1:
            history.append(float(np.mean((positions[-2][:, 2]-p[:, 2])/(.5/24))))
    profile = p.reshape(n+1, n+1, 3).mean(1)
    return {'mass_kg': mass, 'air': float(mod.settings.air_damping),
            'speed_last10_m_s': float(np.mean(history[-10:])), 'profile_m': profile.tolist()}


def main():
    try:
        back_control('C1', 'fixed')
        back_control('C1b', False)
        fall = swatch('Fall')
        predicted = 2.4*fall['mass_kg']*9.81/fall['air']
        one = swatch('CantileverOne', pins=True, frames=300)
        scaled = swatch('CantileverScaled', scale=.5, pins=True, frames=300)
        difference = float(np.linalg.norm(np.array(one['profile_m'])-scaled['profile_m'], axis=1).max())
        RECORD['controls']['C2'] = {'free_fall': fall, 'predicted_m_s': predicted,
            'relative_error': abs(fall['speed_last10_m_s']/predicted-1),
            'cantilever_max_profile_difference_m': difference,
            'cantilever_1x': one, 'cantilever_scaled': scaled,
            'pass': abs(fall['speed_last10_m_s']/predicted-1) <= .2 and difference <= .003}
        records = [v['solve'] for k, v in RECORD['controls'].items() if k in {'C1', 'C1b'}]
        for key in ['C3', 'C4']:
            checks = [c for r in records for c in r['controls']]
            RECORD['controls'][key] = {'checks': checks, 'pass': all(c[key+'_pass'] for c in checks)}
        RECORD['controls']['C5'] = {'initial_contact_errors': {k: v['initial_contact_error'] for k, v in RECORD['controls'].items() if k in {'C1', 'C1b'}},
            'pass': all(RECORD['controls'][k]['initial_contact_error'] is None for k in ['C1', 'C1b'])}
        RECORD['pass'] = all(v['pass'] for v in RECORD['controls'].values())
    finally:
        save()
    print('EARLY CONTROLS', json.dumps(RECORD), flush=True)

if __name__ == '__main__':
    main()
