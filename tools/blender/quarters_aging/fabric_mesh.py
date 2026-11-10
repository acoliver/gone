"""Baked cloth surfaces with explicit tear rims and a thin, closed section."""
import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector

from common import activate, apply, recalc


def material(name, color):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1)
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Roughness'].default_value = .95
    return mat


def replace(obj, vertices, faces, mat, uv=None):
    data = bpy.data.meshes.new(obj.name + '_surface')
    inverse = obj.matrix_world.inverted()
    data.from_pydata([inverse @ Vector(p) for p in vertices], [], faces)
    data.materials.append(mat)
    obj.data = data
    obj.modifiers.clear()
    obj['aged_export'] = True
    recalc(obj)
    layer = data.uv_layers.new(name='AgedPattern')
    for loop in data.loops:
        p = vertices[loop.vertex_index]
        layer.data[loop.index].uv = uv[loop.vertex_index] if uv is not None else (p[0], p[2])
    for face in data.polygons:
        face.use_smooth = True
    return obj


def new_object(name, vertices, faces, mat):
    obj = bpy.data.objects.new(name, bpy.data.meshes.new(name))
    bpy.context.collection.objects.link(obj)
    return replace(obj, vertices, faces, mat)


def thicken(obj, thickness, inside='ClothInside', rim='FrayedSection'):
    color = obj.data.materials[0].diffuse_color[:3]
    obj.data.materials.append(material(inside, tuple(c * .75 for c in color)))
    obj.data.materials.append(material(rim, tuple(c * .85 for c in color)))
    if obj.data.attributes.get('SectionNormal'):
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.dissolve_degenerate(bm, dist=.00001, edges=list(bm.edges))
        bm.to_mesh(obj.data)
        bm.free()
        mesh = obj.data
        limits = np.full(len(mesh.vertices), thickness)
        for edge in mesh.edges:
            a, b = edge.vertices
            limit = (mesh.vertices[a].co - mesh.vertices[b].co).length * .10
            limits[a] = min(limits[a], limit)
            limits[b] = min(limits[b], limit)
        positions = [v.co.copy() for v in mesh.vertices]
        normals = mesh.attributes['SectionNormal'].data
        flags = mesh.attributes['ThinFibre'].data
        n = len(positions)
        positions += [v.co - Vector(normals[v.index].vector).normalized() * min(limits[v.index], thickness * (.02 if flags[v.index].value else 1)) for v in mesh.vertices]
        faces = [tuple(p.vertices) for p in mesh.polygons]
        uv = [[tuple(mesh.uv_layers.active.data[i].uv) for i in p.loop_indices] for p in mesh.polygons]
        uses = {}
        for face, pattern in zip(faces, uv):
            for k, (a, b) in enumerate(zip(face, face[1:] + face[:1])):
                uses.setdefault(tuple(sorted((a, b))), []).append((a, b, pattern[k], pattern[(k + 1) % len(face)]))
        backside = [tuple(n + i for i in reversed(face)) for face in faces]
        backside_uv = [list(reversed(pattern)) for pattern in uv]
        rims, rim_uv = [], []
        for edges in uses.values():
            if len(edges) == 1:
                a, b, u, v = edges[0]
                rims.extend([(b, a, n + a), (b, n + a, n + b)])
                rim_uv.extend([[v, u, u], [v, u, v]])
        data = bpy.data.meshes.new(obj.name + '_section')
        data.from_pydata(positions, [], faces + backside + rims)
        for mat in mesh.materials:
            data.materials.append(mat)
        layer = data.uv_layers.new(name='AgedPattern')
        for p, pattern in zip(data.polygons, uv + backside_uv + rim_uv):
            p.material_index = 0 if p.index < len(faces) else (1 if p.index < len(faces) * 2 else 2)
            p.use_smooth = True
            for i, value in zip(p.loop_indices, pattern):
                layer.data[i].uv = value
        obj.data = data
        recalc(obj)
        from section_contacts import impossible_fibres
        bad = impossible_fibres(obj, mesh)
        if bad:
            bm = bmesh.new()
            bm.from_mesh(mesh)
            labels = bm.verts.layers.int['FrayID']
            tips = bm.verts.layers.int['FrayTip']
            remove = [v for v in bm.verts if v[tips] and v[labels] in bad]
            if remove:
                obj['pruned_impossible_fibres'] = obj.get('pruned_impossible_fibres', 0) + len(remove)
                bmesh.ops.delete(bm, geom=remove, context='VERTS')
                bm.to_mesh(mesh)
                obj.data = mesh
                # Rebuild the section without the physically intersecting thread tips.
                obj.data.materials.clear()
                obj.data.materials.append(data.materials[0])
                thicken(obj, thickness, inside, rim)
            bm.free()
        return
    mod = obj.modifiers.new('Baked thin fabric section', 'SOLIDIFY')
    mod.thickness = thickness
    mod.offset = -1
    mod.use_even_offset = False
    mod.material_offset = 1
    mod.material_offset_rim = 2
    if obj.data.attributes.get('ThinFibre'):
        group = obj.vertex_groups.new(name='Fibre section')
        for vertex, flag in zip(obj.data.vertices, obj.data.attributes['ThinFibre'].data):
            group.add([vertex.index], 0 if flag.value else 1, 'REPLACE')
        mod.vertex_group = group.name
        mod.thickness_vertex_group = .02
    apply(obj, mod)
    recalc(obj)


def boundary_loops(mesh):
    counts = {}
    for face in mesh.polygons:
        ids = list(face.vertices)
        for a, b in zip(ids, ids[1:] + ids[:1]):
            edge = tuple(sorted((a, b)))
            counts[edge] = counts.get(edge, 0) + 1
    neighbors = {}
    for (a, b), count in counts.items():
        if count == 1:
            neighbors.setdefault(a, []).append(b)
            neighbors.setdefault(b, []).append(a)
    if any(len(n) != 2 for n in neighbors.values()):
        raise ValueError('Tear boundaries must be loops, without point-only bridges')
    remaining, loops = set(neighbors), []
    while remaining:
        start = min(remaining)
        loop, previous, current = [], None, start
        while True:
            loop.append(current)
            remaining.remove(current)
            following = next(v for v in neighbors[current] if v != previous)
            if following == start:
                break
            previous, current = current, following
        loops.append(loop)
    return loops


def fray(obj, seed, probability=.55, length=(.002, .009), max_edge=.04, region=lambda p: True):
    """Extend narrow bases, rather than overlaying intersecting fibre cards."""
    rng = np.random.default_rng(seed)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bm.normal_update()
    flags = bm.verts.layers.int.new('ThinFibre')
    labels = bm.verts.layers.int.new('FrayID')
    tips = bm.verts.layers.int.new('FrayTip')
    section = bm.verts.layers.float_vector.new('SectionNormal')
    for vertex in bm.verts:
        vertex[section] = vertex.normal.copy()
    count = 0
    for edge in list(bm.edges):
        if not edge.is_boundary or edge.calc_length() > max_edge or rng.random() > probability:
            continue
        a, b = edge.verts
        centre = (a.co + b.co) / 2
        if not region(obj.matrix_world @ centre):
            continue
        source_face = edge.link_faces[0]
        apex = next(v for v in source_face.verts if v not in {a,b})
        outward = (centre - source_face.calc_center_median()).normalized()
        tip = centre + outward * rng.uniform(*length)
        _, left = bmesh.utils.edge_split(edge, a, .46)
        narrow, right = bmesh.utils.edge_split(edge, left, .08)
        loop = narrow.link_loops[0]
        vertex = bm.verts.new(tip)
        vertex[section] = (left[section] + right[section]).normalized()
        for fibre in [left, right, vertex]:
            fibre[flags] = 1
            fibre[labels] = count + 1
        vertex[tips] = 1
        pattern = bm.loops.layers.uv.active
        coordinates = {corner.vert: corner[pattern].uv.copy() for corner in source_face.loops}
        fibre_corners = (loop.link_loop_next.vert, loop.vert, vertex)
        corners = list(source_face.verts)
        start = corners.index(apex)
        boundary = corners[start+1:] + corners[:start]
        material_index = source_face.material_index
        bm.faces.remove(source_face)
        # Fan from the original opposite corner. Ear clipping can emit slivers
        # along the three collinear points introduced by a split fray base.
        for first, second in zip(boundary,boundary[1:]):
            face = bm.faces.new((apex,first,second))
            face.material_index = material_index
            for corner in face.loops:
                corner[pattern].uv = coordinates[corner.vert]
        face = bm.faces.new(fibre_corners)
        face.material_index = material_index
        tip_uv = (coordinates[left] + coordinates[right]) / 2
        for corner in face.loops:
            corner[pattern].uv = coordinates.get(corner.vert, tip_uv)
        count += 1
    bmesh.ops.triangulate(bm, faces=list(bm.faces), quad_method='BEAUTY', ngon_method='EAR_CLIP')
    bm.to_mesh(obj.data)
    bm.free()
    recalc(obj)
    return count


def join(target, others):
    activate(target)
    for obj in others:
        obj.select_set(True)
    bpy.ops.object.join()
    target.data.name = target.name
    return target


def remove_surface_frays(obj):
    """Recover the unchanged simulated surface before rebuilding thread bases."""
    bm=bmesh.new();bm.from_mesh(obj.data)
    labels=bm.verts.layers.int['FrayID']
    tips=bm.verts.layers.int['FrayTip']
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if v[tips]],context='VERTS')
    bases=[v for v in bm.verts if v[labels]]
    bmesh.ops.dissolve_verts(bm,verts=bases,use_face_split=False,use_boundary_tear=False)
    for name in ['ThinFibre','FrayID','FrayTip']:
        bm.verts.layers.int.remove(bm.verts.layers.int[name])
    bm.verts.layers.float_vector.remove(bm.verts.layers.float_vector['SectionNormal'])
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    bm.to_mesh(obj.data);bm.free();recalc(obj)



def grid(nx, ny, point, cut=lambda i, j: False):
    vertices = [point(i / nx, j / ny, i, j) for j in range(ny + 1) for i in range(nx + 1)]
    faces = []
    for j in range(ny):
        for i in range(nx):
            if not cut(i, j):
                a = j * (nx + 1) + i
                faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    return vertices, faces


def shell(nx, ny, point, bottom, cut=lambda i, j: False):
    """A gridded upper face, slack side band and an underside, all sharing edges."""
    vertices, faces = grid(nx, ny, point, cut)
    ring = list(range(nx + 1))
    ring += [j * (nx + 1) + nx for j in range(1, ny + 1)]
    ring += [ny * (nx + 1) + i for i in range(nx - 1, -1, -1)]
    ring += [j * (nx + 1) for j in range(ny - 1, 0, -1)]
    for fraction in [.45, 1.0]:
        following = []
        for idx in ring:
            p = np.asarray(vertices[idx])
            q = np.asarray(bottom(p, fraction))
            following.append(len(vertices))
            vertices.append(q.tolist())
        faces += [(a, b, following[(k + 1) % len(ring)], following[k])
                  for k, (a, b) in enumerate(zip(ring, ring[1:] + ring[:1]))]
        ring = following
    centre = len(vertices)
    vertices.append(np.mean([vertices[i] for i in ring], axis=0).tolist())
    faces += [(ring[(k + 1) % len(ring)], ring[k], centre) for k in range(len(ring))]
    return vertices, faces


def volume(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    result = abs(bm.calc_volume(signed=True))
    bm.free()
    return result
