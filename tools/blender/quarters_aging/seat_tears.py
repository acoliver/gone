"""Length-limited grain splits and a conserved narrow fallen island."""
import bmesh
import numpy as np
from mathutils import Vector

from common import surface_tree
from grain_paths import surface_walk
from tear_paths import split_polyline


def author(obj, centre_x=0., seed=9501):
    paths, records = [], []
    for i, (start, length) in enumerate([((-.13, -.12, .65), .18), ((-.16, -.34, .57), .16)]):
        point = (start[0]+centre_x, start[1], start[2])
        path = surface_walk(obj, point, length, seed+i*11, step=.004, direction=(1, 0, 0))
        paths.append(path)
    # A tapered opening exposes the fallen island without a uniform-width slot.
    # Its frame follows the fitted UV gradient, not an assumed world-axis grain.
    centre = Vector((centre_x+.075, -.15, .6))
    axis_path = surface_walk(obj, centre, .012, seed+50)
    tree = surface_tree(obj)
    centre, normal, _, _ = tree.find_nearest(centre)
    warp = (obj.matrix_world@Vector(axis_path[-1])-obj.matrix_world@Vector(axis_path[0])).normalized()
    weft = normal.cross(warp).normalized()
    outline = [(-.025, -.018), (-.008, -.018), (-.008, -.022), (.022, -.022),
               (.022, .003), (.027, .003), (.027, .019), (.004, .019),
               (.004, .024), (-.025, .024), (-.025, -.018)]
    inverse = obj.matrix_world.inverted()
    loop = []
    for u, v in outline:
        taper = .8+1.6*max(1-abs(u)/.028, 0)
        point, _, _, _ = tree.find_nearest(centre+warp*(u*2.6)+weft*(v*.4*taper))
        loop.append(tuple(inverse@point))
    # Snap and split in one operation so the closed edge chain separates the
    # island, while keeping its faces in the same physical simulation.
    paths.append(loop)
    for index, path in enumerate(paths):
        records.append(split_polyline(obj, path, max_length=.240 if index < 2 else None))
    if any(not .120 <= record['split_length_m'] <= .250 for record in records[:2]):
        raise ValueError('Seat main splits must have 120 to 250 mm of actual cut edges')
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    unseen = set(bm.verts)
    components = []
    while unseen:
        stack, found = [unseen.pop()], []
        while stack:
            vertex = stack.pop()
            found.append(vertex)
            neighbours = {e.other_vert(vertex) for e in vertex.link_edges} & unseen
            unseen.difference_update(neighbours)
            stack.extend(neighbours)
        components.append(found)
    small = [c for c in components if len(c) < len(bm.verts)*.1 and len(c) > 3]
    if not small:
        bm.free()
        raise ValueError('Closed tear did not detach a fallen island')
    island = min(small, key=lambda c: ((sum((obj.matrix_world@v.co for v in c), Vector())/len(c))-centre).length)
    group = obj.vertex_groups.new(name='Fallen island')
    layer = bm.verts.layers.deform.verify()
    for vertex in island:
        vertex[layer][group.index] = 1.
    island_area = sum(f.calc_area() for f in bm.faces if all(v in island for v in f.verts))
    island_points = np.array([obj.matrix_world@v.co for v in island])
    island_size = float(np.linalg.norm(island_points[:, None]-island_points[None, :], axis=2).max())
    if not .120 <= island_size <= .250:
        bm.free()
        raise ValueError(f'Seat fallen slit is outside 120 to 250 mm: {island_size}')
    bm.to_mesh(obj.data)
    bm.free()
    return {'method': 'two length-limited UV-gradient splits and a long narrow conserved fallen island',
            'paths': records, 'fallen_island_vertices': len(island),
            'fallen_island_reference_size_m': island_size, 'fallen_island_reference_area_m2': island_area}
