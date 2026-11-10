"""Independent exported-mesh, ray, attachment and UV contracts; no builder imports."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'assets/props/bay-ceiling'
EVIDENCE = ROOT / 'tmp/verify-stasis-ceiling/geometry'


def glb_document(path):
    data = path.read_bytes()
    magic, version, length = struct.unpack_from('<4sII', data)
    assert magic == b'glTF' and version == 2 and length == len(data)
    size, chunk_type = struct.unpack_from('<I4s', data, 12)
    assert chunk_type == b'JSON'
    return json.loads(data[20:20+size])


def panel_mesh(name):
    scene = trimesh.load(OUT / f'{name}.glb', force='scene', process=False)
    return scene.geometry[scene.graph[name][1]].copy()


def vertical_hits(mesh, xz):
    """Intersect infinite Y rays against exported triangles using barycentric coordinates."""
    triangles = mesh.triangles
    plan = triangles[:, :, [0, 2]]
    a, u, v = plan[:, 0], plan[:, 1] - plan[:, 0], plan[:, 2] - plan[:, 0]
    cross = lambda p, q: p[..., 0]*q[..., 1] - p[..., 1]*q[..., 0]
    denominator = cross(u, v)
    valid = abs(denominator) > 1e-13
    d = np.asarray(xz) - a
    s = np.divide(cross(d, v), denominator, out=np.zeros_like(denominator), where=valid)
    t = np.divide(cross(u, d), denominator, out=np.zeros_like(denominator), where=valid)
    hit = valid & (s >= -1e-7) & (t >= -1e-7) & (s+t <= 1+1e-7)
    y = triangles[:, 0, 1] + s*(triangles[:, 1, 1]-triangles[:, 0, 1]) + t*(triangles[:, 2, 1]-triangles[:, 0, 1])
    return np.unique(np.round(y[hit], 7))


def closed_body(mesh, euler):
    mesh.merge_vertices(digits_vertex=7, merge_tex=True, merge_norm=True)
    mesh.remove_unreferenced_vertices()
    edges, counts = np.unique(np.sort(mesh.edges, axis=1), axis=0, return_counts=True)
    assert mesh.is_watertight, 'open shell'
    assert mesh.is_winding_consistent, 'inconsistent winding'
    assert mesh.volume > 0, 'inward winding'
    assert len(mesh.split(only_watertight=False)) == 1, 'disconnected islands'
    assert mesh.euler_number == euler, (mesh.euler_number, euler)
    assert np.all(counts == 2), 'nonmanifold edges'
    assert mesh.area_faces.min() > 1e-12, 'degenerate triangles'
    return {'triangles': len(mesh.faces), 'welded_vertices': len(mesh.vertices), 'edges': len(edges),
            'euler_characteristic': int(mesh.euler_number), 'components': 1,
            'watertight': True, 'winding_consistent': True,
            'boundary_edges': int(np.sum(counts == 1)), 'nonmanifold_edges': int(np.sum(counts != 2)),
            'signed_volume_m3': float(mesh.volume), 'minimum_triangle_area_m2': float(mesh.area_faces.min())}


def verify(name, manifest):
    path = OUT / f'{name}.glb'
    record = manifest['variants'][name]
    document = glb_document(path)
    nodes = {node['name']: node for node in document['nodes'] if 'mesh' in node}
    assert set(nodes) == {name, *record['hardware_names']}
    assert nodes[name]['extras']['role'] == 'closed_perforated_panel'
    assert nodes[name]['extras']['separate_hardware_bodies'] == 4
    scene = trimesh.load(path, force='scene', process=False)
    assert len(scene.geometry) == 5, (name, 'one panel and four explicit head bodies required')
    for node in scene.graph.nodes_geometry:
        matrix, _ = scene.graph[node]
        np.testing.assert_allclose(matrix, np.eye(4), atol=1e-8)
    mesh = panel_mesh(name)
    attrs = mesh.visual
    exported_vertices = len(mesh.vertices)
    uv = attrs.uv
    assert uv is not None and np.isfinite(uv).all()
    assert uv.min() >= -1e-6 and uv.max() <= 1+1e-6
    uv_tri = uv[mesh.faces]
    a, b = uv_tri[:, 1] - uv_tri[:, 0], uv_tri[:, 2] - uv_tri[:, 0]
    uv_areas = abs(a[:, 0]*b[:, 1] - a[:, 1]*b[:, 0]) / 2
    assert uv_areas.min() > 1e-13, (name, 'collapsed face UV', uv_areas.min())
    result = closed_body(mesh, 2 - 2*manifest['slot_count'])
    assert np.all(mesh.extents[[0, 2]] <= [1.180002, .580002]), mesh.extents
    if name not in ('torncorner', 'brokenedge'):
        assert np.allclose(mesh.extents[[0, 2]], [1.18, .58], atol=2e-6), mesh.extents
        assert np.allclose(mesh.bounds[:, [0, 2]].mean(axis=0), 0, atol=2e-6)
    assert .0199 <= mesh.extents[1] < .061, (name, 'incorrect height axis or scale')
    assert mesh.bounds[0, 1] + 2.99 > 2.85, (name, 'installed clearance')
    vertices = mesh.vertices
    groups = {}
    for x, y, z in vertices:
        groups.setdefault((round(float(x), 7), round(float(z), 7)), []).append(float(y))
    thicknesses = []
    for heights in groups.values():
        assert len(heights) == 2, (name, 'unpaired extrusion vertex', heights)
        thicknesses.append(max(heights) - min(heights))
    assert np.allclose(thicknesses, .002, atol=2e-7), (name, 'sheet thickness')
    contacts = np.array(record['attachment_points_gltf_m'])
    assert contacts.shape == (4, 3)
    contact_error = [float(np.linalg.norm(vertices - c, axis=1).min()) for c in contacts]
    assert max(contact_error) < 2e-6, (name, 'flange contact moved', contact_error)
    hardware = {}
    seat_ray_count = 0
    for index, head_name in enumerate(record['hardware_names']):
        assert nodes[head_name]['extras']['role'] == 'separate_flanged_mount_head'
        assert nodes[head_name]['extras']['attachment_index'] == index
        head = scene.geometry[scene.graph[head_name][1]].copy()
        hardware[head_name] = closed_body(head, 2)
        assert np.allclose(head.extents, [.012, .0044, .012], atol=2e-7)
        assert np.allclose(head.bounds[:, [0, 2]].mean(axis=0), contacts[index, [0, 2]], atol=1e-7)
        assert abs(head.bounds[0, 1]) < 1e-8
        for angle in np.linspace(0, 2*np.pi, 16, endpoint=False):
            point = contacts[index, [0, 2]] + .0059*np.array([np.cos(angle), np.sin(angle)])
            hits = vertical_hits(mesh, point)
            assert len(hits) == 2 and np.allclose(hits, [-.002, 0.], atol=2e-7), (name, 'head seat unsupported', index, point, hits)
            seat_ray_count += 1
    # Rays are checked against explicit slot dimensions, independently of the builder helper.
    slot_rays = 0
    for z in (-.135, -.045, .045, .135):
        for x in np.linspace(-.396, .396, 7):
            for dx, dz in ((0, 0), (-.035, 0), (.035, 0), (0, -.006), (0, .006)):
                assert len(vertical_hits(mesh, [x+dx, z+dz])) == 0, (name, 'blocked through-slot', x, z)
                slot_rays += 1
    ligament_rays = 0
    for z in (-.135, -.045, .045, .135):
        for x in np.linspace(-.330, .330, 6):
            hits = vertical_hits(mesh, [x, z])
            assert len(hits) == 2 and np.isclose(np.ptp(hits), .002, atol=2e-7), (name, 'ligament ray', x, z, hits)
            ligament_rays += 1
    center_hits = vertical_hits(mesh, [0., 0.])
    assert len(center_hits) == 2
    target_top = -.054 if name == 'sag' else -.018
    assert np.isclose(center_hits[-1], target_top, atol=2e-7)
    material = attrs.material
    assert material.alphaMode in (None, 'OPAQUE') and material.baseColorFactor[3] == 255
    assert np.isclose(material.roughnessFactor, .75) and np.isclose(material.metallicFactor, .4)
    result.update({
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'exported_vertices_including_uv_normal_seams': exported_vertices,
        'through_holes_from_genus': int((2-mesh.euler_number)//2),
        'bounds_gltf_m': mesh.bounds.tolist(), 'extents_gltf_xyz_m': mesh.extents.tolist(),
        'assembly_bounds_gltf_m': scene.bounds.tolist(), 'scale': [1., 1., 1.],
        'vertical_sheet_thickness_min_max_m': [min(thicknesses), max(thicknesses)],
        'attachment_max_error_m': max(contact_error), 'attachment_points_gltf_m': contacts.tolist(),
        'uv0_range': [float(uv.min()), float(uv.max())], 'minimum_uv_triangle_area': float(uv_areas.min()),
        'zero_area_uv_triangles': 0, 'slot_clearance_rays': slot_rays,
        'ligament_thickness_rays': ligament_rays, 'hardware_seat_rays': seat_ray_count,
        'center_ray_y_m': center_hits.tolist(), 'minimum_y_at_2_99_placement_m': float(mesh.bounds[0, 1]+2.99),
        'hardware_bodies': hardware, 'assembly_body_count': 5,
    })
    return result


def variant_differences(results, manifest):
    def tops(name):
        heights = {}
        for x, y, z in panel_mesh(name).vertices:
            key = (round(float(x), 7), round(float(z), 7))
            heights[key] = max(heights.get(key, -np.inf), float(y))
        return heights

    reference = tops('intact')
    differences = {}
    for name in ('subtlewarp', 'sag'):
        actual = tops(name)
        assert actual.keys() == reference.keys(), (name, 'plan coordinates changed')
        delta = np.array([actual[key] - value for key, value in reference.items()])
        if name == 'sag':
            assert np.isclose(delta.min(), -.036, atol=1e-7) and delta.max() < 1e-7
        else:
            assert delta.min() < -.003 and delta.max() > .003
        assert abs(results[name]['signed_volume_m3'] - results['intact']['signed_volume_m3']) < 1e-9
        differences[name] = {'exported_height_delta_min_max_m': [float(delta.min()), float(delta.max())],
                             'plan_coordinates_unchanged': True}
    intact_mesh = panel_mesh('intact')
    for name in ('torncorner', 'brokenedge'):
        mesh = panel_mesh(name)
        removed_area = (results['intact']['signed_volume_m3'] - results[name]['signed_volume_m3']) / .002
        assert removed_area > .004, (name, 'outline region removal absent')
        assert np.isclose(removed_area, manifest['variants'][name]['removed_projected_area_m2'], atol=2e-7)
        outer = np.array(manifest['variants'][name]['outer_blender_xy_m'])
        original = np.array(manifest['fit']['outer_blender_xy_m'])
        changed = np.linalg.norm(outer - original, axis=1) > .004
        points = (outer[changed] + original[changed]) / 2
        removed_rays = 0
        for x, y in points:
            if len(vertical_hits(intact_mesh, [x, -y])) == 2:
                assert len(vertical_hits(mesh, [x, -y])) == 0, (name, 'notch not open')
                removed_rays += 1
        assert removed_rays >= 15
        assert mesh.bounds[0, 1] < -.030, (name, 'missing bent lip')
        differences[name] = {'removed_projected_material_area_m2': removed_area,
                             'removed_region_clearance_rays': removed_rays,
                             'maximum_notch_depth_m': manifest['variants'][name]['max_outline_notch_m'],
                             'changed_original_outline_arc_m': manifest['variants'][name]['changed_original_outline_arc_m'],
                             'through_holes_unchanged': results[name]['through_holes_from_genus'] == 28}
    return differences


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--intact-only', action='store_true')
    args = parser.parse_args()
    manifest = json.loads((OUT / 'manifest.json').read_text())
    assert manifest['minimum_slot_to_slot_ligament_m'] >= .008
    assert manifest['minimum_slot_to_inner_rim_ligament_m'] >= .008
    names = ['intact'] if args.intact_only else list(manifest['variants'])
    results = {name: verify(name, manifest) for name in names}
    if not args.intact_only:
        assert set(names) == {'intact', 'subtlewarp', 'sag', 'torncorner', 'brokenedge'}
        results['independent_variant_differences'] = variant_differences(results, manifest)
    results['source_provenance'] = {}
    for role in ('source', 'guide'):
        digest = hashlib.sha256((ROOT / manifest[role]).read_bytes()).hexdigest()
        assert digest == manifest[f'{role}_sha256'], (role, 'provenance mismatch')
        results['source_provenance'][f'{role}_sha256'] = digest
    results['limits'] = [
        'No exhaustive 3D triangle intersection certification; builder checks simple nested planar boundaries and paired extrusion.',
        'Thickness is 2 mm vertical extrusion, not an exact normal offset on steep rim or bent variants.',
        'Mount heads are separate closed captive-head solids with flat seats, not threaded fasteners or modeled hidden shanks.',
        'Return UVs use metal-side planar colour-bank projections per edge; stretched sloping rim UVs remain planar.',
        'Neutral GLB material only; generated-image material textures are rebaked separately for parent binding.',
    ]
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    path = EVIDENCE / ('intact-metrics.json' if args.intact_only else 'export-metrics.json')
    path.write_text(json.dumps(results, indent=2) + '\n')
    if not args.intact_only:
        (ROOT / 'art-source/bay-ceiling/fitted-measurements.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
