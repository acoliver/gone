"""Seat rigid fittings against continuous reduced wool triangles, not vertex samples."""
import bpy
import numpy as np
from mathutils import Vector

from common import recalc


def triangles(obj):
    obj.data.calc_loop_triangles()
    vertices = np.array([obj.matrix_world @ v.co for v in obj.data.vertices])
    return vertices[np.array([t.vertices[:] for t in obj.data.loop_triangles])]


def cross2(a, b):
    return a[0]*b[1]-a[1]*b[0]


def overlap_polygon(subject, clip):
    polygon = list(subject)
    orientation = np.sign(cross2(clip[1]-clip[0], clip[2]-clip[0]))
    for start, end in zip(clip, np.roll(clip, -1, axis=0)):
        output = []
        if not polygon:
            break
        previous = polygon[-1]
        old = orientation*cross2(end-start, previous-start)
        for point in polygon:
            new = orientation*cross2(end-start, point-start)
            if (new >= 0) != (old >= 0):
                output.append(previous+(point-previous)*(old/(old-new)))
            if new >= 0:
                output.append(point)
            previous, old = point, new
        polygon = output
    return np.asarray(polygon)


def continuous_gap(detail_triangles, support_triangles, normal):
    transverse = np.linalg.svd(np.array([normal]))[2][1:]
    frame = np.vstack([transverse, normal])
    detail = detail_triangles @ frame.T
    support = support_triangles @ frame.T
    area = ((support[:, 1, 0]-support[:, 0, 0])*(support[:, 2, 1]-support[:, 0, 1])-
            (support[:, 1, 1]-support[:, 0, 1])*(support[:, 2, 0]-support[:, 0, 0]))
    support = support[np.abs(area) > 1e-12]
    low, high = support[:, :, :2].min(1), support[:, :, :2].max(1)
    minimum = float('inf')
    for face in detail:
        xy = face[:, :2]
        if abs(cross2(xy[1]-xy[0], xy[2]-xy[0])) < 1e-12:
            continue
        candidates = np.flatnonzero(np.all((high >= xy.min(0)) & (low <= xy.max(0)), axis=1))
        own_plane = np.linalg.solve(np.c_[xy, np.ones(3)], face[:, 2])
        for index in candidates:
            other = support[index]
            polygon = overlap_polygon(xy, other[:, :2])
            if len(polygon) < 3:
                continue
            plane = np.linalg.solve(np.c_[other[:, :2], np.ones(3)], other[:, 2])
            gap = np.c_[polygon, np.ones(len(polygon))] @ (own_plane-plane)
            minimum = min(minimum, float(gap.min()))
    if not np.isfinite(minimum):
        raise ValueError('Rigid fitting has no projected support area')
    return minimum


def seat_details(body, bindings):
    report = {}
    for name, binding in bindings.items():
        if not binding['rigid']:
            continue
        obj = bpy.data.objects[name]
        if obj.get('surface_seated_board'):
            continue
        original = np.array(binding['original'])
        destination = np.array([obj.matrix_world @ v.co for v in obj.data.vertices])
        shifts = []
        supports = [body]
        support = ('Collar' if name.startswith('CollarInsignia') else
                   'Placket' if name == 'Buttons' else 'RibbonBar' if name == 'Medal' else None)
        if support:
            supports.append(bpy.data.objects[support])
        support_faces = np.concatenate([triangles(o) for o in supports])
        obj.data.calc_loop_triangles()
        for ids in binding['groups']:
            src, dst = original[ids], destination[ids]
            u, _, vt = np.linalg.svd((src-src.mean(0)).T@(dst-dst.mean(0)))
            rotation = u@vt
            if np.linalg.det(rotation) < 0:
                u[:, -1] *= -1
                rotation = u@vt
            axis = np.array([0., 0., 1.]) if name.startswith('ShoulderBoard') else np.array([0., -1., 0.])
            normal = axis@rotation
            group = set(ids)
            faces = np.array([t.vertices[:] for t in obj.data.loop_triangles if set(t.vertices) <= group])
            gap = continuous_gap(destination[faces], support_faces, normal)
            shift = max(0., .0005-gap)
            destination[ids] += normal*shift
            shifts.append(shift)
        inverse = obj.matrix_world.inverted()
        for vertex, point in zip(obj.data.vertices, destination):
            vertex.co = inverse @ Vector(point)
        recalc(obj)
        report[name] = dict(clearance_m=.0005, additional_rigid_translation_m=shifts,
                            support='continuous projected overlap of actual reduced triangles')
    return report


def seat_sewn(body, bindings):
    from common import surface_tree
    tree = surface_tree(body)
    report = {}
    for name in ('ShoulderBoard_L', 'ShoulderBoard_R', 'Placket', 'RibbonBar'):
        if bindings[name].get('rigid', False):
            continue
        obj = bpy.data.objects[name]
        original = np.asarray(bindings[name]['original'])
        count = len(original)//2
        if len(original) != count*2:
            raise ValueError(f'{name}: expected paired facing vertices')
        points = np.array([obj.matrix_world @ v.co for v in obj.data.vertices])
        maximum = 0.
        for i in range(count):
            middle = (points[i]+points[i+count])/2
            hit, normal, _, distance = tree.find_nearest(Vector(middle))
            maximum = max(maximum, distance)
            thickness = float(np.linalg.norm(original[i+count]-original[i]))
            source_normal = np.asarray(bindings[name]['entries'][i]['offset_frame'])[2]
            sign = float(np.dot(original[i+count]-original[i], source_normal))
            lower, upper = (i, i+count) if sign >= 0 else (i+count, i)
            points[lower] = np.asarray(hit)+np.asarray(normal)*.0005
            points[upper] = np.asarray(hit)+np.asarray(normal)*(.0005+thickness)
        inverse = obj.matrix_world.inverted()
        for vertex, point in zip(obj.data.vertices, points):
            vertex.co = inverse @ Vector(point)
        recalc(obj)
        report[name] = dict(base_clearance_m=.0005, maximum_before_distance_m=maximum,
                            method='paired sewn facing columns follow actual reduced cloth normals')
    return report


def ribbon_vertices(obj):
    return {i for polygon in obj.data.polygons
            if obj.data.materials[polygon.material_index].name == 'RibbonFabric' for i in polygon.vertices}


def seat_medal(body, binding):
    from attachment_metrics import base_indices
    from common import surface_tree
    import json

    obj = bpy.data.objects['Medal']
    original = np.asarray(binding['original'])
    indices = base_indices(original, json.loads(obj['attachment'])['base_blender_m'])
    points = np.array([obj.matrix_world @ v.co for v in obj.data.vertices])
    tree = surface_tree(body)
    support = np.concatenate([triangles(body), triangles(bpy.data.objects['RibbonBar'])])
    from mathutils.bvhtree import BVHTree
    surface = BVHTree.FromPolygons(support.reshape(-1, 3).tolist(),
                                   np.arange(support.size//3).reshape(-1, 3).tolist(), all_triangles=True)
    ribbon = ribbon_vertices(obj)
    obj.data.calc_loop_triangles()
    reports = []
    for ids in binding['groups']:
        base = np.intersect1d(indices, ids)
        if set(ids) <= ribbon:
            hits = [surface.find_nearest(Vector(points[i])) for i in base]
            target = np.array([hit[0]+hit[1]*.0005 for hit in hits])
            pairs = np.linalg.norm(original[ids, None]-original[base], axis=2).argmin(1)
            points[ids] += (target-points[base])[pairs]
            method = 'flexible ribbon columns on reduced wool and ribbon bar'
        else:
            hits = [tree.find_nearest(Vector(points[i])) for i in base]
            target = np.array([hit[0][:] for hit in hits])
            src = original[base]
            u, _, vt = np.linalg.svd((src-src.mean(0)).T@(target-target.mean(0)))
            if np.linalg.det(u@vt) < 0:
                u[:, -1] *= -1
            rotation = u@vt
            points[ids] = (original[ids]-src.mean(0))@rotation+target.mean(0)
            normal = np.array([0., -1., 0.])@rotation
            group = set(ids)
            faces = np.array([t.vertices[:] for t in obj.data.loop_triangles if set(t.vertices) <= group])
            gap = continuous_gap(points[faces], support, normal)
            points[ids] += normal*(.00025-gap)
            method = 'rigid metal base on continuous reduced support'
        distances = [tree.find_nearest(Vector(points[i]))[3] for i in base]
        reports.append(dict(minimum_base_distance_m=min(distances), maximum_base_distance_m=max(distances),
                            within_2mm=max(distances) <= .002, method=method))
    inverse = obj.matrix_world.inverted()
    for vertex, point in zip(obj.data.vertices, points):
        vertex.co = inverse @ Vector(point)
    recalc(obj)
    return reports


def press_medal_support(body, binding):
    """Keep the shared backing under medal bases and ribbon bar locally planar."""
    from attachment_metrics import base_indices, rigid_normal
    import json

    obj = bpy.data.objects['Medal']
    original = np.asarray(binding['original'])
    bases = base_indices(original, json.loads(obj['attachment'])['base_blender_m'])
    points = np.array([obj.matrix_world @ v.co for v in obj.data.vertices])
    vertices = np.array([body.matrix_world @ v.co for v in body.data.vertices])
    initial = vertices.copy()
    ribbon = ribbon_vertices(obj)
    for ids in binding['groups']:
        base = np.intersect1d(bases, ids)
        local = np.flatnonzero(np.isin(ids, base))
        normal = rigid_normal(original[ids], points[ids], local, np.array([0., -1., 0.]))
        transverse = np.linalg.svd(np.array([normal]))[2][1:]
        backing = points[base]
        if set(ids) <= ribbon:
            bar = bpy.data.objects['RibbonBar']
            backing = np.vstack([backing, [bar.matrix_world @ v.co for v in bar.data.vertices]])
        footprint = np.einsum('ij,kj->ik', backing, transverse)
        xy = np.einsum('ij,kj->ik', vertices, transverse)
        outside = np.maximum(footprint.min(0)-xy, xy-footprint.max(0)).clip(0).max(1)
        weight = np.clip(1-outside/.010, 0, 1)
        level = float(np.mean(np.einsum('ij,j->i', points[base], normal)))
        depth = np.einsum('ij,j->i', vertices, normal)-level
        weight[np.abs(depth) > .012] = 0.
        delta = np.clip(-.0008-depth, -.0015, .0015)*weight
        vertices += normal*delta[:, None]
    inverse = body.matrix_world.inverted()
    for vertex, point in zip(body.data.vertices, vertices):
        vertex.co = inverse @ Vector(point)
    recalc(body)
    return dict(maximum_motion_m=float(np.linalg.norm(vertices-initial, axis=1).max()),
                falloff_m=.010, support_gap_m=.0008)


def fit_boards(body, bindings):
    """Interfacing keeps a shoulder board coherent across a failed wool seam."""
    report = {}
    for name in ('ShoulderBoard_L', 'ShoulderBoard_R'):
        binding = bindings[name]
        original = np.asarray(binding['original'])
        vertices = np.array([body.matrix_world @ v.co for v in body.data.vertices])
        patches = np.array([vertices[list(entry['triangle'])] for entry in binding['entries']])
        destination = np.array([np.asarray(entry['weights'])@triangle
                                for entry, triangle in zip(binding['entries'], patches)])
        normal = np.cross(patches[:, 1]-patches[:, 0], patches[:, 2]-patches[:, 0])
        normal = (normal/np.linalg.norm(normal, axis=1)[:, None]).mean(0)
        normal /= np.linalg.norm(normal)
        a = original.mean(0)
        axes = np.linalg.svd(original-a)[2]
        source_long = axes[0]*np.sign(axes[0, 0])
        source_normal = axes[2]*np.sign(axes[2, 2])
        order = np.argsort((original-a)@source_long)
        span = destination[order[-20:]].mean(0)-destination[order[:20]].mean(0)
        span -= normal*(span@normal)
        span /= np.linalg.norm(span)
        source_frame = np.array([source_long, np.cross(source_normal, source_long), source_normal])
        target_frame = np.array([span, np.cross(normal, span), normal])
        rotation = source_frame.T@target_frame
        points = ((original-a)@rotation+destination.mean(0)+normal*.0005+[0., 0., -.02]
                  if name == 'ShoulderBoard_L' else original+[.01, 0., 0.])
        obj = bpy.data.objects[name]
        inverse = obj.matrix_world.inverted()
        for vertex, point in zip(obj.data.vertices, points):
            vertex.co = inverse @ Vector(point)
        recalc(obj)
        binding['rigid'] = True
        report[name] = dict(method=('released board follows front ply, with 20 mm downward slip' if name == 'ShoulderBoard_L'
                                    else 'retained source frame, with 10 mm inward seating'),
                            original_curvature_preserved=True)
    return report


def seat_board_columns(body, bindings):
    """Bend board facings onto wool without changing their transverse ordering."""
    from common import surface_tree
    tree = surface_tree(body)
    report = {}
    for name in ('ShoulderBoard_L', 'ShoulderBoard_R'):
        obj = bpy.data.objects[name]
        original = np.asarray(bindings[name]['original'])
        points = np.array([obj.matrix_world @ v.co for v in obj.data.vertices])
        count = len(points)//2
        if len(points) != count*2:
            raise ValueError(f'{name}: expected paired board facings')
        u, _, vt = np.linalg.svd((original-original.mean(0)).T@(points-points.mean(0)))
        if np.linalg.det(u@vt) < 0:
            u[:, -1] *= -1
        normal = np.array([0., 0., 1.])@(u@vt)
        before = points.copy()
        if name == 'ShoulderBoard_R':
            radius = .0095
            for i in range(count):
                points[[i, i+count], 1] += radius*np.sin(points[i, 1]/radius)-points[i, 1]
        for i in range(count):
            hit, _, _, _ = tree.ray_cast(Vector(points[i]+normal*.15), Vector(-normal), .3)
            if hit is None:
                raise ValueError(f'{name}: board column {i} at {points[i]} has no wool backing')
            displacement = normal*(np.dot(np.asarray(hit)-points[i], normal)+.0005)
            points[[i, i+count]] += displacement
        inverse = obj.matrix_world.inverted()
        for vertex, point in zip(obj.data.vertices, points):
            vertex.co = inverse @ Vector(point)
        recalc(obj)
        report[name] = dict(method='paired normal-ray columns; fixed transverse parameterization',
                            maximum_motion_m=float(np.linalg.norm(points-before, axis=1).max()),
                            base_clearance_m=.0005)
    return report
