"""Audit native-renderer readback of the installed production seat family.

Run after tools/run_seat_production_tests.gd, using the existing art Python env.
No source assets are generated or modified.
"""
import json
from pathlib import Path
import numpy as np
import trimesh
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'tmp/verify-stasis-wiring/seat-production'


def mesh_from(row):
    meshes = []
    for surface in row['surfaces']:
        vertices = np.asarray(surface['vertices'])
        indices = np.asarray(surface['indices'], dtype=int)
        if not len(indices):
            indices = np.arange(len(vertices))
        meshes.append(trimesh.Trimesh(vertices, indices.reshape(-1, 3), process=False))
    return trimesh.util.concatenate(meshes)


def placed(source, pose):
    mesh = source.copy()
    mesh.apply_transform(pose)
    return mesh


def penetration(rail, panel):
    edges = rail.vertices[rail.edges_unique]
    vectors = edges[:, 1] - edges[:, 0]
    lengths = np.linalg.norm(vectors, axis=1)
    valid = lengths > 1e-8
    edges, vectors, lengths = edges[valid], vectors[valid], lengths[valid]
    locations, rays, _ = panel.ray.intersects_location(
        edges[:, 0], vectors / lengths[:, None], multiple_hits=True)
    distance = np.linalg.norm(locations - edges[rays, 0], axis=1)
    # Use the measured float32 bearing plane, not its rounded decimal label.
    bearing = rail.bounds[1, 1]
    intersections = np.sum((distance > 1e-7) & (distance < lengths[rays] - 1e-7)
                           & (locations[:, 1] < bearing - 1e-7))
    panel_under = panel.vertices[panel.vertices[:, 1] < bearing - 1e-7]
    rail_under = rail.vertices[rail.vertices[:, 1] < bearing - 1e-7]
    contained = np.sum(rail.contains(panel_under)) + np.sum(panel.contains(rail_under))
    return int(intersections), int(contained)


def normal_error(surface, source_surface):
    points = np.asarray(surface['vertices'])
    normals = np.asarray(surface['normals'])
    source_points = np.asarray(source_surface['vertices'])
    source_normals = np.asarray(source_surface['normals'])
    faces = np.asarray(source_surface['indices']).reshape(-1, 3)
    source = trimesh.Trimesh(source_points, faces, process=False)
    tree = cKDTree(source_points)
    worst = 0.0
    # Newly cut physical end caps intentionally have hard +/-X normals.
    for point, normal in zip(points, normals):
        if abs(normal[0]) >= .99999:
            continue
        vertices = tree.query_ball_point(point, 1e-7)
        if vertices:
            expected = source_normals[vertices]
        else:
            ids = trimesh.proximity.nearby_faces(source, [point])[0]
            triangles = source.triangles[ids]
            closest = trimesh.triangles.closest_point(triangles, np.tile(point, (len(ids), 1)))
            on_surface = np.linalg.norm(closest - point, axis=1) < 1e-7
            assert np.any(on_surface), 'clipped normal belongs to a source face'
            weights = trimesh.triangles.points_to_barycentric(triangles[on_surface], closest[on_surface])
            expected = np.einsum('ij,ijk->ik', weights, source_normals[faces[np.asarray(ids)[on_surface]]])
        expected = expected / np.linalg.norm(expected, axis=1)[:, None]
        worst = max(worst, float(np.min(np.max(np.abs(expected - normal), axis=1))))
    return worst


def main():
    data = json.loads((OUT / 'installed-meshes.json').read_text())
    meshes = {key: mesh_from(row) for key, row in data['meshes'].items()}
    source_rows = [row for row in data['instances'] if row['path'].startswith('/Source_full/')]
    assert len(source_rows) == 1
    source_id = source_rows[0]['mesh']
    source = meshes[source_id]
    source_surface = data['meshes'][source_id]['surfaces'][0]
    source_uv = np.asarray(source_surface['uv'])
    source_indices = np.asarray(source_surface['indices']).reshape(-1, 3)
    variants = {}
    for key, row in data['meshes'].items():
        if not row['shared_material'] or row['resource']:
            continue
        mesh = meshes[key].copy()
        mesh.merge_vertices(digits_vertex=8)
        assert mesh.is_watertight, (key, 'open cut', mesh.bounds.tolist())
        assert mesh.is_winding_consistent and mesh.volume < 0, (key, 'Godot clockwise winding')
        surface = row['surfaces'][0]
        vertices = np.asarray(surface['vertices'])
        uv = np.asarray(surface['uv'])
        closest, distance, faces = trimesh.proximity.closest_point(source, vertices)
        assert distance.max() < 1e-7, (key, distance.max())
        barycentric = trimesh.triangles.points_to_barycentric(source.triangles[faces], closest)
        expected_uv = np.einsum('ij,ijk->ik', barycentric, source_uv[source_indices[faces]])
        uv_error = float(np.max(np.abs(expected_uv - uv)))
        assert uv_error < 1e-6, (key, 'UV stretched', uv_error)
        # Test the void, the top skin, and real punched holes in every full span.
        if mesh.bounds[0, 0] < 0 < mesh.bounds[1, 0]:
            inside = mesh.copy()
            inside.invert()  # trimesh expects anticlockwise outward faces.
            np.testing.assert_array_equal(inside.contains([[0, -.009, 0], [0, -.00125, 0]]), [False, True])
            if mesh.bounds[0, 0] < -.36 and mesh.bounds[1, 0] > .36:
                np.testing.assert_array_equal(inside.contains([[-.351, -.008, .01975], [.351, -.008, -.01975]]), [False, False])
        part = 'left' if mesh.bounds[1, 0] < 0 else 'right' if mesh.bounds[0, 0] > 0 else 'full'
        template_id = next(instance['mesh'] for instance in data['instances'] if instance['path'].startswith('/Source_' + part + '/'))
        normal_max_error = normal_error(surface, data['meshes'][template_id]['surfaces'][0])
        assert normal_max_error < 1e-4, (key, 'source normal interpolation', normal_max_error)
        variants[key] = {'bounds_m': mesh.bounds.tolist(), 'watertight': True,
                         'winding_consistent': True, 'metal_volume_m3': float(-mesh.volume),
                         'source_surface_max_distance_m': float(distance.max()), 'source_uv_max_error': uv_error,
                         'source_normal_max_error': normal_max_error}
    assert len(variants) == data['cache_size'], (len(variants), data['cache_size'])
    panels = [row for row in data['instances'] if '/Panel_' in row['path']]
    rails = [row for row in data['instances'] if '/PanelSupportLedgersCross/' in row['path'] or '/BrokenEdgeFrameRail/' in row['path']]
    assert len(panels) == 111 and len(rails) == 132
    assert not any(np.allclose(np.array(row['pose'])[:3, 3], [-.6, 2.988, -.6], atol=1e-6)
                   for row in rails if '/BrokenEdgeFrameRail/' not in row['path'])
    comparisons = 0
    edge_hits = 0
    inside_vertices = 0
    checked = {}
    for rail_row in rails:
        rail = placed(meshes[rail_row['mesh']], rail_row['pose'])
        rail.invert()
        for panel_row in panels:
            panel = placed(meshes[panel_row['mesh']], panel_row['pose'])
            if not np.all(np.minimum(rail.bounds[1], panel.bounds[1]) - np.maximum(rail.bounds[0], panel.bounds[0]) > 1e-8):
                continue
            comparisons += 1
            relative = np.array(panel_row['pose'])[:3, 3] - np.array(rail_row['pose'])[:3, 3]
            key = (rail_row['mesh'], panel_row['mesh'], tuple(np.round(relative, 5)))
            if key not in checked:
                panel.invert()
                checked[key] = penetration(rail, panel)
            hits, contained = checked[key]
            assert hits == 0 and contained == 0, (rail_row['path'], panel_row['path'], relative, hits, contained)
            edge_hits += hits
            inside_vertices += contained
    assert comparisons >= 200
    report = {'installed_full_spans': 130, 'retained_matched_ends': 2, 'cache_variants': data['cache_size'],
              'source_clipped_meshes': variants, 'actual_rail_panel_candidate_pairs': comparisons,
              'distinct_relative_mesh_pairs_tested': len(checked), 'actual_edge_intersections_below_bearing': edge_hits,
              'actual_contained_vertices_below_bearing': inside_vertices,
              'occupancy': {'panels': 111, 'service_cassettes': 8, 'empty_cell': [4, 4], 'occupied_total': 119},
              'failure_bay_origin_m': [-.6, 2.988, -.6], 'source_assets_modified': False}
    (OUT / 'mesh-checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f"SEAT_PRODUCTION_MESH_PASS variants={len(variants)} installed_seats={len(rails)} panel_pairs={comparisons} distinct_pairs={len(checked)} rim_edge_hits={edge_hits} contained_vertices={inside_vertices}")


if __name__ == '__main__':
    main()
