"""Exclude sub-diameter rest triangles from Blender's minimum-radius self contact."""
import numpy as np
from mathutils.kdtree import KDTree


def exclude_small_rest_faces(obj, mod, subdivision_levels=0):
    # Blender 4.5 clamps self_distance_min to 1 mm. On graded 3 mm bands,
    # triangle altitudes can be smaller than the 2 mm contact diameter.
    # Those adjacent rest faces repel before any fold exists. Keep regular
    # sleeve faces in self contact, while excluding these unresolved bands.
    diameter = 2*mod.collision_settings.self_distance_min
    base_altitude = diameter*2**subdivision_levels
    group = obj.vertex_groups.get('Self collision exclusion') or obj.vertex_groups.new(name='Self collision exclusion')
    positions = np.array([v.co[:] for v in obj.data.vertices])
    rest = mod.settings.rest_shape_key
    targets = [positions]
    if rest is not None:
        targets.append(np.array([v.co[:] for v in rest.data]))
    obj.data.calc_loop_triangles()
    tree = KDTree(len(positions))
    for i, point in enumerate(positions):
        tree.insert(point, i)
    tree.balance()
    split_vertices = {i for i, point in enumerate(positions)
                      if len(tree.find_range(point, 1e-7)) > 1}
    excluded = set()
    count = 0
    split_faces = 0
    for triangle in obj.data.loop_triangles:
        ids = np.array(triangle.vertices)
        altitudes = []
        for shape in targets:
            points = shape[ids]
            lengths = np.linalg.norm(points-np.roll(points, 1, axis=0), axis=1)
            area2 = np.linalg.norm(np.cross(points[1]-points[0], points[2]-points[0]))
            altitudes.append(area2/lengths.max())
        if min(altitudes) < base_altitude:
            excluded.update(ids.tolist())
            count += 1
        if split_vertices.intersection(ids.tolist()):
            # Zero-area splits begin with coincident lips, like sewn plies.
            excluded.update(ids.tolist())
            split_faces += 1
    if excluded:
        group.add(sorted(excluded), 1., 'REPLACE')
    mod.collision_settings.vertex_group_self_collisions = group.name
    return dict(actual_self_distance_m=float(mod.collision_settings.self_distance_min),
                contact_diameter_m=float(diameter), base_altitude_threshold_m=float(base_altitude),
                subdivision_levels=subdivision_levels, sub_diameter_faces=count,
                exclusion_vertices=len(excluded), coincident_lip_faces=split_faces,
                total_faces=len(obj.data.loop_triangles))
