"""Clean coarse fitted cloth and physical seam releases for sofa pass 8."""
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from densify import densify
from tear_paths import split_polyline


def mesh_quality(obj):
    obj.data.calc_loop_triangles()
    p = np.array([obj.matrix_world@v.co for v in obj.data.vertices])
    f = np.array([t.vertices[:] for t in obj.data.loop_triangles])
    t = p[f]
    edges = np.linalg.norm(t-np.roll(t, 1, axis=1), axis=2)
    altitude = np.linalg.norm(np.cross(t[:, 1]-t[:, 0], t[:, 2]-t[:, 0]), axis=1)/edges.max(1)
    return {'vertices': len(p), 'triangles': len(f),
            'altitude_quantiles_m': np.quantile(altitude, [0, .01, .5, 1]).tolist(),
            'edge_quantiles_m': np.quantile(edges, [.1, .5, .9]).tolist(),
            'self_collision_exclusions': bool(obj.vertex_groups.get('Self collision exclusion')),
            'pass': bool(altitude.min() >= .005 and np.quantile(altitude, .01) >= .006)}


def clean_mesh(obj):
    density = densify(obj, levels=1)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    reference = BVHTree.FromBMesh(bm)
    for _ in range(5):
        normals = {v: v.normal.copy() for v in bm.verts}
        positions = {}
        for v in bm.verts:
            if v.is_boundary or not v.link_edges:
                continue
            mean = sum((e.other_vert(v).co for e in v.link_edges), Vector())/len(v.link_edges)
            delta = mean-v.co
            positions[v] = v.co+.5*(delta-normals[v]*delta.dot(normals[v]))
        for v, p in positions.items():
            v.co = reference.find_nearest(p)[0]
        bm.normal_update()
    for _ in range(100):
        occupied, selected = set(), []
        for loops in bm.calc_loop_triangles():
            vertices = [loop.vert for loop in loops]
            a, b, c = [v.co for v in vertices]
            lengths = [(a-b).length, (b-c).length, (c-a).length]
            altitude = (b-a).cross(c-a).length/max(lengths)
            if altitude >= .0061:
                continue
            candidates = [bm.edges.get((v, w)) for v, w in zip(vertices, vertices[1:]+vertices[:1])]
            edge = min((e for e in candidates if e is not None), key=lambda e: e.calc_length())
            if not any(v in occupied for v in edge.verts):
                selected.append(edge)
                occupied.update(v for vertex in edge.verts for e in vertex.link_edges for v in e.verts)
        if not selected:
            break
        bmesh.ops.collapse(bm, edges=selected, uvs=True)
        bmesh.ops.dissolve_degenerate(bm, dist=.00001, edges=list(bm.edges))
        for v in bm.verts:
            v.co = reference.find_nearest(v.co)[0]
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    density['quality'] = mesh_quality(obj)
    if not density['quality']['pass']:
        raise ValueError(f'{obj.name}: unresolved coarse cloth elements: {density}')
    return density


def split_world(obj, points):
    inverse = obj.matrix_world.inverted()
    return split_polyline(obj, [tuple(inverse@Vector(p)) for p in points], shrink_band=.015)


def welt_release(obj, back=False):
    p = np.array([obj.matrix_world@v.co for v in obj.data.vertices])
    lo, hi = p.min(0), p.max(0)
    cx = (lo[0]+hi[0])/2
    records = []
    if back:
        records.append(split_world(obj, [(x, lo[1]+.025, hi[2]-.025)
                                         for x in np.linspace(cx-.26, cx+.26, 50)]))
        for x in [lo[0]+.015, hi[0]-.015]:
            records.append(split_world(obj, [(x, y, hi[2]-.015)
                                             for y in np.linspace(lo[1]+.04, lo[1]+.12, 15)]))
    else:
        # The two long side runs plus the front release leave rear stitches.
        z = .559
        for x in [lo[0]+.012, hi[0]-.012]:
            records.append(split_world(obj, [(x, y, z) for y in np.linspace(lo[1]+.025, hi[1]-.11, 50)]))
        records.append(split_world(obj, [(x, lo[1]+.012, z) for x in np.linspace(lo[0]+.035, hi[0]-.035, 50)]))
        for x in [lo[0]+.012, hi[0]-.012]:
            records.append(split_world(obj, [(x, lo[1]+.012, z) for z in np.linspace(.451, .555, 20)]))
    perimeter = 2*((hi[0]-lo[0])+(hi[1]-lo[1]))
    share = sum(r['split_length_m'] for r in records[:3])/perimeter
    return {'runs': records, 'welt_split_share': share, 'target_share': [.3, .5] if back else [.55, .75]}


def tie_pins(obj):
    p = np.array([obj.matrix_world@v.co for v in obj.data.vertices])
    cx = obj.matrix_world.translation.x
    pins = {}
    patches = []
    for x in [cx-.20, cx, cx+.20]:
        rear = np.flatnonzero(p[:, 1] >= .34)
        nearest = rear[np.linalg.norm(p[rear][:, [0, 2]]-[x, .61], axis=1).argmin()]
        centre = p[nearest]
        ids = np.flatnonzero((np.abs(p[:, 0]-centre[0]) <= .018) &
                             (np.abs(p[:, 2]-centre[2]) <= .010) & (p[:, 1] >= .34))
        inverse = obj.matrix_world.inverted()
        for index in ids:
            p[index, 2] = np.clip(p[index, 2], .60, .62)
            obj.data.vertices[int(index)].co = inverse@Vector(p[index])
        pins.update({int(i): 1. for i in ids})
        patches.append({'vertices': ids.tolist(), 'bounds_m': [p[ids].min(0).tolist(), p[ids].max(0).tolist()]})
    return pins, patches
