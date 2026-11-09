"""Retain the settled tunic and give its allowance a real opacity bake domain."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from age_tunic import save_checkpoint
from common import recalc
from polish_pass9 import vertex_pattern
from wear_pass10 import smoothstep


def open_shoulder(body):
    pattern = vertex_pattern(body)
    points = np.array([v.co[:] for v in body.data.vertices])
    u, v = pattern.T
    rear = (u > .48) & (u < 1.)
    fade = smoothstep((points[:, 0]-.165)/.025)*smoothstep((.255-points[:, 0])/.025)
    fade *= smoothstep((v-.85)/.085)*rear
    patch = body.vertex_groups['DetailPatch'].index
    protected = np.array([any(g.group == patch and g.weight > .1 for g in vertex.groups)
                          for vertex in body.data.vertices])
    board = bpy.data.objects['ShoulderBoard_L']
    support_back = max((board.matrix_world @ vertex.co).y for vertex in board.data.vertices)+.002
    protected &= points[:, 1] <= support_back
    fade[protected] = 0.
    from mathutils.bvhtree import BVHTree
    tree = BVHTree.FromObject(board, bpy.context.evaluated_depsgraph_get())
    inverse = board.matrix_world.inverted()
    clearance = np.array([tree.find_nearest(inverse @ (body.matrix_world @ vertex.co))[3]
                          for vertex in body.data.vertices])
    front = smoothstep((points[:, 0]-.180)/.020)*smoothstep((.255-points[:, 0])/.025)
    front *= smoothstep((v-.88)/.06)*(u < .48)*smoothstep((clearance-.008)/.006)
    for vertex, weight, forward in zip(body.data.vertices, fade, front):
        vertex.co.y += .008*weight-.012*forward
        vertex.co.z += .004*weight+.029*forward
    recalc(body)
    return dict(maximum_rear_lip_motion_m=float(fade.max()*np.hypot(.008, .004)),
                maximum_front_lip_motion_m=float(front.max()*np.hypot(.012, .029)),
                fitting_support_clearance_limit_m=.008,
                retained_binding_and_fitting_supports_unchanged=True)


def prepare(base, out, shoulder=True, shape=False):
    from bake_down import bake, material_maps
    from cloth_metrics import lip_lift
    bpy.ops.wm.open_mainfile(filepath=str(base/'baked.blend'))
    record = json.loads(bpy.context.scene['tunic5_record'])
    body = bpy.data.objects['TunicBody']
    report = dict(base=str(base.relative_to(ROOT)), age_years=1000)
    if shoulder:
        report['shoulder'] = open_shoulder(body)
    body['pass12_wear'] = True
    from lip_arclength import refine_physical_lips
    report['physical_lips'] = refine_physical_lips(body)
    if shape:
        from shape_pass12 import torn_hem, scatter_debris
        report['hem'] = torn_hem(body)
        report['heap'] = scatter_debris(record, report['hem']['removed_area_m2'])
        body['pass12_full_fringe'] = True
    patch = body.vertex_groups['DetailPatch'].index
    support = [v.index for v in body.data.vertices if any(g.group == patch and g.weight > 0 for g in v.groups)]
    report['protected_fitting_support_vertices'] = len(support)
    dense = bpy.data.objects['TunicBody_Dense']
    # The retained game sheet is the reference for this finishing pass.
    bpy.data.objects.remove(dense, do_unlink=True)
    dense = body.copy()
    dense.data = body.data.copy()
    bpy.context.collection.objects.link(dense)
    dense.name = 'TunicBody_Dense'
    dense['aged_export'] = False
    dense.hide_render = True
    dense.hide_set(True)
    report['allowance_faces'] = sum(p.material_index != 0 for p in body.data.polygons)
    if shape:
        from reduce_pass12 import reduce_body
        low, reduction = reduce_body(body, 7100)
        bpy.data.objects.remove(body, do_unlink=True)
        low.name = 'TunicBody'
        body = low
        record['reduction']['TunicBody'] = reduction
    mat, paths = bake(dense, body, out/'textures', size=2048, samples=8)
    material_maps(mat, (.025, .043, .08))
    dense.hide_render = True
    dense.hide_set(True)
    body['aged_export'] = True
    body['pass10_wear'] = True
    body['pass11_wear'] = True
    body['pass12_wear'] = True
    record['lip_lift'] = lip_lift(body)
    report['maps'] = paths
    report['allowance'] = 'same nondegenerate BakeUV atlas, wool base, opacity and cut-edge alpha as the sheet'
    record['pass12'] = report
    record['finish_opacity_size'] = 4096
    save_checkpoint(out, 'baked', record)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', type=Path, default=ROOT/'tmp/age/tunic11/visible')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--no-shoulder', action='store_true')
    p.add_argument('--shape', action='store_true')
    a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out/'textures').mkdir(exist_ok=True)
    prepare(a.base.resolve(), a.out.resolve(), not a.no_shoulder, a.shape)
