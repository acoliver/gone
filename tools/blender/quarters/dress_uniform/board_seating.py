"""Seat paired board bases without lifting the whole facing off a wool crease."""
import json

import bmesh
import bpy
import numpy as np
from mathutils import Vector

from attachment_metrics import base_indices
from common import recalc, surface_tree
from reduced_clearance import crossing_pairs, push_out


def refine_board(obj, binding):
    original = np.asarray(binding['original'])
    count = len(original)//2
    points = np.array([obj.matrix_world @ v.co for v in obj.data.vertices])
    bm = bmesh.new()
    top = bm.verts.layers.float_vector.new('Paired top')
    source_top = bm.verts.layers.float_vector.new('Source top')
    source_base = bm.verts.layers.float_vector.new('Source base')
    vertices = [bm.verts.new(Vector(p)) for p in points[count:]]
    for i, vertex in enumerate(vertices):
        vertex[top], vertex[source_top], vertex[source_base] = points[i], original[i], original[i+count]
    obj.data.calc_loop_triangles()
    for face in obj.data.loop_triangles:
        if min(face.vertices) >= count:
            bm.faces.new([vertices[i-count] for i in face.vertices])
    bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=1, use_grid_fill=True)
    bm.verts.index_update()
    bottom = np.array([v.co[:] for v in bm.verts])
    upper = np.array([v[top][:] for v in bm.verts])
    source = np.vstack([[v[source_top][:] for v in bm.verts], [v[source_base][:] for v in bm.verts]])
    faces = [tuple(v.index for v in face.verts) for face in bm.faces]
    boundary = [tuple(v.index for v in edge.verts) for edge in bm.edges if edge.is_boundary]
    n = len(bottom)
    closed = [tuple(i+n for i in face) for face in faces]+[tuple(reversed(face)) for face in faces]
    closed += [face for a, b in boundary for face in [(a, b, b+n), (a, b+n, a+n)]]
    bm.free()
    data = bpy.data.meshes.new(obj.name+'ResolvedFacings')
    data.from_pydata(np.vstack([upper, bottom]), [], closed)
    for mat in obj.data.materials:
        data.materials.append(mat)
    obj.data = data
    obj.matrix_world.identity()
    for face in data.polygons:
        face.use_smooth = True
    binding['original'] = source.tolist()
    binding['groups'] = [list(range(2*n))]
    attachment = json.loads(obj['attachment'])
    attachment['base_blender_m'] = source[n:].tolist()
    obj['attachment'] = json.dumps(attachment)
    recalc(obj)


def seat_boards(body, bindings):
    tree = surface_tree(body)
    report = {}
    for name in ['ShoulderBoard_L', 'ShoulderBoard_R']:
        obj = bpy.data.objects[name]
        refine_board(obj, bindings[name])
        push_out(obj, body, clearance=.00015, maximum=.0005, paired=True)
        original = np.asarray(bindings[name]['original'])
        count = len(original)//2
        base = base_indices(original, json.loads(obj['attachment'])['base_blender_m'])
        if not np.array_equal(base, np.arange(count, count*2)):
            raise ValueError(f'{name}: expected paired source facings with lower bases in second block')
        if crossing_pairs(obj, body) or crossing_pairs(obj):
            raise ValueError(f'{name}: seating requires an initially crossing-free board')
        before = max(tree.find_nearest(obj.matrix_world @ obj.data.vertices[i].co)[3] for i in base)
        initial = np.array([obj.matrix_world @ v.co for v in obj.data.vertices])
        column_offsets = initial[count:]-initial[:count]
        accepted = 0
        from board_contacts import BoardContacts
        contacts = BoardContacts(obj, body)
        inverse = obj.matrix_world.inverted()
        # Preserve each facing column; minimize distance subject to zero SAT contacts.
        for iteration in range(8):
            gaps = [tree.find_nearest(obj.matrix_world @ obj.data.vertices[i].co)[3] for i in base]
            if max(gaps) < .0010:
                break
            changed = False
            for k in np.argsort(gaps)[::-1]:
                i = int(base[k])
                hit, _, _, distance = tree.find_nearest(obj.matrix_world @ obj.data.vertices[i].co)
                if distance < .0006:
                    continue
                pair = [i-count, i]
                old = [obj.matrix_world @ obj.data.vertices[j].co for j in pair]
                delta = (hit-old[1]).normalized()*(distance-.00035)
                placed = False
                offsets = [Vector((0, 0, 0))]
                if iteration >= 2:
                    offsets += [Vector(axis)*sign*.0006 for axis in [(1, 0, 0), (0, 1, 0), (0, 0, 1)]
                                for sign in [-1, 1]]
                for offset in offsets:
                    for fraction in [1., .5, .25, .125, .0625, .03125, .015625]:
                        shift = (delta+offset)*fraction
                        proposed = old[1]+shift
                        if tree.find_nearest(proposed)[3] >= distance-1e-7:
                            continue
                        contacts.points[pair] = (np.array(old)+np.array(shift)).astype(np.float32)
                        if contacts.clear(pair):
                            for j, point in zip(pair, contacts.points[pair]):
                                obj.data.vertices[j].co = inverse @ Vector(point)
                            accepted += 1
                            changed = placed = True
                            break
                    if placed:
                        break
                if not placed:
                    contacts.points[pair] = np.array(old)
            print(name, 'seating iteration', iteration, 'accepted', accepted, 'max gap', max(gaps), flush=True)
            if not changed:
                break
        recalc(obj)
        after = max(tree.find_nearest(obj.matrix_world @ obj.data.vertices[i].co)[3] for i in base)
        obj['surface_seated_board'] = True
        final = np.array([obj.matrix_world @ v.co for v in obj.data.vertices])
        offset_change = float(np.linalg.norm(final[count:]-final[:count]-column_offsets, axis=1).max())
        self_crossings, body_crossings = len(crossing_pairs(obj)), len(crossing_pairs(obj, body))
        if self_crossings or body_crossings:
            raise ValueError(f'{name}: incremental seating introduced a strict SAT crossing')
        report[name] = dict(maximum_before_gap_m=before, maximum_after_gap_m=after,
                            maximum_column_offset_change_m=offset_change,
                            accepted_column_steps=accepted,
                            self_crossings=self_crossings,
                            body_crossings=body_crossings, within_2mm=after <= .002,
                            method='paired base descent constrained by strict body and self SAT')
    return report
