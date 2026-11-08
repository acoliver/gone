"""Seeded seam/stress cuts made before gravity settling."""
import math

import bmesh
import numpy as np


def fractal(t, seed, amplitude=.006):
    return amplitude * sum(math.sin(t * (2 ** k) * 57 + seed * (k + 1) * .73) / 2 ** k for k in range(4)) / 1.875


def release_armhole(vertices, faces, start, end, fraction=.60):
    body = {i for f in faces[:1680] for i in f}
    sleeve = {i for f in faces[start:end] for i in f}
    cap = body & sleeve
    neighbors = {i: set() for i in cap}
    for face in faces[start:end]:
        for a, b in zip(face, face[1:] + face[:1]):
            if a in cap and b in cap:
                neighbors[a].add(b)
                neighbors[b].add(a)
    loop, previous, current = [], None, min(cap)
    while True:
        loop.append(current)
        nxt = next(i for i in sorted(neighbors[current]) if i != previous)
        if nxt == loop[0]:
            break
        previous, current = current, nxt
    # Retain the lower rear arc, so the upper cap and forward seam can fall.
    centre = max(range(len(loop)), key=lambda k: vertices[loop[k]][2]-3*vertices[loop[k]][1])
    count = round(fraction * len(loop))
    released = {loop[(centre - count // 2 + k) % len(loop)] for k in range(count)}
    copies = {}
    for index in released:
        copies[index] = len(vertices)
        vertices.append(vertices[index].copy()+np.array([.0025,0,0]))
    for index in range(start, end):
        faces[index] = tuple(copies.get(i, i) for i in faces[index])
    total = opened = 0.
    for a, b in zip(loop, loop[1:] + loop[:1]):
        length = np.linalg.norm(vertices[a] - vertices[b])
        total += length
        if a in released or b in released:
            opened += length
    return {'released_fraction': float(opened / total), 'released_vertices': len(released), 'cap_vertices': len(loop)}


def cut_faces(obj, predicate, seed, refine=True, noise_region=lambda p: True, fan_clearance=.002):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    removed = [f for f in bm.faces if predicate(obj.matrix_world @ f.calc_center_median())]
    area = sum(f.calc_area() for f in removed)
    bmesh.ops.delete(bm, geom=removed, context='FACES')
    # A coarse face mask can leave two cloth regions touching at just one vertex.
    # Separate those fans before simulation; such a point is not a surviving stitch.
    uv=bm.loops.layers.uv.active
    bm.faces.index_update()
    next_face_index=max((face.index for face in bm.faces),default=-1)+1
    for vertex in list(bm.verts):
        remaining=set(vertex.link_faces);fans=[]
        while remaining:
            first=min(remaining,key=lambda face:face.index);remaining.remove(first)
            frontier={first};fan=set(frontier)
            while frontier:
                following={f for face in frontier for edge in face.edges if vertex in edge.verts for f in edge.link_faces}&remaining
                remaining-=following;fan|=following;frontier=following
            fans.append(fan)
        original=vertex.co.copy()
        if len(fans)>1:
            centre=sum((f.calc_center_median() for f in fans[0]),original*0)/len(fans[0])
            vertex.co=original+(centre-original).normalized()*fan_clearance
        for fan in fans[1:]:
            centre=sum((f.calc_center_median() for f in fan),original*0)/len(fan)
            duplicate=bm.verts.new(original+(centre-original).normalized()*fan_clearance)
            for face in sorted(fan,key=lambda face:face.index):
                corners=[duplicate if v==vertex else v for v in face.verts]
                patterns=[loop[uv].uv.copy() for loop in face.loops]
                index=face.material_index;bm.faces.remove(face)
                replacement=bm.faces.new(corners);replacement.material_index=index
                replacement.index=next_face_index;next_face_index+=1
                for loop,pattern in zip(replacement.loops,patterns):loop[uv].uv=pattern
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context='EDGES')
    if refine:
        edges = [e for e in bm.edges if e.is_boundary and e.calc_length() > .012]
        bmesh.ops.subdivide_edges(bm, edges=edges, cuts=2, use_grid_fill=False)
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
        bm.normal_update()
        bm.verts.index_update()
        for v in sorted({v for e in bm.edges if e.is_boundary for v in e.verts},key=lambda vertex:vertex.index):
            edges = [e for e in v.link_edges if e.is_boundary]
            p = obj.matrix_world @ v.co
            if len(edges) != 2 or not noise_region(p):
                continue
            tangent = edges[0].other_vert(v).co - edges[1].other_vert(v).co
            outward = v.normal.cross(tangent).normalized()
            offset = fractal(p.x + .47 * p.y + .33 * p.z, seed)
            limit = min(e.calc_length() for e in edges) * .25
            delta=outward*float(np.clip(offset,-limit,limit))
            original=v.co.copy()
            normals={f:(f.verts[1].co-f.verts[0].co).cross(f.verts[2].co-f.verts[0].co) for f in v.link_faces}
            for fraction in [1,.5,.25,.125,0]:
                v.co=original+delta*fraction
                if all((f.verts[1].co-f.verts[0].co).cross(f.verts[2].co-f.verts[0].co).dot(n)>.3*n.length_squared for f,n in normals.items()):
                    break
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return {'removed_faces': len(removed), 'removed_area_m2': area, 'boundary_noise_amplitude_m': .006 if refine else 0, 'octaves': 4 if refine else 0, 'point_fan_clearance_m': fan_clearance}
