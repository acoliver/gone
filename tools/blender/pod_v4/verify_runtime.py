"""Check prepared Godot arrays against the retained source, using Blender's BVH.

Export with tools/pod_geometry_export.gd first, then pass --runtime and --output.
These local-pod checks do not certify room-wide transparency ordering.
"""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
from mathutils.geometry import barycentric_transform

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_glass import topology


def arrays(part):
    vertices = [Vector(v) for v in part['vertices']]
    normals = [Vector(n) for n in part['normals']]
    indices = part['indices']
    # Godot indices use clockwise front faces; Blender's BVH uses CCW normals.
    faces = [(indices[i], indices[i+2], indices[i+1]) for i in range(0, len(indices), 3)]
    return vertices, normals, faces, BVHTree.FromPolygons(vertices, faces, all_triangles=True)


def nearest(trees, origin, direction):
    hits = []
    for part, tree in trees:
        point, _, triangle, distance = tree.ray_cast(origin, direction)
        if point is not None:
            hits.append(dict(node=part['node'], material=part['material'], triangle=triangle,
                             point=point[:], distance=distance))
    return min(hits, key=lambda h: h['distance']) if hits else None


def interior_grid(vertices, normals, faces, roles, tree):
    uses = Counter(tuple(sorted((tuple(vertices[a]), tuple(vertices[b]))))
        for face, role in zip(faces, roles) if role == 0
        for a, b in zip(face, face[1:] + face[:1]))
    segments = [(Vector(a), Vector(b)) for (a, b), count in uses.items() if count == 1]
    # Downward rays need the projected clear opening at the skirt's lower
    # boundary. A 3D distance on the steep crown includes its seated rim.
    all_uses = Counter(tuple(sorted((tuple(vertices[a]), tuple(vertices[b]))))
        for face in faces for a, b in zip(face, face[1:] + face[:1]))
    aperture = [(Vector((a[0], 0, a[2])), Vector((b[0], 0, b[2])))
        for (a, b), count in all_uses.items() if count == 1]
    assert aperture, 'render sheet must retain its authored skirt boundary'
    xmin, xmax = min(v.x for v in vertices), max(v.x for v in vertices)
    zmin, zmax = min(v.z for v in vertices), max(v.z for v in vertices)
    top = max(v.y for v in vertices) + .1
    for ix in range(math.ceil(xmin/.005), math.floor(xmax/.005)+1):
        for iz in range(math.ceil(zmin/.005), math.floor(zmax/.005)+1):
            point, _, triangle, _ = tree.ray_cast(Vector((ix*.005, top, iz*.005)), Vector((0,-1,0)))
            if point is None or roles[triangle] != 0:
                continue
            # Exact distance to every boundary segment, rather than grid erosion.
            distance = min((point-a.lerp(b, max(0., min(1., (point-a).dot(b-a)/(b-a).length_squared)))).length for a, b in segments)
            if distance < .01:
                continue
            face = faces[triangle]
            normal = barycentric_transform(point, *(vertices[i] for i in face), *(normals[i] for i in face)).normalized()
            yield 'grid-normal', triangle, point, normal
            projected = Vector((point.x, 0, point.z))
            crossings = sum((a.z > projected.z) != (b.z > projected.z)
                and projected.x < a.x + (b.x-a.x)*(projected.z-a.z)/(b.z-a.z)
                for a, b in aperture)
            clearance = min((projected-a.lerp(b, max(0., min(1.,
                (projected-a).dot(b-a)/(b-a).length_squared)))).length for a, b in aperture)
            if crossings % 2 and clearance >= .01:
                yield 'grid-down', triangle, point, Vector((0,1,0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    args.output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(Path(__file__).with_name('pod-v4-working.blend')))
    bpy.context.view_layer.update()
    source = bpy.data.objects['WindowPane']
    source_vertices = [source.matrix_world @ v.co for v in source.data.vertices]
    regions = [d.value for d in source.data.attributes['pane_region'].data]
    source_faces = [list(p.vertices) for p, r in zip(source.data.polygons, regions) if r != 1]
    source_regions = [r for r in regions if r != 1]
    source_roles = {tuple(sorted(f)): r for f, r in zip(source_faces, source_regions)}
    vertex_tree = KDTree(len(source_vertices))
    for i, point in enumerate(source_vertices):
        vertex_tree.insert(point, i)
    vertex_tree.balance()
    pivot = bpy.data.objects['PodLid'].matrix_world.translation.copy()
    reference = []
    for name in ('PodBase', 'PodLid', 'Couch', 'Pillow'):
        obj = bpy.data.objects[name]
        vv = [obj.matrix_world @ v.co for v in obj.data.vertices]
        obj.data.calc_loop_triangles()
        for material_index, material in enumerate(obj.data.materials):
            faces = [list(t.vertices) for t in obj.data.loop_triangles if obj.data.polygons[t.polygon_index].material_index == material_index]
            reference.append((dict(node=name, material=material.name), BVHTree.FromPolygons(vv, faces, all_triangles=True)))
    data = json.loads(args.runtime.read_text())
    results = dict(asset_sha256=data['asset_sha256'], cases=[], failures=[])
    with (args.output / 'runtime-rays.jsonl').open('w') as records:
        for case in data['cases']:
            parts = case['parts']
            assert len({p['node'] for p in parts}) == 5
            assert len({p['material'] for p in parts}) == 5
            triangles = sum(len(p['indices']) // 3 for p in parts)
            assert triangles <= 20000, triangles
            pane, = [p for p in parts if p['node'] == 'WindowPane']
            vv, nn, faces, pane_tree = arrays(pane)
            weld = {}
            remap = [weld.setdefault(tuple(v), len(weld)) for v in vv]
            topo = topology(None, [[remap[i] for i in f] for f in faces])
            assert topo['nonmanifold'] == 0 and topo['boundary_loops'] == 1, topo
            opaque = [(p, arrays(p)[3]) for p in parts if p['node'] != 'WindowPane']
            inverse = Matrix.Rotation(-case['angle'], 3, 'X')
            row = dict(state=case['state'], angle=case['angle'], triangles=triangles,
                       topology=topo, max_unit_error=max(abs(n.length-1) for n in nn),
                       minimum_corner_dot=1., minimum_broad_dot=1., source_error=0.,
                       near_backing=0, closed_misses=0, closed_wrong_witness=0,
                       maximum_witness_position_error=0., rays=0, minimum_backing=math.inf)
            assert row['max_unit_error'] < 1e-4
            source_indices = []
            for point in vv:
                original = pivot + inverse @ (point-pivot)
                _, source_index, error = vertex_tree.find(original)
                source_indices.append(source_index)
                row['source_error'] = max(row['source_error'], error)
            roles = [source_roles[tuple(sorted(source_indices[i] for i in face))] for face in faces]
            (args.output / ('pane-regions-%s.json' % case['state'])).write_text(json.dumps(roles))
            samples = []
            for triangle, face in enumerate(faces):
                point = sum((vv[i] for i in face), Vector()) / 3
                region = roles[triangle]
                geom = (vv[face[1]]-vv[face[0]]).cross(vv[face[2]]-vv[face[0]])
                assert geom.length > 1e-12, ('degenerate', triangle)
                geom.normalize()
                dots = [geom.dot(nn[i]) for i in face]
                row['minimum_corner_dot'] = min(row['minimum_corner_dot'], *dots)
                masks = [pane['mask'][i] for i in face]
                target = 1 if region == 2 else 0
                assert all(abs(m-target) < 1e-5 for m in masks), (region, masks)
                if region != 0:
                    continue
                row['minimum_broad_dot'] = min(row['minimum_broad_dot'], *dots)
                normal = sum((nn[i] for i in face), Vector()).normalized()
                samples.append(('centroid-normal', triangle, point, normal))
            if case['closed']:
                samples.extend(interior_grid(vv, nn, faces, roles, pane_tree))
                central, _, _, _ = pane_tree.ray_cast(Vector((0,2,0)), Vector((0,-1,0)))
                backing = nearest(opaque, central-Vector((0,.00001,0)), Vector((0,-1,0)))
                row['central_couch_distance'] = backing['distance'] + .00001
                assert backing['node'] == 'Couch' and abs(row['central_couch_distance']-.6559952) < .0005
            for family, triangle, point, normal in samples:
                for sign in ((-1,) if family == 'grid-down' else (-1, 1)):
                    direction = normal * sign
                    origin = point + direction * .00001
                    hit = nearest(opaque, origin, direction)
                    expected = nearest(reference, origin, direction) if case['closed'] and sign == -1 else None
                    records.write(json.dumps(dict(state=case['state'], lid_angle=case['angle'],
                        pivot=pivot[:], family=family, origin=origin[:], direction=direction[:],
                        pane_triangle=triangle, pane_point=point[:], first_opaque=hit, reference_opaque=expected)) + '\n')
                    row['rays'] += 1
                    if hit:
                        row['minimum_backing'] = min(row['minimum_backing'], hit['distance'])
                        row['near_backing'] += hit['distance'] < .02
                    if case['closed'] and sign == -1:
                        row['closed_misses'] += hit is None
                        if hit and expected:
                            deviation = (Vector(hit['point'])-Vector(expected['point'])).length
                            row['maximum_witness_position_error'] = max(row['maximum_witness_position_error'], deviation)
                            row['closed_wrong_witness'] += hit['node'] not in ('Couch', 'Pillow', 'PodBase') or hit['node'] != expected['node'] or deviation > .002
            row['pass'] = (row['source_error'] <= .000002 and row['minimum_corner_dot'] > 0
                and row['minimum_broad_dot'] >= .98 and row['near_backing'] == 0
                and row['closed_misses'] == 0 and row['closed_wrong_witness'] == 0)
            if math.isinf(row['minimum_backing']):
                row['minimum_backing'] = None
            results['cases'].append(row)
            if not row['pass']:
                results['failures'].append(case['state'])
    (args.output / 'runtime-geometry.json').write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2), flush=True)
    assert not results['failures'], results['failures']


if __name__ == '__main__':
    main()
