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
from common import recalc
from polish_pass9 import vertex_pattern
from wear_pass10 import finishing_displacement


def deform(body):
    pattern = vertex_pattern(body)
    points = np.array([v.co[:] for v in body.data.vertices])
    delta = finishing_displacement(points, pattern)
    for vertex, point in zip(body.data.vertices, points+delta):
        vertex.co = point
    recalc(body)
    return dict(maximum_motion_m=float(np.linalg.norm(delta, axis=1).max()),
                maximum_rear_lip_opening_m=float(delta[:, 1].max()),
                maximum_hem_deepening_m=float(delta[:, 2].max()))


def bridge_roots(body):
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
        if (pattern[:, 0].min() > 1.09 and pattern[:, 0].max() < 1.56 and
                pattern[:, 1].max() < .001 and edge.link_faces[0].normal.y < -.3):
            sleeve.append(entry)
        elif np.max(np.abs(pattern[:, 0]-.46)) < .003 and pattern[:, 1].min() > .66:
            torso.append(entry)
    bm.free()
    if not sleeve or not torso:
        raise ValueError('Pass-ten bridges require the existing body and sleeve armhole lips')
    roots = []
    for height in [-.235, -.244, -.253, -.266, -.278, -.290]:
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
        if .009 < gap < .055:
            p = p+own_inward*.007+np.array([0, -.0015, 0])
            q = q+other_inward*.007+np.array([0, -.0015, 0])
            roots.append([p.tolist(), q.tolist()])
    return roots


def prepare(base, out):
    from bake_down import decimate, material_maps
    from cloth_metrics import lip_lift
    from torn_allowance import add_allowances, ragged_shoulders
    from wool_material import wool_material
    bpy.ops.wm.open_mainfile(filepath=str(base/'baked.blend'))
    record = json.loads(bpy.context.scene['tunic5_record'])
    body = bpy.data.objects['TunicBody']
    report = dict(base=str(base.relative_to(ROOT)), age_years=1000, cloth=deform(body))
    report['shoulder'] = ragged_shoulders(body)
    report['allowance'] = add_allowances(body)
    bpy.data.objects.remove(bpy.data.objects['TunicBody_Dense'], do_unlink=True)
    body.name = 'TunicBody_Dense'
    body['pass10_wear'] = True
    keep = body.vertex_groups['Keep']
    patch = body.vertex_groups['DetailPatch'].index
    protected = [v.index for v in body.data.vertices if abs(v.co.x) < .035 or v.co.z > -.26 or
                 any(g.group == patch and g.weight > .1 for g in v.groups)]
    keep.add(protected, 1., 'REPLACE')
    low, reduction = decimate(body, 10450, protect=.006, keep_factor=1000)
    reduction['seated_support_protected_vertices'] = len(protected)
    body['aged_export'] = False
    body.hide_render = True
    body.hide_set(True)
    low.name = 'TunicBody'
    low['aged_export'] = True
    body = low
    record['reduction']['TunicBody'] = reduction
    report['reduction_reference'] = 'pass-nine game sheet with authored pass-ten folds, hem and connected allowances, before reduction'
    record['lip_lift'] = lip_lift(body)
    report['bridge_roots'] = bridge_roots(body)
    mound = bpy.data.objects['FibreDust']
    report['mound_triangles'] = len(mound.data.polygons)
    material_maps(mound.data.materials[0], (.34, .31, .26))
    record['heap_material'] = wool_material(mound, out/'textures', color=(.34, .31, .26))
    report['dust_albedo_linear'] = [.34, .31, .26]
    record['pass10'] = report
    record['finish_opacity_size'] = 4096
    save_checkpoint(out, 'baked', record)


def finish_details(record):
    from card_contacts import CardContacts
    from common import surface_tree
    from fabric_mesh import material, new_object
    objects = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.get('aged_export')]
    contacts = CardContacts(objects)
    tree = surface_tree(bpy.data.objects['TunicBody'])
    vertices, faces = [], []
    accepted = []
    view = np.array([.3, -.9, .22])
    view /= np.linalg.norm(view)
    for number, roots in enumerate(record['pass10']['bridge_roots']):
        anchors = []
        for root in roots:
            hit, _, _, _ = tree.ray_cast(Vector(np.asarray(root)+view*.12), Vector(-view), .24)
            if hit is not None:
                anchors.append(np.asarray(hit)+view*.0008)
        if len(anchors) != 2:
            continue
        a, b = anchors
        t = np.linspace(0, 1, 9)
        path = a[None]*(1-t[:, None])+b[None]*t[:, None]
        path[:, 2] -= (.0035+number*.00035)*np.sin(np.pi*t)
        path += view[None]*.006*np.sin(np.pi*t[:, None])
        tangent = np.gradient(path, axis=0)
        sideways = np.cross(tangent, view)
        sideways /= np.linalg.norm(sideways, axis=1)[:, None]
        width = (.00095+number*.00006)*(.8+.2*np.sin(np.pi*t))
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
                accepted_roots=accepted, yarn_width_m=[.00095, .00125], collision_tested=True,
                dust_fibres_albedo_linear=[.39, .35, .29])


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', type=Path, default=ROOT/'tmp/age/tunic9/binding')
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out/'textures').mkdir(exist_ok=True)
    prepare(a.base.resolve(), a.out.resolve())
