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
    for name in ('ShoulderBoard_L', 'ShoulderBoard_R', 'Placket'):
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
            sign = float(np.dot(points[i+count]-points[i], normal))
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
