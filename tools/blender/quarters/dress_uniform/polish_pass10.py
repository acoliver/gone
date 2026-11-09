"""Finish the pass-nine checkpoint without replacing its settled cloth or fittings."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from age_tunic import save_checkpoint
from common import apply, recalc
from polish_pass9 import vertex_pattern
from wear_pass10 import finishing_displacement


def deform(obj):
    pattern = vertex_pattern(obj)
    points = np.array([v.co[:] for v in obj.data.vertices])
    delta = finishing_displacement(points, pattern)
    for vertex, point in zip(obj.data.vertices, points+delta):
        vertex.co = point
    recalc(obj)
    return dict(maximum_motion_m=float(np.linalg.norm(delta, axis=1).max()),
                maximum_rear_lip_opening_m=float(delta[:, 1].max()),
                maximum_hem_deepening_m=float(delta[:, 2].max()))


def bridge_roots(body):
    from fringe_boundary import boundary_chains
    from aging_cards import edge_groups
    edge_groups(body)
    chains = boundary_chains(body, 'Seam allowance')
    sleeve, torso = [], []
    uv = vertex_pattern(body)
    body.data.calc_loop_triangles()
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.verts.index_update()
    bm.normal_update()
    for edge in bm.edges:
        if not edge.is_boundary:
            continue
        ids = [v.index for v in edge.verts]
        pattern = uv[ids]
        a, b = [np.array(body.matrix_world @ v.co) for v in edge.verts]
        tangent = (b-a)/np.linalg.norm(b-a)
        inward = np.array(body.matrix_world @ edge.link_faces[0].calc_center_median())-(a+b)/2
        inward -= tangent*(inward@tangent)
        inward /= np.linalg.norm(inward)
        entry = (a, b, inward)
        if pattern[:, 0].min() > 1.09 and pattern[:, 0].max() < 1.56 and pattern[:, 1].max() < .001:
            sleeve.append(entry)
        elif np.max(np.abs(pattern[:, 0]-.46)) < .003 and pattern[:, 1].min() > .66:
            torso.append(entry)
    bm.free()
    if not sleeve or not torso:
        raise ValueError('Pass-ten bridges require the existing body and sleeve armhole lips')
    roots = []
    for height in [-.235, -.249, -.266, -.283, -.299]:
        candidates = []
        for a, b, inward in torso:
            t = np.clip((height-a[2])/(b[2]-a[2]), 0, 1) if abs(b[2]-a[2]) > 1e-9 else .5
            p = a+(b-a)*t
            candidates.append((abs(p[2]-height), p, inward))
        _, p, own_inward = min(candidates, key=lambda item: item[0])
        candidates = []
        for a, b, inward in sleeve:
            t = np.clip((p-a)@(b-a)/((b-a)@(b-a)), 0, 1)
            q = a+(b-a)*t
            candidates.append((np.linalg.norm(p-q), q, inward))
        gap, q, other_inward = min(candidates, key=lambda item: item[0])
        if .012 < gap < .050:
            p = p+own_inward*.007+np.array([0, -.0015, 0])
            q = q+other_inward*.007+np.array([0, -.0015, 0])
            roots.append([p.tolist(), q.tolist()])
    return roots


def prepare(base, out):
    from bake_down import boundary_hausdorff, material_maps
    from cloth_metrics import lip_lift
    from wool_material import wool_material
    bpy.ops.wm.open_mainfile(filepath=str(base/'baked.blend'))
    record = json.loads(bpy.context.scene['tunic5_record'])
    body = bpy.data.objects['TunicBody']
    report = dict(base=str(base.relative_to(ROOT)), age_years=1000, cloth=deform(body))
    dense = bpy.data.objects['TunicBody_Dense']
    report['dense_cloth'] = deform(dense)
    record['reduction']['TunicBody']['boundary_hausdorff_upper_m'] = boundary_hausdorff(dense, body)
    record['lip_lift'] = lip_lift(body)
    body['pass10_wear'] = True
    report['bridge_roots'] = bridge_roots(body)
    mound = bpy.data.objects['FibreDust']
    reduction = mound.modifiers.new('Budget for seam strands', 'DECIMATE')
    reduction.ratio = .68
    apply(mound, reduction)
    report['mound_triangles'] = len(mound.data.polygons)
    material_maps(mound.data.materials[0], (.34, .31, .26))
    record['heap_material'] = wool_material(mound, out/'textures', color=(.34, .31, .26))
    report['dust_albedo_linear'] = [.34, .31, .26]
    record['pass10'] = report
    record['finish_opacity_size'] = 4096
    save_checkpoint(out, 'baked', record)


def finish_details(record):
    from card_contacts import CardContacts
    from fabric_mesh import material, new_object
    objects = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.get('aged_export')]
    contacts = CardContacts(objects)
    vertices, faces = [], []
    accepted = []
    view = np.array([.3, -.9, .22])
    for number, roots in enumerate(record['pass10']['bridge_roots']):
        a, b = np.asarray(roots)
        t = np.linspace(0, 1, 9)
        path = a[None]*(1-t[:, None])+b[None]*t[:, None]
        path[:, 2] -= (.0025+number*.00035)*np.sin(np.pi*t)
        path[:, 1] -= .002*np.sin(np.pi*t)
        tangent = np.gradient(path, axis=0)
        sideways = np.cross(tangent, view)
        sideways /= np.linalg.norm(sideways, axis=1)[:, None]
        width = (.00065+number*.00006)*(.8+.2*np.sin(np.pi*t))
        left, right = path-sideways*width[:, None]/2, path+sideways*width[:, None]/2
        quads = [[left[i], right[i], right[i+1], left[i+1]] for i in range(len(t)-1)]
        if not all(contacts.clear(quad) for quad in quads):
            continue
        start = len(vertices)
        for l, r in zip(left, right):
            vertices.extend([l, r])
        for i in range(len(t)-1):
            faces.append((start+2*i, start+2*i+1, start+2*i+3, start+2*i+2))
        for quad in quads:
            contacts.add(quad)
        accepted.append(number)
    mat = material('Torn surviving wool yarn', (.064, .079, .108))
    mat.use_backface_culling = False
    shader = mat.node_tree.nodes['Principled BSDF']
    shader.inputs['Roughness'].default_value = .97
    shader.inputs['Specular IOR Level'].default_value = .12
    threads = new_object('ArmholeSurvivingYarns', vertices, faces, mat)
    threads['aged_export'] = True
    fibre = bpy.data.objects['HeapFibres']
    light_fibres = fibre.data.materials[0].copy()
    light_fibres.name = 'Loose pale wool fibres'
    shader = light_fibres.node_tree.nodes['Principled BSDF']
    for link in list(shader.inputs['Base Color'].links):
        light_fibres.node_tree.links.remove(link)
    shader.inputs['Base Color'].default_value = (.39, .35, .29, 1)
    fibre.data.materials[0] = light_fibres
    return dict(surviving_yarns=len(accepted), attempted_yarns=len(record['pass10']['bridge_roots']),
                accepted_roots=accepted, yarn_width_m=[.00065, .00089], collision_tested=True,
                dust_fibres_albedo_linear=[.39, .35, .29])


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', type=Path, default=ROOT/'tmp/age/tunic9/binding')
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out/'textures').mkdir(exist_ok=True)
    prepare(a.base.resolve(), a.out.resolve())
