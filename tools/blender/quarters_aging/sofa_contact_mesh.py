"""Resolve narrow cloth elements against Blender's 1 mm self-distance minimum."""
import bmesh
import numpy as np
from mathutils.bvhtree import BVHTree


def exclude_small_faces(obj, diameter):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=list(bm.faces), quad_method='BEAUTY')
    bm.verts.index_update()
    layer = bm.verts.layers.deform.verify()
    group = obj.vertex_groups.get('Self collision exclusion') or obj.vertex_groups.new(name='Self collision exclusion')
    count = 0
    for face in bm.faces:
        p = np.array([v.co[:] for v in face.verts])
        altitude = np.linalg.norm(np.cross(p[1]-p[0], p[2]-p[0]))/max(e.calc_length() for e in face.edges)
        if altitude < diameter:
            count += 1
            for vertex in face.verts:
                vertex[layer][group.index] = 1.
    bm.to_mesh(obj.data)
    bm.free()
    return {'base_altitude_threshold_m': diameter, 'excluded_base_faces': count}


def resolve_elements(obj, minimum_edge=.003, diameter=.002):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    reference = BVHTree.FromBMesh(bm)
    before = len(bm.verts)
    collapsed = 0
    for _ in range(12):
        occupied, selected = set(), []
        for edge in sorted(bm.edges, key=lambda e: e.calc_length()):
            if edge.calc_length() >= minimum_edge:
                break
            if any(v in occupied for v in edge.verts):
                continue
            selected.append(edge)
            occupied.update(edge.verts)
        if not selected:
            break
        collapsed += len(selected)
        bmesh.ops.collapse(bm, edges=selected, uvs=True)
        for vertex in bm.verts:
            point, _, _, _ = reference.find_nearest(vertex.co)
            vertex.co = point
    bmesh.ops.triangulate(bm, faces=list(bm.faces), quad_method='BEAUTY')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.verts.index_update()
    layer = bm.verts.layers.deform.verify()
    group = obj.vertex_groups.get('Self collision exclusion') or obj.vertex_groups.new(name='Self collision exclusion')
    unresolved, altitudes = 0, []
    for face in bm.faces:
        vertices = list(face.verts)
        p = np.array([v.co[:] for v in vertices])
        altitude = np.linalg.norm(np.cross(p[1]-p[0], p[2]-p[0]))/max(e.calc_length() for e in face.edges)
        altitudes.append(altitude)
        if altitude < diameter:
            unresolved += 1
            for vertex in vertices:
                vertex[layer][group.index] = 1.
    after = len(bm.verts)
    bm.to_mesh(obj.data)
    bm.free()
    return {'source_vertices': before, 'resolved_vertices': after, 'collapsed_edges': collapsed,
            'minimum_edge_target_m': minimum_edge, 'contact_diameter_m': diameter,
            'remaining_sub_diameter_faces_excluded': unresolved,
            'altitude_quantiles_m': np.quantile(altitudes, [0, .01, .1, .5, 1]).tolist()}
