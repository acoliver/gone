"""Reseat transported wool cards against the changed cloth and existing fittings."""
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from pilot_finish import card_groups
from reduced_clearance import crossing_pairs


def shorten_shoulder_cards(names, maximum=.0012):
    report = {}
    for name in names:
        obj = bpy.data.objects[name]
        lengths = []
        for ids in card_groups(obj):
            uv = {obj.data.loops[i].vertex_index: obj.data.uv_layers[0].data[i].uv.y
                  for face in obj.data.polygons for i in face.loop_indices
                  if obj.data.loops[i].vertex_index in ids}
            roots = [i for i in ids if abs(uv[i]-min(uv.values())) < 1e-7]
            centre = sum((obj.data.vertices[i].co for i in roots), Vector())/len(roots)
            if centre.x < .14 or centre.z < -.35:
                continue
            tangent = max((obj.data.vertices[a].co-obj.data.vertices[b].co for a in roots for b in roots),
                          key=lambda value: value.length).normalized()
            offsets = {i: obj.data.vertices[i].co-centre for i in ids}
            extent = max((offset-tangent*offset.dot(tangent)).length for offset in offsets.values())
            scale = min(1., maximum/extent)
            for index, offset in offsets.items():
                if index not in roots:
                    along = tangent*offset.dot(tangent)
                    obj.data.vertices[index].co = centre+along+(offset-along)*scale
            lengths.append(extent)
        obj.data.update()
        report[name] = dict(cards=len(lengths), previous_maximum_m=max(lengths),
                            maximum_projection_m=maximum, root_vertices_unchanged=True)
    return report


def seat_cards(sheet, names):
    tree = BVHTree.FromPolygons(sheet['vertices'].tolist(), sheet['faces'].tolist(), all_triangles=True)
    report = {}
    for name in names:
        obj = bpy.data.objects[name]
        groups = card_groups(obj)
        owner = {vertex: group for group, ids in enumerate(groups) for vertex in ids}
        blockers = [other for other in bpy.context.scene.objects
                    if other != obj and other.type == 'MESH' and other.get('aged_export')]
        def contacts():
            obj.data.calc_loop_triangles()
            faces = [triangle.vertices[:] for triangle in obj.data.loop_triangles]
            bad = {owner[v] for i, j in crossing_pairs(obj) for face in [i, j] for v in faces[face]}
            for other in blockers:
                bad |= {owner[v] for i, _ in crossing_pairs(obj, other) for v in faces[i]}
            return bad
        initial = contacts()
        moved = {}
        for group in sorted(initial):
            if group not in contacts():
                continue
            ids = groups[group]
            before = np.array([obj.data.vertices[i].co[:] for i in ids])
            centre = sum((obj.matrix_world @ obj.data.vertices[i].co for i in ids), Vector())/len(ids)
            _, normal, _, _ = tree.find_nearest(centre)
            inverse = obj.matrix_world.to_3x3().inverted()
            direction = inverse @ normal
            uv = {obj.data.loops[i].vertex_index: obj.data.uv_layers[0].data[i].uv.y
                  for face in obj.data.polygons for i in face.loop_indices
                  if obj.data.loops[i].vertex_index in ids}
            roots = [obj.data.vertices[i].co.copy() for i in ids if abs(uv[i]-min(uv.values())) < 1e-7]
            tangent = max((b-a for a in roots for b in roots), key=lambda v: v.length).normalized()
            across = direction.cross(tangent).normalized()
            shifts = [axis*distance for axis in [direction, tangent, across]
                      for distance in [.0005, -.0005, .001, -.001, .002, -.002, .003, -.003]]
            for shift in shifts:
                for index, point in zip(ids, before):
                    obj.data.vertices[index].co = Vector(point)+shift
                obj.data.update()
                if group not in contacts():
                    moved[str(group)] = list(shift)
                    break
            else:
                raise ValueError(f'{name} card {group} cannot seat within the original 3 mm placement range')
        remaining = contacts()
        if remaining:
            raise ValueError(f'{name} fringe contacts remain at cards {sorted(remaining)}')
        report[name] = dict(initial_intersecting_cards=len(initial), offsets_m=moved,
                           remaining_intersecting_cards=0, card_shapes_and_root_widths_unchanged=True)
    return report


def measure_root_coverage(body, names):
    import bmesh
    from fringe_boundary import boundary_chains, measured_coverage
    proxy = body.copy()
    proxy.data = body.data.copy()
    bpy.context.collection.objects.link(proxy)
    mesh = proxy.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.delete(bm, geom=[face for face in bm.faces if face.material_index != 0], context='FACES')
    bm.to_mesh(mesh)
    bm.free()
    result = {}
    roles = {'Seamallowance': 'Seam allowance', 'Longwoolfringe': 'Long wool fringe'}
    for name in names:
        obj = bpy.data.objects[name]
        pairs = []
        for ids in card_groups(obj):
            uv = {obj.data.loops[i].vertex_index: obj.data.uv_layers[0].data[i].uv.y
                  for face in obj.data.polygons for i in face.loop_indices
                  if obj.data.loops[i].vertex_index in ids}
            roots = [i for i in ids if abs(uv[i]-min(uv.values())) < 1e-7]
            pairs.append(max(((a, b) for a in roots for b in roots),
                             key=lambda pair: (obj.data.vertices[pair[0]].co-obj.data.vertices[pair[1]].co).length))
        result[roles[name]] = measured_coverage(obj, boundary_chains(proxy, roles[name]), pairs)
    bpy.data.objects.remove(proxy, do_unlink=True)
    bpy.data.meshes.remove(mesh)
    return result
