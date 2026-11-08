"""One experimental seat through dense cloth, split, collapse and game-mesh baking.

This never publishes. Other sofa parts come from the recorded pass-3 comparison
bake; their known failures remain visible in the final all-part report.
"""
import argparse
import json
from pathlib import Path
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bake_down import bake, decimate, material_maps
from cloth_stage import calibrated_config, configure, simulate
from common import collision, export, recalc, save, surface_tree
from densify import densify
from fabric_mesh import join, material, new_object
from foam_collapse import largest_shell
from fringe_cards import cards, fringe_material
from opacity_bake import opacity_bake

ROOT = Path(__file__).resolve().parents[3]
NAME = 'SeatCushion_C'


def prepare(out, residue_path, collapse_frames=100, cuts=True, contact_mode='fitted', full_self=False):
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'tmp/age/pass3/sofa-k/sofa-aged.blend'))
    bpy.data.objects.remove(bpy.data.objects[NAME], do_unlink=True)
    with bpy.data.libraries.load(str(ROOT/'tools/blender/quarters/sofa/sofa-working.blend'), link=False) as (_, target):
        target.objects = [NAME]
    obj = target.objects[0]
    bpy.context.collection.objects.link(obj)
    obj['aged_export'] = True
    obj.modifiers.clear()
    largest_shell(obj)
    original = np.array([v.co[:] for v in obj.data.vertices])
    original_count = len(original)
    envelope = obj.copy()
    envelope.data = obj.data.copy()
    bpy.context.collection.objects.link(envelope)
    envelope.name = 'PilotCollapseEnvelope'
    envelope['aged_export'] = False
    envelope.hide_render = True
    dense_npz = np.load(residue_path)
    points = dense_npz['vertices']+np.array([0, -.035, .391])
    residue = new_object('PilotDenseResidue', points, dense_npz['faces'], material('Foam', (.28, .19, .10)))
    residue['aged_export'] = False
    proxy = new_object('ResiduePoreProxy', dense_npz['game_vertices']+np.array([0, -.035, .391]),
                       dense_npz['game_faces'], residue.data.materials[0])
    proxy_source_vertices = len(proxy.data.vertices)
    largest_shell(proxy)
    low_residue, residue_report = decimate(proxy, 700)
    residue_report['removed_disconnected_proxy_vertices'] = proxy_source_vertices-len(proxy.data.vertices)
    bpy.data.objects.remove(proxy, do_unlink=True)
    low_residue.name = 'PilotResidue'
    low_residue['aged_export'] = False
    low_residue.hide_render = True
    collision(low_residue, .001)
    tree = surface_tree(low_residue)
    basis = envelope.shape_key_add(name='Original filling contact')
    collapsed = envelope.shape_key_add(name='Powder contact')
    bottom, top = original[:, 2].min(), original[:, 2].max()
    inverse = envelope.matrix_world.inverted()
    for i, v in enumerate(basis.data):
        normal = envelope.data.vertices[i].normal
        v.co -= normal*.008
        world = envelope.matrix_world@Vector(original[i])
        point, _, _, _ = tree.ray_cast(Vector((world.x, world.y, .7)), Vector((0, 0, -1)))
        height = point.z if point else .394
        fraction = float(np.clip((original[i, 2]-bottom)/(top-bottom), 0, 1))
        collapsed.data[i].co = inverse@Vector((world.x, world.y, .392+fraction*(height-.392)))
    collapsed.value = 0
    collapsed.keyframe_insert(data_path='value', frame=1)
    collapsed.value = 1
    collapsed.keyframe_insert(data_path='value', frame=collapse_frames)
    for curve in envelope.data.shape_keys.animation_data.action.fcurves:
        for key in curve.keyframe_points:
            key.interpolation = 'LINEAR'
    collision(envelope, .001)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    remove = [f for f in bm.faces if f.normal.z < -.2 or min((obj.matrix_world@v.co).z for v in f.verts) < .392]
    bmesh.ops.delete(bm, geom=remove, context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(obj.data)
    bm.free()
    dense_report = densify(obj, levels=2)
    from seat_tears import author
    tears = author(obj) if cuts else {'method': 'uncut initialization control'}
    # The original welt retains bending resistance; boxing walls can pleat.
    welt = obj.vertex_groups.new(name='Welt')
    fold = obj.vertex_groups.new(name='Self collision exclusion')
    for vertex in obj.data.vertices:
        p = obj.matrix_world@vertex.co
        wall = abs(vertex.normal.z) < .5
        weight = (1. if wall and p.z > .555 else .02 if wall else .5) if cuts else (1. if wall and p.z > .51 else .2 if wall else .4)
        welt.add([vertex.index], weight, 'REPLACE')
        if not wall and not full_self:
            fold.add([vertex.index], 1., 'REPLACE')
    from split_contacts import exclude_split_contacts
    split_contacts = exclude_split_contacts(obj)
    for other in bpy.context.scene.objects:
        if other.type == 'MESH' and other.get('aged_export') and other != obj:
            other.modifiers.clear()
            collision(other, .001)
    from neighbour_colliders import fitted_backs
    neighbours = fitted_backs(collapse_frames, mode=contact_mode if cuts else 'fitted')
    bpy.ops.mesh.primitive_plane_add(size=8)
    floor = bpy.context.object
    floor.name = 'PilotFloor'
    floor['aged_export'] = False
    floor.hide_render = True
    collision(floor, .001)
    return obj, {'dense': dense_report, 'reference_vertices': original_count, 'tears': tears,
                 'residue_decimation': residue_report, 'residue_source': str(residue_path), 'status': 'prepared',
                 'tear_method': tears['method'],
                 'production_calibrated': True, 'neighbour_contacts': neighbours,
                 'cuts': cuts, 'full_self_collision': full_self, 'split_contacts': split_contacts}


def finish(out, obj, record, size):
    for other in list(bpy.context.scene.objects):
        for mod in list(other.modifiers):
            if mod.type == 'COLLISION':
                other.modifiers.remove(mod)
    low, report = decimate(obj, 2700)
    record['cover_decimation'] = report
    from cloth_metrics import lip_lift, save_surface, surface_metrics
    record['game_metrics'] = surface_metrics(low)
    record['G5'] = lip_lift(obj)
    save_surface(obj, out/'dense-cover.npz')
    save_surface(low, out/'game-cover.npz')
    mat, paths = bake(obj, low, out/'textures', size=size)
    mat.name = 'CharcoalUpholstery_Pass5'
    opacity, opacity_report = opacity_bake(low, out/'textures/seat_opacity.png', size=size)
    record['opacity'] = opacity_report
    material_maps(mat, (.10, .12, .10), opacity_image=opacity)
    record['cover_maps'] = paths
    residue = bpy.data.objects['PilotDenseResidue']
    save_surface(residue, out/'dense-residue.npz')
    residue.hide_render = False
    game_residue = bpy.data.objects['PilotResidue']
    game_residue.hide_render = False
    mat_residue, paths = bake(residue, game_residue, out/'textures', size=min(size, 2048))
    material_maps(mat_residue, (.28, .19, .10))
    mat_residue.name = 'Foam_Pass5'
    record['residue_maps'] = paths
    blockers = [low, game_residue]+[o for o in bpy.context.scene.objects if o.type == 'MESH' and o.get('aged_export') and o not in {obj, low, game_residue}]
    fringe, fringe_report = cards(low, fringe_material(out/'textures', 9501), 9501,
                                  boundary_group='Lip shrink', blockers=blockers)
    record['fringe'] = fringe_report
    # Keep original node, pivot and transform. Helpers and bake sources are removed.
    obj.data = low.data.copy()
    obj.modifiers.clear()
    obj.shape_key_clear()
    bpy.data.objects.remove(low, do_unlink=True)
    join(obj, [game_residue])
    obj['aged_export'] = True
    for helper in ['PilotDenseResidue', 'PilotCollapseEnvelope', 'PilotFloor']:
        bpy.data.objects.remove(bpy.data.objects[helper], do_unlink=True)
    record['status'] = 'experimental_baked'
    record['limitations'] = ['Other sofa parts retain pass-3 failures',
                             'Changed-part SAT and alpha-aware render gates must still run']
    (out/'seat-trial.json').write_text(json.dumps(record, indent=2)+'\n')
    save(out/'sofa-seat-pilot.blend', record)
    export(out/'sofa_aged.glb')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, default=ROOT/'tmp/age/pass5/seat-pilot')
    p.add_argument('--frames', type=int, default=360)
    p.add_argument('--size', type=int, default=4096)
    p.add_argument('--finish', type=Path)
    p.add_argument('--residue', type=Path, default=ROOT/'tmp/age/pass4/residue-proxy/seat-residue.npz')
    p.add_argument('--settings', type=Path)
    p.add_argument('--collapse-frames', type=int, default=240)
    p.add_argument('--simulate-only', action='store_true')
    p.add_argument('--uncut-control', action='store_true')
    p.add_argument('--contact-mode', choices=['fitted', 'retreat', 'staged', 'morph', 'rear'], default='fitted')
    p.add_argument('--self-collision-mode', choices=['folds', 'all'], default='folds')
    a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    a.out.mkdir(parents=True, exist_ok=True)
    if a.finish:
        bpy.ops.wm.open_mainfile(filepath=str(a.finish.resolve()))
        obj = bpy.data.objects[NAME]
        record = json.loads(bpy.context.scene['pilot_record'])
    else:
        from cloth_metrics import surface_metrics, within_frame
        contact_end = a.collapse_frames*(3 if a.contact_mode == 'rear' else 2)+60
        if not a.uncut_control and a.contact_mode in {'staged', 'rear'} and a.frames < contact_end:
            raise ValueError('Staged neighbour contacts must reach their actual exported pose before simulation ends')
        obj, record = prepare(a.out, a.residue, a.collapse_frames, not a.uncut_control, a.contact_mode, a.self_collision_mode == 'all')
        bpy.context.scene.render.fps = 24
        bpy.context.scene.frame_set(1)
        config = calibrated_config('upholstery', .2/34, .2/9, a.frames)
        config.update(self_collision=True, shrink=.04, quality=16,
                      collision_quality=4, distance=.0015, time_scale=.5,
                      welt_bending=3.2, self_distance=.0002)
        from common import assert_collision_clear
        if a.settings:
            config.update(json.loads(a.settings.read_text()))
        assert_collision_clear(obj)
        mod = configure(obj, config, record['reference_vertices'])
        record['settings'] = config
        record['collapse_frames'] = a.collapse_frames
        record['simulation'] = simulate(obj, mod, a.frames, sample=surface_metrics)
        record['dense_metrics'] = surface_metrics(obj)
        record['frame_bounds'] = within_frame(obj, bpy.data.objects['Frame'])
        low, report = decimate(obj, 2400 if a.uncut_control else 2700)
        record['game_metrics'] = surface_metrics(low)
        record['cover_decimation'] = report
        bpy.data.objects.remove(low, do_unlink=True)
        (a.out/'simulation.json').write_text(json.dumps(record, indent=2)+'\n')
        bpy.context.scene['pilot_record'] = json.dumps(record)
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(a.out/'simulated.blend'))
    if not a.simulate_only:
        finish(a.out, obj, record, a.size)


if __name__ == '__main__':
    main()
