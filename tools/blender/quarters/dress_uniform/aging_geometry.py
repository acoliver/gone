"""Dense tunic bands and seam failures, with zero-area splits before gravity."""
import json

import bmesh
import bpy
import numpy as np
from mathutils import Vector

from aging_support import ROOT
from densify import triangulate
from tear_paths import lift_pattern_path, split_polyline
from common import recalc


def face_panel(face, uv):
    u = np.mean([loop[uv].uv.x for loop in face.loops])
    return 'front' if u < .48 else 'back' if u < 1. else 'left' if u < 1.6 else 'right'


def seam_edges(bm, kind):
    uv = bm.loops.layers.uv.active
    result = []
    for edge in bm.edges:
        labels = {face_panel(f, uv) for f in edge.link_faces}
        middle = (edge.verts[0].co+edge.verts[1].co)/2
        if kind == 'shoulder':
            chosen = labels == {'front', 'back'} and middle.x > .09 and middle.z > -.22
        else:
            chosen = 'left' in labels and bool(labels & {'front', 'back'})
        if chosen:
            result.append(edge)
    return result


def refine(body):
    from common import surface_tree
    # Keep the sewn pattern grid as the rest carrier. Decimating graded tear
    # bands before SIMPLE subdivision produced 0.069 mm triangle altitudes.
    report = {'unaged_vertices': len(body.data.vertices),
              'rest_quality': {'method': 'source-grid carrier; no pre-simulation collapse'}}
    report['dense_vertices'] = len(body.data.vertices)
    report['mass_multiplier'] = 1.
    lengths = np.array([(body.data.vertices[e.vertices[0]].co-body.data.vertices[e.vertices[1]].co).length
                        for e in body.data.edges])
    report['edge_quantiles_m'] = np.quantile(lengths, [.1, .5, .9]).tolist()
    # Catmull-Clark rounds the sewn contact crest down into the wire. Raise
    # the narrow contact band vertically, keeping front/back pattern order.
    wire = surface_tree(bpy.data.objects['Hanger'])
    adjusted = 0
    for vertex in body.data.vertices:
        p = vertex.co
        if .085 < abs(p.x) < .27 and abs(p.y) < .010 and p.z > -.24:
            contact, _, _, _ = wire.ray_cast(Vector((p.x, 0, .1)), Vector((0, 0, -1)))
            if contact is not None and p.z > contact.z-.020:
                clearance = .004*float(np.clip((.010-abs(p.y))/.004, 0, 1))
                target = contact.z+clearance
                if p.z < target:
                    p.z = target
                    adjusted += 1
    report['wire_clearance_m'] = .004
    report['contact_vertices_adjusted'] = adjusted
    return report


def split_seam(body, kind, fraction):
    bm = bmesh.new()
    bm.from_mesh(body.data)
    edges = seam_edges(bm, kind)
    total = sum(e.calc_length() for e in edges)
    if not total:
        raise ValueError(f'Missing {kind} seam in pattern UVs')
    if kind == 'shoulder':
        edges.sort(key=lambda e: abs(sum(v.co.x for v in e.verts)/2-.19))
    else:
        # Front arc first, then the cap's back quadrant. Underarm/back remain sewn.
        edges.sort(key=lambda e: (sum(v.co.y for v in e.verts) > 0,
                                  -sum(v.co.z for v in e.verts)))
    chosen, length = [], 0.
    for edge in edges:
        if length+edge.calc_length()/2 > total*fraction:
            break
        chosen.append(edge)
        length += edge.calc_length()
    deform = bm.verts.layers.deform.verify()
    group = body.vertex_groups.get('Lip shrink') or body.vertex_groups.new(name='Lip shrink')
    allowance = (body.vertex_groups.get('Seam allowance') or body.vertex_groups.new(name='Seam allowance')) if kind == 'armhole' else None
    for edge in chosen:
        for vertex in edge.verts:
            vertex[deform][group.index] = 1.
            if allowance is not None:
                vertex[deform][allowance.index] = 1.
    bmesh.ops.split_edges(bm, edges=chosen)
    bm.to_mesh(body.data)
    bm.free()
    return dict(seam_length_m=total, split_length_m=length, released_fraction=length/total,
                retained_fraction=1-length/total, method='split shared seam edges; no deleted area')


def cut_tunic(body):
    record = {'armhole': split_seam(body, 'armhole', .59),
              'shoulder': split_seam(body, 'shoulder', .60)}
    # The seam already follows the hanger crest. A second parallel slit only
    # 5 mm away made an unresolved strip between two coincident split lips.
    record['hanger'] = dict(record['shoulder'], method='hanger wear follows the released shoulder seam')
    hems = []
    for lo, hi in [(.035, .145), (.29, .395), (.58, .70)]:
        # End cuts detach an allowance; their vertices remain in the cloth model.
        path_uv = [(lo, 0.), (lo, .038)]
        path_uv += [(u, .038) for u in np.linspace(lo, hi, 30)[1:]]
        path_uv += [(hi, 0.)]
        path = lift_pattern_path(body, np.array(path_uv))
        hems.append(split_polyline(body, path))
    record['hem_runs'] = hems
    record['hem_runs_count'] = len(hems)
    record['hem_released_pattern_fraction'] = sum(hi-lo for lo, hi in [(.035, .145), (.29, .395), (.58, .70)])/.92
    triangulate(body)
    recalc(body)
    return record


def pressed_sleeve(body):
    body.shape_key_add(name='Aged basis')
    rest = body.shape_key_add(name='Empty pressed left sleeve')
    from pressed_pattern import press_rows
    uv = body.data.uv_layers[0].data
    coordinates = {}
    for loop in body.data.loops:
        point = uv[loop.index].uv
        if 1.099 < point.x < 1.551:
            old = coordinates.get(loop.vertex_index)
            if old is None or point.x < old[0]:
                coordinates[loop.vertex_index] = tuple(point)
    sleeve = sorted(coordinates)
    original = np.array([body.data.vertices[index].co[:] for index in sleeve])
    pressed = press_rows(original, np.array([coordinates[index] for index in sleeve]))
    for index, point in zip(sleeve, pressed):
        rest.data[index].co = Vector(point)
    offsets = open_lip_rest(body, rest)
    # Structural springs take their lengths from the starting mesh, whereas
    # rest_shape_key supplies bending angles. Both must describe empty wool.
    basis = body.data.shape_keys.key_blocks[0]
    for index, offset in offsets.items():
        basis.data[index].co += offset
        body.data.vertices[index].co = basis.data[index].co
    for index in sleeve:
        basis.data[index].co = rest.data[index].co
        body.data.vertices[index].co = rest.data[index].co
    body.data.update()
    return rest


def open_lip_rest(body, rest):
    """Rest contraction pulls split lips apart, fading into each retained ply."""
    import heapq
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.verts.ensure_lookup_table()
    deform = bm.verts.layers.deform.active
    group = body.vertex_groups['Lip shrink'].index
    vectors = {}
    for edge in bm.edges:
        if (not edge.is_boundary or max(v.co.z for v in edge.verts) < -.80 or
                not all(v[deform].get(group, 0.) >= .5 for v in edge.verts)):
            continue
        a, b = edge.verts
        tangent = (b.co-a.co).normalized()
        inward = edge.link_faces[0].calc_center_median()-(a.co+b.co)/2
        inward = (inward-tangent*inward.dot(tangent)).normalized()
        for vertex in edge.verts:
            vectors[vertex.index] = vectors.get(vertex.index, Vector())+inward*edge.calc_length()
    distances = {i: 0. for i in vectors}
    origin = {i: i for i in vectors}
    queue = [(0., i) for i in sorted(vectors)]
    heapq.heapify(queue)
    while queue:
        distance, index = heapq.heappop(queue)
        if distance != distances[index]:
            continue
        for edge in bm.verts[index].link_edges:
            j = edge.other_vert(bm.verts[index]).index
            candidate = distance+edge.calc_length()
            if candidate < .025 and candidate < distances.get(j, float('inf')):
                distances[j], origin[j] = candidate, origin[index]
                heapq.heappush(queue, (candidate, j))
    rng = np.random.default_rng(9521)
    indices = sorted(vectors)
    points = np.array([bm.verts[i].co[:] for i in indices])
    weights = np.exp(-np.sum((points[:, None]-points[None, :])**2, axis=2)/(2*.012**2))
    variation = weights@rng.normal(size=len(indices))/np.sqrt(np.sum(weights**2, axis=1))
    width = {i: float(np.clip(.85+.25*w, .8, 1.5)) for i, w in zip(indices, variation)}
    directions = np.array([vectors[i].normalized()[:] for i in indices])
    uv = bm.loops.layers.uv.active
    panels = [face_panel(bm.verts[i].link_faces[0], uv) for i in indices]
    for k, i in enumerate(indices):
        delta = points-points[k]
        along = delta@directions[k]
        lateral = np.linalg.norm(delta-along[:, None]*directions[k], axis=1)
        opposing = ((directions@directions[k] < -.5) & (along > 1e-5) &
                    (along < .02) & (lateral < .004) &
                    (np.array(panels) == panels[k]))
        if opposing.any():
            # A strip between two nearby splits cannot contract past itself.
            width[i] = min(width[i], .3*float(along[opposing].min())/.007)
    offsets = {}
    for i, distance in distances.items():
        vector = vectors[origin[i]]
        if vector.length:
            contraction = .002 if bm.verts[origin[i]].co.z > -.22 else .003
            offset = vector.normalized()*(contraction*width[origin[i]]*(1-distance/.025))
            rest.data[i].co += offset
            offsets[i] = offset
    bm.free()
    return offsets


def detach_fallen(body):
    """Separate only disconnected hem islands; retain the body/sleeve bridges."""
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.verts.ensure_lookup_table()
    uv = bm.loops.layers.uv.active
    remaining = set(bm.verts)
    groups = []
    while remaining:
        frontier = {remaining.pop()}
        group = set(frontier)
        while frontier:
            following = {e.other_vert(v) for v in frontier for e in v.link_edges} & remaining
            remaining -= following
            group |= following
            frontier = following
        groups.append(group)
    islands = sorted((g for g in groups if max(v.co.z for v in g) < -.80),
                     key=lambda g: min(v.co.x for v in g))
    reports = []
    for number, group in enumerate(islands):
        faces = sorted({f for v in group for f in v.link_faces}, key=lambda f: f.index)
        indices = {v: i for i, v in enumerate(sorted(group, key=lambda v: v.index))}
        data = bpy.data.meshes.new(f'FallenHem_{number+1}')
        data.from_pydata([tuple(v.co) for v in indices], [],
                         [tuple(indices[v] for v in f.verts) for f in faces])
        layer = data.uv_layers.new(name='FlatPattern')
        for polygon, source in zip(data.polygons, faces):
            for index, loop in zip(polygon.loop_indices, source.loops):
                layer.data[index].uv = loop[uv].uv
        data.materials.append(body.data.materials[0])
        obj = bpy.data.objects.new(data.name, data)
        bpy.context.collection.objects.link(obj)
        obj['aged_export'] = True
        initial_area = sum(f.calc_area() for f in faces)
        lost_area = 0.
        if number == 2:
            loose = bmesh.new()
            loose.from_mesh(data)
            midpoint = (min(v.co.x for v in loose.verts)+max(v.co.x for v in loose.verts))/2
            dust_faces = [f for f in loose.faces if f.calc_center_median().x > midpoint]
            lost_area = sum(f.calc_area() for f in dust_faces)
            bmesh.ops.delete(loose, geom=dust_faces, context='FACES')
            bmesh.ops.delete(loose, geom=[v for v in loose.verts if not v.link_faces], context='VERTS')
            loose.to_mesh(data)
            loose.free()
        reports.append(dict(name=obj.name, area_m2=initial_area-lost_area,
                            lost_area_m2=lost_area, vertices=len(data.vertices)))
        bmesh.ops.delete(bm, geom=list(group), context='VERTS')
    bm.to_mesh(body.data)
    bm.free()
    return reports
