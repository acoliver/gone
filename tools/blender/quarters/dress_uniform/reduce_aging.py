"""Simplify redundant strip boundary samples before protected reduction."""
import math

import bmesh
import bpy
import numpy as np

from bake_down import boundary_hausdorff, decimate


def retained_samples(points, tolerance=.0005):
    if len(points) <= 2:
        return {0, len(points)-1}
    delta = points[-1]-points[0]
    length2 = float(delta@delta)
    t = np.clip((points-points[0])@delta/length2, 0, 1) if length2 else np.zeros(len(points))
    distances = np.linalg.norm(points-points[0]-t[:, None]*delta, axis=1)
    index = int(distances.argmax())
    if distances[index] <= tolerance:
        return {0, len(points)-1}
    left = retained_samples(points[:index+1], tolerance)
    right = retained_samples(points[index:], tolerance)
    return left | {index+i for i in right}


def simplify_boundary(bm):
    remaining = {e for e in bm.edges if e.is_boundary}
    remove = set()
    while remaining:
        first = min(remaining, key=lambda e: min(v.index for v in e.verts))
        start = first.verts[0]
        chain = [start]
        current = start
        while True:
            edge = next((e for e in current.link_edges if e in remaining), None)
            if edge is None:
                break
            remaining.remove(edge)
            current = edge.other_vert(current)
            chain.append(current)
            if current == start:
                break
        points = np.array([v.co[:] for v in chain])
        keep = {chain[i] for i in retained_samples(points)}
        remove.update(set(chain)-keep)
    bmesh.ops.dissolve_verts(bm, verts=list(remove), use_face_split=False, use_boundary_tear=False)


def reduce_game(dense, target):
    if dense.name == 'TunicBody':
        low, report = decimate(dense, target)
        bm = bmesh.new()
        bm.from_mesh(low.data)
        interior = [v for v in bm.verts if not v.is_boundary]
        for _ in range(4):
            bmesh.ops.smooth_vert(bm, verts=interior, factor=.3,
                                  use_axis_x=True, use_axis_y=True, use_axis_z=True)
        bm.to_mesh(low.data)
        bm.free()
        report['interior_relaxation'] = {'passes': 4, 'factor': .3, 'boundary_fixed': True}
        report['boundary_hausdorff_upper_m'] = boundary_hausdorff(dense, low)
        report['pass'] = report['triangles'] <= target and report['boundary_hausdorff_upper_m'] <= .0015
        return low, report
    working = dense.copy()
    working.data = dense.data.copy()
    bpy.context.collection.objects.link(working)
    working.shape_key_clear()
    working['aged_export'] = False
    bm = bmesh.new()
    bm.from_mesh(working.data)
    bm.verts.index_update()
    # The narrow allowance is mostly within its 6 mm Keep band. First reduce
    # boundary sampling to a measured 0.5 mm chord error, rather than asking
    # Decimate to destroy a protected lip or using an angle-only boundary test.
    simplify_boundary(bm)
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(10),
                             use_dissolve_boundaries=False,
                             verts=[], edges=[e for e in bm.edges if not e.is_boundary])
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bm.to_mesh(working.data)
    bm.free()
    low, report = decimate(working, target)
    report['boundary_hausdorff_upper_m'] = boundary_hausdorff(dense, low)
    report['pass'] = report['triangles'] <= target and report['boundary_hausdorff_upper_m'] <= .0015
    bpy.data.objects.remove(working, do_unlink=True)
    return low, report
