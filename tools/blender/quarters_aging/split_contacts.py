"""Exclude complete incident triangles at a coincident zero-area cloth split."""
import bmesh


def exclude_split_contacts(obj):
    lip = obj.vertex_groups.get('Lip shrink')
    if lip is None:
        return {'excluded_vertices': 0, 'incident_faces': 0}
    group = obj.vertex_groups.get('Self collision exclusion')
    if group is None:
        group = obj.vertex_groups.new(name='Self collision exclusion')
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    deform = bm.verts.layers.deform.active
    lips = {v for v in bm.verts if v[deform].get(lip.index, 0.) > 0}
    faces = {face for vertex in lips for face in vertex.link_faces}
    indices = {vertex.index for face in faces for vertex in face.verts}
    bm.free()
    if indices:
        group.add(sorted(indices), 1., 'REPLACE')
    return {'excluded_vertices': len(indices), 'incident_faces': len(faces),
            'reason': 'Blender excludes a triangle only when all three vertices belong to the group.'}
