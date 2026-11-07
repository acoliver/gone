"""One-time #88 glass edge authoring on the verified retained paired solid.

Ordinary exports use build.py and consume saved regions, never reapply this trim.
All perimeter edits stay inside the 2 mm band; the inner modeling face is retained.
"""
from collections import Counter
import argparse
import sys
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
PIVOT = Vector((0.0, 0.437, -1.1725093126296997))
RADIUS = .0005
REVEAL = .001
RECESS = .0015
SEAT_GAP = .00005


def mesh_object(obj, vertices, faces, normals, regions=None, materials=None):
    mesh = bpy.data.meshes.new(obj.name + 'Authored')
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    for material in materials or list(obj.data.materials):
        mesh.materials.append(material)
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.normals_split_custom_set(normals)
    if regions is not None:
        attr = mesh.attributes.new('pane_region', 'INT', 'FACE')
        for datum, region in zip(attr.data, regions):
            datum.value = region
    old = obj.data
    obj.data = mesh
    bpy.data.meshes.remove(old)
    return mesh


def clipped_seat(vertices, faces, regions, tangents, depths, stations):
    """Follow the actual skirt triangles, including their diagonal crease.

    Interpolating whole perimeter quads cuts across the retained skirt's
    nonplanar facets. Clipping each facet preserves its plane at the seat.
    """
    def clip(polygon, limit, above):
        result = []
        for a, b in zip(polygon, polygon[1:] + polygon[:1]):
            a_inside = a['depth'] >= limit if above else a['depth'] <= limit
            b_inside = b['depth'] >= limit if above else b['depth'] <= limit
            if a_inside != b_inside:
                weight = (limit - a['depth']) / (b['depth'] - a['depth'])
                support = a['support'] | b['support']
                assert len(support) == 2, 'seat clipping must stay on a source edge'
                result.append(dict(point=a['point'].lerp(b['point'], weight), tangent=a['tangent'].lerp(b['tangent'], weight), depth=limit, support=support))
            if b_inside:
                result.append(b)
        return result

    points = []
    front = []
    lookup = {}
    for face, region in zip(faces, regions):
        if region != 2:
            continue
        polygon = [dict(point=vertices[i], tangent=tangents[i], depth=depths[i], support=frozenset([i])) for i in face]
        polygon = clip(clip(polygon, RECESS, True), .007, False)
        indices = []
        for point in polygon:
            key = (tuple(sorted(point['support'])), round(point['depth'], 9))
            if key not in lookup:
                lookup[key] = len(points)
                points.append(point)
            indices.append(lookup[key])
        for i in range(1, len(indices) - 1):
            front.append([indices[0], indices[i + 1], indices[i]])
    count = len(points)
    perimeter = len(stations) // 2
    seat_vertices = [p['point'] - p['tangent'] * SEAT_GAP for p in points]
    seat_vertices += [p['point'] - p['tangent'] * (REVEAL - SEAT_GAP) for p in points]
    top, bottom, back_top = [], [], []
    for i, point in enumerate(points):
        support = {stations[j] for j in point['support']}
        station = next(iter(support)) if len(support) == 1 else (perimeter - .5 if support == {0, perimeter - 1} else min(support) + .5)
        if abs(point['depth'] - RECESS) < 1e-9:
            top.append((station, i))
            if len(support) == 1:
                back_top.append((station, i + count))
        else:
            assert len(support) == 1, 'seat bottom must meet the retained inner edge'
            bottom.append((station, i))
    top.sort()
    bottom.sort()
    back_top.sort()
    back_bottom = [(station, i + count) for station, i in bottom]
    original_bottom = list(back_bottom)

    def segment_distance(point, a, b):
        weight = max(0, min(1, (point-a).dot(b-a)/(b-a).length_squared))
        return (point - a.lerp(b, weight)).length

    # The lower frame-facing contour is hidden inside the seat. Reduce only
    # that new contour, not the pane-facing facets, exposed top or old gasket.
    while len(back_bottom) > 3:
        candidates = []
        for i in range(1, len(back_bottom)):
            previous = back_bottom[i-1]
            following = back_bottom[(i+1) % len(back_bottom)]
            span = (following[0] - previous[0]) % perimeter
            samples = [seat_vertices[j] for station, j in original_bottom if (station-previous[0]) % perimeter <= span]
            error = max(segment_distance(p, seat_vertices[previous[1]], seat_vertices[following[1]]) for p in samples)
            if error <= .0004:
                candidates.append((error, i))
        if not candidates:
            break
        del back_bottom[min(candidates)[1]]

    seat_faces = list(front)
    def join(a, b):
        ia = ib = 0
        while ia < len(a) or ib < len(b):
            next_a = a[ia+1][0] if ia+1 < len(a) else perimeter if ia < len(a) else math.inf
            next_b = b[ib+1][0] if ib+1 < len(b) else perimeter if ib < len(b) else math.inf
            current_a = a[ia % len(a)][1]
            current_b = b[ib % len(b)][1]
            if next_a <= next_b:
                seat_faces.append([current_a, current_b, a[(ia+1) % len(a)][1]])
                ia += 1
            else:
                seat_faces.append([current_a, current_b, b[(ib+1) % len(b)][1]])
                ib += 1
    join(top, back_top)
    join(back_top, back_bottom)
    join(back_bottom, bottom)
    used = sorted({i for face in seat_faces for i in face})
    remap = {old: new for new, old in enumerate(used)}
    return [seat_vertices[i] for i in used], [[remap[i] for i in face] for face in seat_faces]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'pod-v4-working.blend')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    pane = bpy.data.objects['WindowPane']
    source = pane.data
    assert 'pane_region' not in source.attributes, 'conversion already authored; export with build.py'
    assert len(source.vertices) == 4050 and len(source.polygons) == 8096
    original = [v.co.copy() for v in source.vertices]
    outer = [p for p in source.polygons if all(i < 2025 for i in p.vertices)]
    inner = [p for p in source.polygons if all(i >= 2025 for i in p.vertices)]
    edges = [p for p in source.polygons if p not in outer and p not in inner]
    assert (len(outer), len(inner), len(edges)) == (3872, 3872, 352)
    uses = Counter(tuple(sorted((a, b))) for p in outer for a, b in zip(list(p.vertices), list(p.vertices)[1:] + list(p.vertices)[:1]))
    boundary_edges = {edge for edge, count in uses.items() if count == 1}
    # Orient the boundary exactly as the exterior triangles do.
    successor = {}
    for poly in outer:
        face = list(poly.vertices)
        for a, b in zip(face, face[1:] + face[:1]):
            if tuple(sorted((a,b))) in boundary_edges:
                successor[a] = b
    ring = [min(successor)]
    while successor[ring[-1]] != ring[0]:
        ring.append(successor[ring[-1]])
    assert len(ring) == 176
    inherited = {}
    for p in outer:
        for loop in p.loop_indices:
            inherited[source.loops[loop].vertex_index] = source.corner_normals[loop].vector.copy()
    tangent = {}
    for k, i in enumerate(ring):
        along = (original[ring[(k+1)%len(ring)]] - original[ring[k-1]]).normalized()
        inward = inherited[i].cross(along).normalized()
        if inward.dot(Vector((-original[i].x,0,-original[i].z))) < 0:
            inward = -inward
        tangent[i] = inward
    vertices = [v.copy() for v in original]
    for i in ring:
        vertices[i] += tangent[i] * (REVEAL + RADIUS)
        vertices[i + 2025] += tangent[i] * REVEAL
    faces = [list(p.vertices) for p in outer + inner]
    regions = [0] * len(outer) + [1] * len(inner)
    normals = [tuple(source.corner_normals[l].vector) for p in outer + inner for l in p.loop_indices]
    rings = [ring]
    for segment in range(1,4):
        phi = math.pi * .5 * segment / 3
        new_ring = []
        for i in ring:
            new_ring.append(len(vertices))
            vertices.append(original[i] + tangent[i] * (REVEAL + RADIUS - RADIUS * math.sin(phi)) - inherited[i] * RADIUS * (1 - math.cos(phi)))
        rings.append(new_ring)
    def band(a, b, region, normal_a, normal_b):
        for k in range(len(ring)):
            j = (k + 1) % len(ring)
            # Exterior boundary winding closes outward across the edge.
            for f, nn in [([a[k], b[j], a[j]], [normal_a[k],normal_b[j],normal_a[j]]), ([a[k],b[k],b[j]], [normal_a[k],normal_b[k],normal_b[j]])]:
                faces.append(f)
                regions.append(region)
                normals.extend(tuple(n) for n in nn)
    for segment in range(3):
        p0 = math.pi * .5 * segment / 3
        p1 = math.pi * .5 * (segment+1) / 3
        n0 = [inherited[i] * math.cos(p0) - tangent[i] * math.sin(p0) for i in ring]
        n1 = [inherited[i] * math.cos(p1) - tangent[i] * math.sin(p1) for i in ring]
        band(rings[segment], rings[segment+1], 3, n0, n1)
    edge_normals = [-tangent[i] for i in ring]
    band(rings[-1], [i + 2025 for i in ring], 2, edge_normals, edge_normals)
    mesh = mesh_object(pane, vertices, faces, normals, regions)
    attr = mesh.attributes.new('retained_position', 'FLOAT_VECTOR', 'POINT')
    for datum, vertex in zip(attr.data, original):
        datum.vector = vertex
    pane['glass_construction'] = json.dumps(dict(bevel_radius=RADIUS, bevel_segments=3,reveal=REVEAL,gasket_recess=RECESS,interface_separation=SEAT_GAP,source_pairs=2025))
    preview = mesh.materials[0]
    preview.use_nodes = True
    bsdf = next(n for n in preview.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = (1,1,1,1)
    bsdf.inputs['Metallic'].default_value = 0
    bsdf.inputs['Roughness'].default_value = .07
    bsdf.inputs['Transmission Weight'].default_value = 1
    bsdf.inputs['IOR'].default_value = 1.5
    # A closed annular seat shares the existing Gasket material and lid node.
    lid = bpy.data.objects['PodLid']
    lv = [v.co.copy() for v in lid.data.vertices]
    lf = [list(p.vertices) for p in lid.data.polygons]
    ln = [tuple(n.vector) for n in lid.data.corner_normals]
    material_ids = [p.material_index for p in lid.data.polygons]
    materials = list(lid.data.materials) + [bpy.data.materials['Gasket']]
    edge_tangents = {}
    edge_depths = {}
    edge_stations = {}
    for k, i in enumerate(ring):
        cut, bottom = rings[-1][k], i + 2025
        edge_tangents[cut] = edge_tangents[bottom] = tangent[i]
        edge_stations[cut] = edge_stations[bottom] = k
        edge_depths[cut] = RADIUS
        edge_depths[bottom] = (original[i] - vertices[bottom]).dot(inherited[i])
    seat_vertices, seat_faces = clipped_seat(vertices, faces, regions, edge_tangents, edge_depths, edge_stations)
    start = len(lv)
    lv.extend(seat_vertices)
    for face in seat_faces:
        face = [i + start for i in face]
        normal = (lv[face[1]]-lv[face[0]]).cross(lv[face[2]]-lv[face[0]]).normalized()
        lf.append(face)
        ln.extend([tuple(normal)]*3)
        material_ids.append(1)
    lm = mesh_object(lid,lv,lf,ln,materials=materials)
    for poly, index in zip(lm.polygons,material_ids):
        poly.material_index = index
    # The saved editable hierarchy owns the same seam origin as the export.
    for obj in (lid,pane):
        for vertex in obj.data.vertices:
            vertex.co -= PIVOT
        obj.location = PIVOT
    pane.parent = lid
    pane.location = (0,0,0)
    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'pod-v4-working.blend'))
    print('Authored pane regions, bevel, closed seat and seam origin',flush=True)


if __name__ == '__main__':
    main()
