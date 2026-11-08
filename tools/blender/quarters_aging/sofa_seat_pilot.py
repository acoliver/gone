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
from cloth_stage import configure, simulate
from common import collision, export, recalc, save, surface_tree
from densify import densify
from fabric_mesh import join, material, new_object
from foam_collapse import largest_shell
from fringe_cards import cards, fringe_material
from opacity_bake import opacity_bake
from tear_paths import grain_walk, split_polyline

ROOT = Path(__file__).resolve().parents[3]
NAME = 'SeatCushion_C'


def prepare(out, residue_path):
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
    low_residue, residue_report = decimate(proxy, 700)
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
    collapsed.keyframe_insert(data_path='value', frame=100)
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
    tree = surface_tree(obj)
    inverse = obj.matrix_world.inverted()
    tears = []
    for start, length, seed, angle in [([-.13, -.12], .18, 9501, 0), ([-.16, -.34], .16, 9502, 0)]:
        walk = grain_walk(start, length, seed, step=.004, angle=angle)
        path = []
        for x, y in walk:
            point, _, _, _ = tree.find_nearest(Vector((float(x), float(y), .65)))
            path.append(tuple(inverse@point))
        tears.append(split_polyline(obj, path))
    # The original welt retains bending resistance; boxing walls can pleat.
    welt = obj.vertex_groups.new(name='Welt')
    fold = obj.vertex_groups.new(name='Fold self collision')
    for vertex in obj.data.vertices:
        p = obj.matrix_world@vertex.co
        wall = abs(vertex.normal.z) < .5
        welt.add([vertex.index], 1. if wall and p.z > .51 else .2 if wall else .4, 'REPLACE')
        if wall:
            fold.add([vertex.index], 1., 'REPLACE')
    for other in bpy.context.scene.objects:
        if other.type == 'MESH' and other.get('aged_export') and other != obj:
            other.modifiers.clear()
            collision(other, .001)
    bpy.ops.mesh.primitive_plane_add(size=8)
    floor = bpy.context.object
    floor.name = 'PilotFloor'
    floor['aged_export'] = False
    floor.hide_render = True
    collision(floor, .001)
    return obj, {'dense': dense_report, 'reference_vertices': original_count, 'tears': tears,
                 'residue_decimation': residue_report, 'residue_source': str(residue_path), 'status': 'prepared',
                 'tear_method': 'Surface-projected XY grain walk; UV-gradient path integration pending',
                 'production_calibrated': False}


def finish(out, obj, record, size):
    for other in list(bpy.context.scene.objects):
        for mod in list(other.modifiers):
            if mod.type == 'COLLISION':
                other.modifiers.remove(mod)
    low, report = decimate(obj, 2400)
    record['cover_decimation'] = report
    mat, paths = bake(obj, low, out/'textures', size=size)
    mat.name = 'CharcoalUpholstery_Pass4'
    opacity, opacity_report = opacity_bake(low, out/'textures/seat_opacity.png', size=size)
    record['opacity'] = opacity_report
    material_maps(mat, (.10, .12, .10), opacity_image=opacity)
    record['cover_maps'] = paths
    residue = bpy.data.objects['PilotDenseResidue']
    residue.hide_render = False
    game_residue = bpy.data.objects['PilotResidue']
    game_residue.hide_render = False
    mat_residue, paths = bake(residue, game_residue, out/'textures', size=min(size, 2048))
    material_maps(mat_residue, (.28, .19, .10))
    mat_residue.name = 'Foam_Pass4'
    record['residue_maps'] = paths
    fringe, fringe_report = cards(low, fringe_material(out/'textures', 9501), 9501)
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
    record['limitations'] = ['Uncalibrated drape', 'Other sofa parts retain pass-3 failures',
                             'All-part SAT and alpha-aware render gates must still run']
    (out/'seat-trial.json').write_text(json.dumps(record, indent=2)+'\n')
    save(out/'sofa-seat-pilot.blend', record)
    export(out/'sofa_aged.glb')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, default=ROOT/'tmp/age/pass4/seat-pilot')
    p.add_argument('--frames', type=int, default=180)
    p.add_argument('--size', type=int, default=4096)
    p.add_argument('--finish', type=Path)
    p.add_argument('--residue', type=Path, default=ROOT/'tmp/age/pass4/residue/seat-residue.npz')
    a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    a.out.mkdir(parents=True, exist_ok=True)
    if a.finish:
        bpy.ops.wm.open_mainfile(filepath=str(a.finish.resolve()))
        obj = bpy.data.objects[NAME]
        record = json.loads(bpy.context.scene['pilot_record'])
    else:
        obj, record = prepare(a.out, a.residue)
        bpy.context.scene.render.fps = 24
        bpy.context.scene.frame_set(1)
        config = {'mass': .025, 'stiffness': 180, 'bending': .2, 'frames': a.frames,
                  'self_collision': True, 'shrink': .04}
        mod = configure(obj, config, record['reference_vertices'])
        record['settings'] = config
        record['simulation'] = simulate(obj, mod, a.frames)
        # Shape keys belong to the collapse collider, not this simulated mesh.
        bpy.context.scene['pilot_record'] = json.dumps(record)
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(a.out/'simulated.blend'))
    finish(a.out, obj, record, a.size)


if __name__ == '__main__':
    main()
