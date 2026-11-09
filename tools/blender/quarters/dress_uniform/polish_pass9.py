"""Local finishing deformations of the settled tunic8, without another cloth solve."""
import argparse
import json
from pathlib import Path
import sys
import subprocess

import bmesh
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from age_tunic import save_checkpoint
from common import apply, recalc


def vertex_pattern(obj):
    coordinates = np.zeros((len(obj.data.vertices), 2))
    layer = obj.data.uv_layers[0].data
    for loop in obj.data.loops:
        coordinates[loop.vertex_index] = layer[loop.index].uv
    return coordinates


def turn_sleeve(body):
    uv = vertex_pattern(body)
    ids = np.flatnonzero((uv[:, 0] > 1.09) & (uv[:, 0] < 1.56))
    points = np.array([body.data.vertices[i].co[:] for i in ids])
    stations = np.linspace(0, 1, 101)
    centers = np.array([points[np.abs(uv[ids, 1]-s) < .025].mean(0) for s in stations])
    center = np.column_stack([np.interp(uv[ids, 1], stations, centers[:, k]) for k in range(3)])
    weight = np.clip((uv[ids, 1]-.08)/.40, 0, 1)
    angle = np.radians(-8)*weight**2*(3-2*weight)
    delta = points-center
    turned = points.copy()
    turned[:, 0] = center[:, 0]+delta[:, 0]*np.cos(angle)-delta[:, 1]*np.sin(angle)
    turned[:, 1] = center[:, 1]+delta[:, 0]*np.sin(angle)+delta[:, 1]*np.cos(angle)
    for i, p in zip(ids, turned):
        body.data.vertices[i].co = p
    recalc(body)
    return dict(maximum_twist_degrees=-8, cap_unchanged_to_pattern_v=.08,
                maximum_vertex_motion_m=float(np.linalg.norm(turned-points, axis=1).max()),
                method='smooth row-centred twist of the existing settled pressed sleeve')


def round_hem(body):
    uv = vertex_pattern(body)
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    boundary = {v.index for e in bm.edges if e.is_boundary for v in e.verts
                if uv[v.index, 0] < 1. and uv[v.index, 1] < .06 and v.co.z < -.77}
    neighbors = {i: [] for i in boundary}
    for e in bm.edges:
        a, b = [v.index for v in e.verts]
        if e.is_boundary and a in boundary and b in boundary:
            neighbors[a].append(b)
            neighbors[b].append(a)
    points = np.array([v.co[:] for v in bm.verts])
    initial = points.copy()
    for _ in range(6):
        next_points = points.copy()
        for i, adjacent in neighbors.items():
            if len(adjacent) == 2:
                next_points[i] += .38*(points[adjacent].mean(0)-points[i])
        points = next_points
    displacement = points-initial
    fixed = displacement.copy()
    adjacency = [[] for _ in points]
    for edge in bm.edges:
        a, b = [v.index for v in edge.verts]
        adjacency[a].append(b)
        adjacency[b].append(a)
    for _ in range(8):
        following = displacement.copy()
        for i, adjacent in enumerate(adjacency):
            if i not in boundary and initial[i, 2] < -.75:
                following[i] = .85*np.mean(displacement[adjacent], axis=0)
        following[list(boundary)] = fixed[list(boundary)]
        displacement = following
    for v, p in zip(bm.verts, initial+displacement):
        v.co = Vector(p)
    bm.to_mesh(body.data)
    bm.free()
    recalc(body)
    return dict(maximum_motion_m=float(np.linalg.norm(displacement, axis=1).max()),
                method='six boundary-curvature steps diffused through the hem backing; no new cut rectangles')


def broad_folds(body):
    uv = vertex_pattern(body)
    initial = np.array([v.co[:] for v in body.data.vertices])
    motions = []
    for v in body.data.vertices:
        x, y, z = v.co
        weight = float(np.clip((-z-.34)/.10, 0, 1)*np.clip((z+.80)/.10, 0, 1))
        if uv[v.index, 0] >= 1.:
            weight = 0.
        delta = .0018*weight*np.sin(x*43+z*19)*np.sin(z*31+.6)
        v.co += v.normal*delta
        motions.append(abs(delta))
    recalc(body)
    return dict(maximum_normal_displacement_m=max(motions), amplitude_m=.0018,
                method='low-amplitude normal folds below attachments; no changes to the shoulder rest solve')


def crumple_strip(obj, number, supports):
    from common import surface_tree
    trees = [surface_tree(o) for o in supports]
    points = np.array([obj.matrix_world @ v.co for v in obj.data.vertices])
    center = points[:, :2].mean(0)
    axis = np.linalg.svd(points[:, :2]-center)[2][0]
    across = np.array([-axis[1], axis[0]])
    coordinates = (points[:, :2]-center) @ np.array([axis, across]).T
    s, t = coordinates.T
    stations = np.linspace(s.min(), s.max(), 1024)
    phase = .8+number*1.1
    bend = .45*np.sin(2*np.pi*(stations-stations[0])/np.ptp(stations)+phase)
    step = np.diff(stations)
    along = np.r_[0., np.cumsum((np.cos(bend[:-1])+np.cos(bend[1:]))*.5*step)]
    lateral = np.r_[0., np.cumsum((np.sin(bend[:-1])+np.sin(bend[1:]))*.5*step)]
    along -= np.mean(along)
    lateral -= np.mean(lateral)
    angle = np.interp(s, stations, bend)
    sideways = -axis[None, :]*np.sin(angle[:, None])+across[None, :]*np.cos(angle[:, None])
    xy = center+np.interp(s, stations, along)[:, None]*axis+np.interp(s, stations, lateral)[:, None]*across
    xy += t[:, None]*sideways
    wave = 2*np.pi*(s-s.min())/np.ptp(s)+phase
    width = max(abs(t).max(), 1e-8)
    lift = .0012+.007*(.5+.5*np.sin(wave))+.002*(1+t/width*np.sin(wave*.7))
    height = []
    for point, extra in zip(xy, lift):
        levels = [-.95]
        for tree in trees:
            hit, _, _, _ = tree.ray_cast(Vector((*point, -.75)), Vector((0, 0, -1)))
            if hit is not None:
                levels.append(hit.z)
        height.append(max(levels)+extra)
    inverse = obj.matrix_world.inverted()
    for vertex, point, z in zip(obj.data.vertices, xy, height):
        vertex.co = inverse @ Vector((*point, z))
    recalc(obj)
    return dict(method='curved arclength spine and transverse crumple seated over deposit and earlier strips',
                lift_range_m=[float(lift.min()), float(lift.max())], vertices=len(points))


def soften_debris(record, out):
    from bake_down import decimate
    from fabric_mesh import new_object
    report = {}
    lost = sum(piece['lost_area_m2'] for piece in record['fallen'])
    subprocess.run(['/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python',
                    str(Path(__file__).with_name('build_fibre_heap.py')), '--lost-area', str(lost),
                    '--out', str(out/'heap.npz')], check=True)
    data = np.load(out/'heap.npz')
    old_dense = bpy.data.objects['FibreDust_Dense']
    mat = old_dense.data.materials[0]
    bpy.data.objects.remove(old_dense, do_unlink=True)
    dense = new_object('FibreDust_Dense', data['vertices'], data['faces'], mat)
    dense.location.z = -.95
    record['heap'] = json.loads((out/'heap.json').read_text())
    modifier = dense.modifiers.new('Soft fibre deposition', 'SMOOTH')
    modifier.factor, modifier.iterations = .65, 6
    apply(dense, modifier)
    old = bpy.data.objects['FibreDust']
    bpy.data.objects.remove(old, do_unlink=True)
    mound, reduction = decimate(dense, 900, protect=0.)
    mound.name = 'FibreDust'
    mound['aged_export'] = True
    mound.hide_render = False
    mound.hide_set(False)
    dense['aged_export'] = False
    dense.hide_render = True
    dense.hide_set(True)
    record['heap_reduction'] = reduction
    report['mound'] = dict(method='compact-support SDF deposit, faired before reduction and normal bake', reduction=reduction)
    supports = [mound]
    for number, piece in enumerate(record['fallen']):
        obj = bpy.data.objects[piece['name']]
        modifier = obj.modifiers.new('Round allowance folds', 'SUBSURF')
        modifier.levels = 1
        apply(obj, modifier)
        report[obj.name] = crumple_strip(obj, number, supports)
        supports.append(obj)
    return report


def prepare(base, out):
    bpy.ops.wm.open_mainfile(filepath=str(base/'simulated.blend'))
    record = json.loads(bpy.context.scene['tunic5_record'])
    body = bpy.data.objects['TunicBody']
    record['pass9'] = dict(base=str(base.relative_to(ROOT)), sleeve=turn_sleeve(body),
                           hem=round_hem(body), folds=broad_folds(body), debris=soften_debris(record, out))
    record['finish_opacity_size'] = 4096
    record['reduction_targets'] = {piece['name']: 400 for piece in record['fallen']}
    save_checkpoint(out, 'simulated', record)


def boards(out):
    from board_seating import seat_boards
    bpy.ops.wm.open_mainfile(filepath=str(out/'baked.blend'))
    record = json.loads(bpy.context.scene['tunic5_record'])
    record['pass9']['board_seating'] = seat_boards(bpy.data.objects['TunicBody'], record['bindings'])
    save_checkpoint(out, 'baked', record)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', type=Path, default=ROOT/'tmp/age/tunic8/final')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--stage', choices=['prepare', 'boards'], required=True)
    a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    a.out.mkdir(parents=True, exist_ok=True)
    prepare(a.base.resolve(), a.out.resolve()) if a.stage == 'prepare' else boards(a.out.resolve())
