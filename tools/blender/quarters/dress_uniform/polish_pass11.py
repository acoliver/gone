"""Refine the retained pass-ten tunic without rerunning its cloth simulation."""
import argparse
import json
from pathlib import Path
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from age_tunic import save_checkpoint
from common import recalc
from polish_pass9 import vertex_pattern
from wear_pass10 import smoothstep
from wear_pass11 import lip_loss, wool_displacement


def refine_lips(body):
    from torn_allowance import released_side
    bm = bmesh.new()
    bm.from_mesh(body.data)
    layer = bm.loops.layers.uv[0]
    deform = bm.verts.layers.deform.active
    released = body.vertex_groups['Lip shrink'].index
    keep = body.vertex_groups['Keep'].index

    def torn(edge):
        if not edge.is_boundary:
            return False
        uv = np.array([loop[layer].uv[:] for v in edge.verts for loop in v.link_loops])
        shoulder = (uv[:, 0].max() < 1. and np.max(abs(uv[:, 1]-.94)) < .001 and
                    min(v.co.x for v in edge.verts) > .175 and
                    all(v[deform].get(released, 0.) >= .5 for v in edge.verts))
        return shoulder or bool(released_side(edge, layer))

    for edge in [e for e in bm.edges if torn(e)]:
        cuts = max(0, int(np.ceil(edge.calc_length()/.0018))-1)
        if cuts:
            bmesh.ops.subdivide_edges(bm, edges=[edge], cuts=cuts, use_grid_fill=False)
    bm.normal_update()
    directions, depths = {}, {}
    edges = {e for e in bm.edges if torn(e)}
    bm.verts.index_update()
    stations = {}
    component = 0
    remaining = edges.copy()
    while remaining:
        degree = {}
        for edge in remaining:
            for vertex in edge.verts:
                degree[vertex] = degree.get(vertex, 0)+1
        current = min([v for v in degree if degree[v] == 1] or list(degree), key=lambda v: v.index)
        station = 0.
        while True:
            stations[current] = station+component*.937
            edge = next((e for e in current.link_edges if e in remaining), None)
            if edge is None:
                break
            remaining.remove(edge)
            station += edge.calc_length()
            current = edge.other_vert(current)
        component += 1
    for edge in edges:
        tangent = (edge.verts[1].co-edge.verts[0].co).normalized()
        middle = (edge.verts[0].co+edge.verts[1].co)/2
        face = edge.link_faces[0]
        inward = face.calc_center_median()-middle
        inward = (inward-tangent*inward.dot(tangent)).normalized()
        depth = max((v.co-middle).dot(inward) for v in face.verts)
        for vertex in edge.verts:
            directions.setdefault(vertex, []).append(inward)
            depths.setdefault(vertex, []).append(depth)
    count = 0
    maximum = 0.
    for vertex, inward in directions.items():
        point = np.array(vertex.co)
        # Arclength avoids constant noise on lips perpendicular to a world-space projection.
        scale = float(smoothstep((point[0]-.175)/.035))
        # Keep each loss within its supporting face instead of folding a thin
        # allowance back through its own root.
        loss = float(lip_loss(stations[vertex], min(depths[vertex])))*scale
        direction = sum(inward, Vector()).normalized()
        vertex.co += direction*loss
        vertex[deform][keep] = 1.
        maximum = max(maximum, loss)
        count += 1
    bm.to_mesh(body.data)
    bm.free()
    recalc(body)
    return dict(vertices=count, maximum_additional_loss_m=maximum,
                boundary_spacing_m=.0018, method='arclength multiscale losses within supporting face depth; no contour threshold changes')


def prepare(base, out, refine=False):
    from bake_down import decimate
    from cloth_metrics import lip_lift
    bpy.ops.wm.open_mainfile(filepath=str(base/'baked.blend'))
    record = json.loads(bpy.context.scene['tunic5_record'])
    body = bpy.data.objects['TunicBody']
    pattern = vertex_pattern(body)
    points = np.array([v.co[:] for v in body.data.vertices])
    delta = wool_displacement(points, pattern)
    for vertex, point in zip(body.data.vertices, points+delta):
        vertex.co = point
    recalc(body)
    report = dict(base=str(base.relative_to(ROOT)), age_years=1000,
                  wool_motion_maximum_m=float(np.linalg.norm(delta, axis=1).max()),
                  lips=refine_lips(body) if refine else dict(retained_pass10=True))
    bpy.data.objects.remove(bpy.data.objects['TunicBody_Dense'], do_unlink=True)
    body.name = 'TunicBody_Dense'
    body['pass11_wear'] = True
    low, reduction = decimate(body, 9550 if refine else 10000, protect=.006, keep_factor=1000)
    body['aged_export'] = False
    body.hide_render = True
    body.hide_set(True)
    low.name = 'TunicBody'
    low['aged_export'] = True
    record['reduction']['TunicBody'] = reduction
    record['lip_lift'] = lip_lift(low)
    report['reduction_reference'] = 'retained pass-ten game sheet with pass-eleven wool motion and lip losses before reduction'
    record['pass11'] = report
    record['finish_opacity_size'] = 4096
    save_checkpoint(out, 'baked', record)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, default=ROOT/'tmp/age/tunic10/curled')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--refine-lips', action='store_true', help='Build the experimental physical-lip variant')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out/'textures').mkdir(exist_ok=True)
    prepare(args.base.resolve(), args.out.resolve(), refine=args.refine_lips)
