"""CPU geometry gates for the retained glazing solid and its render derivative.

Run with the supported Blender binary; --output selects the raw evidence directory.
Distances are metres. The intentionally open render sheet is not a modeling solid.
"""
import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parent


def topology(mesh, faces):
    uses = Counter(tuple(sorted((a, b))) for face in faces for a, b in zip(face, face[1:] + face[:1]))
    boundary = [edge for edge, count in uses.items() if count == 1]
    graph = defaultdict(set)
    for a, b in boundary:
        graph[a].add(b)
        graph[b].add(a)
    loops = 0
    unseen = set(graph)
    while unseen:
        loops += 1
        stack = [unseen.pop()]
        while stack:
            for neighbor in graph[stack.pop()]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    stack.append(neighbor)
    return dict(nonmanifold=sum(n > 2 for n in uses.values()), boundary_edges=len(boundary), boundary_loops=loops)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    args.output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'pod-v4-working.blend'))
    pane = bpy.data.objects['WindowPane']
    mesh = pane.data
    assert 'pane_region' in mesh.attributes, 'missing explicit pane face regions'
    regions = [d.value for d in mesh.attributes['pane_region'].data]
    faces = [list(p.vertices) for p in mesh.polygons]
    solid = topology(mesh, faces)
    render = topology(mesh, [f for f, r in zip(faces, regions) if r != 1])
    assert solid == dict(nonmanifold=0, boundary_edges=0, boundary_loops=0), solid
    assert render['nonmanifold'] == 0 and render['boundary_loops'] == 1, render
    assert set(regions) == {0, 1, 2, 3}, 'outer, inner, edge and bevel must survive'
    vertices = [pane.matrix_world @ v.co for v in mesh.vertices]
    minimum_dot = 1.0
    degenerate = 0
    for p, region in zip(mesh.polygons, regions):
        a, b, c = [vertices[i] for i in p.vertices]
        normal = (b - a).cross(c - a)
        if normal.length < 1e-12:
            degenerate += 1
            continue
        normal.normalize()
        for loop in p.loop_indices:
            n = mesh.corner_normals[loop].vector
            assert abs(n.length - 1) < 1e-4
            dot = normal.dot(n)
            assert dot > 0, (p.index, region, dot)
            if region == 0:
                minimum_dot = min(minimum_dot, dot)
    assert degenerate == 0
    assert minimum_dot >= .98, minimum_dot
    retained = mesh.attributes['retained_position']
    successor = {}
    uses = Counter(tuple(sorted((a, b))) for face, region in zip(faces, regions) if region == 0 for a, b in zip(face, face[1:] + face[:1]))
    for face, region in zip(faces, regions):
        if region != 0:
            continue
        for a, b in zip(face, face[1:] + face[:1]):
            if uses[tuple(sorted((a, b)))] == 1:
                successor[a] = b
    ring = [min(successor)]
    while successor[ring[-1]] != ring[0]:
        ring.append(successor[ring[-1]])
    original_segments = [(retained.data[i].vector.copy(), retained.data[successor[i]].vector.copy()) for i in ring]
    def boundary_distance(point):
        return min((point - a.lerp(b, max(0, min(1, (point-a).dot(b-a)/(b-a).length_squared)))).length for a, b in original_segments)
    correspondence = []
    worst_position = 0
    worst_thickness = 0
    for i in range(2025):
        before = retained.data[i].vector
        after = vertices[i]
        change = (after - before).length
        if boundary_distance(before) > .002:
            worst_position = max(worst_position, change)
            original_inner = retained.data[i + 2025].vector
            thickness = (before - original_inner).length
            new_thickness = (after - vertices[i + 2025]).length
            worst_thickness = max(worst_thickness, abs(new_thickness - thickness))
            correspondence.append([i, thickness, new_thickness])
    assert len(correspondence) > 1500
    assert worst_position <= .000002 and worst_thickness <= .00005
    exterior_normals = {}
    for poly, region in zip(mesh.polygons, regions):
        if region == 0:
            for loop in poly.loop_indices:
                exterior_normals[mesh.loops[loop].vertex_index] = mesh.corner_normals[loop].vector.copy()
    measured_radii = []
    measured_reveals = []
    for k, i in enumerate(ring):
        normal = exterior_normals[i]
        center = vertices[i] - normal * .0005
        inward = (vertices[i] - retained.data[i].vector).normalized()
        for segment in range(1, 4):
            point = vertices[4050 + (segment - 1) * len(ring) + k]
            radius = (point - center).length
            measured_radii.append(radius)
            assert abs(radius - .0005) <= .00005
            expected_cosine = math.cos(math.pi * .5 * segment / 3)
            assert abs((point - center).normalized().dot(normal) - expected_cosine) < .001
        cut = vertices[4050 + 2 * len(ring) + k]
        reveal = (cut - retained.data[i].vector).dot(inward)
        measured_reveals.append(reveal)
        assert abs(reveal - .001) <= .0001
    construction = json.loads(pane['glass_construction'])
    assert abs(construction['bevel_radius'] - .0005) <= .00005
    assert construction['bevel_segments'] == 3
    assert abs(construction['interface_separation'] - .00005) < .000001, 'seat separation must be 0.05 mm'
    assert abs(construction['reveal'] - .001) <= .0001
    assert abs(construction['gasket_recess'] - .0015) <= .0001
    # Nearest opaque surface behind every broad triangle centroid, preserving
    # real node/triangle identities instead of exempting all shell plastic.
    lid = bpy.data.objects['PodLid']
    seat_vertices = [lid.matrix_world @ v.co for v in lid.data.vertices]
    seat_topology = topology(lid.data, [list(p.vertices) for p in lid.data.polygons if p.material_index == 1])
    assert seat_topology['boundary_edges'] == seat_topology['nonmanifold'] == 0, 'gasket seat must be closed'
    seat = BVHTree.FromPolygons(seat_vertices, [list(p.vertices) for p in lid.data.polygons if p.material_index == 1], all_triangles=True)
    render_bvh = BVHTree.FromPolygons(vertices, [f for f, r in zip(faces, regions) if r != 1], all_triangles=True)
    assert not render_bvh.overlap(seat), 'pane skirt intersects its gasket'
    opaque = []
    for name in ('PodBase', 'PodLid', 'Couch', 'Pillow'):
        obj = bpy.data.objects[name]
        vv = [obj.matrix_world @ v.co for v in obj.data.vertices]
        opaque.append((name, BVHTree.FromPolygons(vv, [list(p.vertices) for p in obj.data.polygons], all_triangles=False)))
    rays = []
    forbidden = 0
    minimum = math.inf
    for p, region in zip(mesh.polygons, regions):
        if region != 0:
            continue
        point = sum((vertices[i] for i in p.vertices), Vector()) / 3
        n = sum((mesh.corner_normals[l].vector for l in p.loop_indices), Vector()).normalized()
        hits = []
        for name, bvh in opaque:
            hit, hn, index, distance = bvh.ray_cast(point - n * .00001, -n)
            if hit is not None:
                hits.append((distance, name, index, hit[:]))
        hits.sort()
        assert hits, ('aperture miss', point[:])
        distance, name, triangle, hit = hits[0]
        minimum = min(minimum, distance)
        if name == 'PodLid' or distance < .02:
            forbidden += 1
        rays.append(dict(origin=point[:], direction=(-n)[:], pane_triangle=p.index, opaque_node=name, opaque_triangle=triangle, hit=hit, distance=distance))
    assert forbidden == 0, forbidden
    sys.path.insert(0, str(ROOT))
    from build import render_pane
    inherited_normals = [mesh.corner_normals[l].vector.copy() for p, region in zip(mesh.polygons, regions) if region != 1 for l in p.loop_indices]
    render_pane(pane)
    render_normal_error = max(a.angle(b.vector, 0) for a, b in zip(inherited_normals, pane.data.corner_normals))
    assert render_normal_error <= math.radians(.1), ('export derivative changed inherited normals', math.degrees(render_normal_error))
    (args.output / 'source-rays.json').write_text(json.dumps(rays))
    (args.output / 'thickness.json').write_text(json.dumps(correspondence))
    result = dict(render_normal_error_degrees=math.degrees(render_normal_error), solid=solid, render=render, seat=seat_topology, degenerate=degenerate, broad_normal_dot=minimum_dot, retained_broad_position_error=worst_position, thickness_change=worst_thickness, construction=construction, measured_bevel_radius_range=[min(measured_radii), max(measured_radii)], measured_reveal_range=[min(measured_reveals), max(measured_reveals)], pane_gasket_intersections=0, broad_centroid_rays=len(rays), forbidden_hits=forbidden, minimum_backing_distance=minimum)
    (args.output / 'geometry.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
