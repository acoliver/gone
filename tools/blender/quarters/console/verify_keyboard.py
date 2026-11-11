"""Measure the exported keyboard against the exported deck, housing and screen."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE.parent / 'wardrobe'))
sys.path.insert(0, str(ROOT / 'tools/blender/quarters_aging'))
from verify_common import uv_report
from triangle_contacts import intersect


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--reexport', type=Path, default=ROOT / 'tmp/issue129-keyboard/keyboard-repeat.glb')
    args = parser.parse_args()
    scene = trimesh.load(ROOT / 'assets/props/quarters/console.glb', force='scene')
    source = trimesh.load(ROOT / 'assets/props/terminal/keyboard.glb', force='scene')
    keyboard = trimesh.load(ROOT / 'assets/props/quarters/console_keyboard.glb', force='scene')
    transform, geometry = keyboard.graph['Keyboard']
    mesh = keyboard.geometry[geometry]
    original = source.geometry[source.graph['Keyboard'][1]]
    assert np.array_equal(mesh.triangles, original.triangles)
    assert np.array_equal(mesh.visual.uv[mesh.faces], original.visual.uv[original.faces])
    assert len(mesh.faces) == 28998 and len(mesh.faces) <= 30000
    assert (ROOT / 'assets/props/quarters/console_keyboard.glb').read_bytes() == args.reexport.read_bytes()
    world = mesh.copy()
    world.apply_transform(transform)
    deck, geometry = scene.graph['ControlPanel']
    deck_local = trimesh.transform_points(world.vertices, np.linalg.inv(deck))
    size = scene.geometry[geometry].extents
    margins = dict(front=float(size[2]/2-deck_local[:, 2].max()),
                   rear=float(deck_local[:, 2].min()+size[2]/2),
                   side=float(size[0]/2-np.abs(deck_local[:, 0]).max()),
                   minimum_normal_gap=float(deck_local[:, 1].min()-size[1]/2))
    assert abs(margins['front']-.010) < 1e-6
    assert .00049 < margins['minimum_normal_gap'] < .00051
    assert min(margins.values()) > 0
    console = {}
    for name in scene.graph.nodes_geometry:
        frame, geometry = scene.graph[name]
        part = scene.geometry[geometry].copy()
        part.apply_transform(frame)
        console[name] = part
    combined = trimesh.util.concatenate(list(console.values()))
    bounds = np.column_stack([combined.triangles.min(1), combined.triangles.max(1)])
    tree = trimesh.util.bounds_tree(bounds)
    crossings = 0
    for triangle in world.triangles:
        box = np.r_[triangle.min(0)-1e-9, triangle.max(0)+1e-9]
        crossings += sum(intersect(triangle, combined.triangles[i]) for i in tree.intersection(box))
    assert crossings == 0, crossings
    old = trimesh.load(args.baseline / 'assets/props/quarters/console.glb', force='scene')
    unchanged = []
    for name in scene.graph.nodes_geometry:
        new_frame, new_geometry = scene.graph[name]
        old_frame, old_geometry = old.graph[name]
        np.testing.assert_array_equal(new_frame, old_frame)
        new_points = np.unique(scene.geometry[new_geometry].vertices, axis=0)
        old_points = np.unique(old.geometry[old_geometry].vertices, axis=0)
        np.testing.assert_array_equal(new_points, old_points)
        unchanged.append(name)
    distances = {}
    for name in ['Display', 'BezelBottom', 'ArmouredHousing']:
        _, distance, _ = trimesh.proximity.closest_point(console[name], world.vertices)
        distances[name] = float(distance.min())
    uv = uv_report({'Keyboard': mesh})
    # The retained keyboard has its own established projected key-top UV density.
    # Every UV triangle is identical to power room; no console UV gate is changed.
    assert uv['out_of_unit_square_coordinates'] == 0
    source_uv = uv_report({'Keyboard': original})
    assert uv == source_uv, 'Reused keyboard UV metrics must equal the power-room source'
    underside = world.copy()
    underside.apply_transform(np.linalg.inv(deck))
    origins = np.array([[x, -.1, z] for x in (-.22, 0, .22) for z in (-.04, .02, .08)])
    points, ray_ids, _ = underside.ray.intersects_location(origins, np.tile([0, 1, 0], (9, 1)), multiple_hits=False)
    assert len(ray_ids) == 9, 'Every underside support ray must hit'
    gaps = points[:, 1] - .009
    assert gaps.min() > 0 and gaps.max() < .001, 'Underside must sit within 1 mm of the panel'
    report = dict(physical_size_before_placement_m=(original.extents*.6600278615951538).tolist(),
                  console_gltf_bounds_m=world.bounds.tolist(),
                  deck_local_center_gltf_m=((deck_local.min(0)+deck_local.max(0))/2).tolist(),
                  deck_local_bounds_gltf_m=[deck_local.min(0).tolist(), deck_local.max(0).tolist()],
                  margins_m=margins, mesh_clearance_m=distances, intersections=crossings,
                  underside_support_gaps_m=gaps.tolist(),
                  unchanged_console_parts=sorted(unchanged), triangles=len(mesh.faces),
                  triangle_limit=30000, reused_triangle_and_uv_corners_identical=True,
                  UV=uv, source_UV=source_uv, UV_unchanged=True, axis_contract='Blender +Z up / -Y front exported +Y up / +Z front', passed=True)
    args.report.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
