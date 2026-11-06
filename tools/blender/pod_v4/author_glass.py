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
# Offset covers the retained tapered edge's finite-triangle chord deviation.
SEAT_GAP = .00025


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
    seat_rings = []
    for offset, depth in [(REVEAL-SEAT_GAP,RECESS),(.00005,RECESS),(.00005,.007),(REVEAL-SEAT_GAP,.007)]:
        ids = []
        for i in ring:
            ids.append(len(lv))
            # The retained paired solid has a tapered cut. Follow its actual
            # generatrix rather than pushing a vertical seat through that edge.
            cut = vertices[rings[-1][ring.index(i)]]
            bottom = vertices[i + 2025]
            lower_depth = (original[i] - bottom).dot(inherited[i])
            fraction = (depth - RADIUS) / (lower_depth - RADIUS)
            edge_at_depth = cut.lerp(bottom, fraction)
            lv.append(edge_at_depth + tangent[i] * (offset - REVEAL))
        seat_rings.append(ids)
    for side in range(4):
        a, b = seat_rings[side], seat_rings[(side+1)%4]
        for k in range(len(ring)):
            j = (k+1)%len(ring)
            for f in [[a[k],b[j],a[j]],[a[k],b[k],b[j]]]:
                n = (lv[f[1]]-lv[f[0]]).cross(lv[f[2]]-lv[f[0]]).normalized()
                lf.append(f)
                ln.extend([tuple(n)]*3)
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
