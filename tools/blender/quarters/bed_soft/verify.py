"""Measure the exported GLBs, including frame contacts in the game's +Y-up frame."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
import trimesh
from shapely.geometry import Polygon
from shapely.strtree import STRtree

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.append(str(HERE.parents[1] / 'quarters_aging'))
from triangle_contacts import intersect

PARTS = ('Mattress', 'Quilt', 'Pillow_L', 'Pillow_R')


def crossings(a, b):
    tree = b.triangles_tree
    count = 0
    for triangle in a.triangles:
        bounds = np.r_[triangle.min(0) - 1e-8, triangle.max(0) + 1e-8]
        for other in tree.intersection(bounds):
            if intersect(triangle, b.triangles[other]):
                count += 1
    return count


def support_gap(part, support):
    triangles = support.triangles[support.face_normals[:, 1] > 1e-4]
    polygons = [Polygon(t[:, [0, 2]]) for t in triangles]
    tree = STRtree(polygons)
    planes = [np.linalg.solve(np.c_[t[:, [0, 2]], np.ones(3)], t[:, 1]) for t in triangles]
    gaps = []
    for triangle in part.triangles[np.abs(part.face_normals[:, 1]) > 1e-4]:
        polygon = Polygon(triangle[:, [0, 2]])
        plane = np.linalg.solve(np.c_[triangle[:, [0, 2]], np.ones(3)], triangle[:, 1])
        for i in tree.query(polygon, predicate='intersects'):
            overlap = polygon.intersection(polygons[i])
            if overlap.geom_type != 'Polygon' or overlap.area < 1e-12:
                continue
            points = np.c_[np.asarray(overlap.exterior.coords), np.ones(len(overlap.exterior.coords))]
            gaps.append(float((points @ (plane - planes[i])).min()))
    if not gaps:
        raise ValueError('No projected support overlap')
    return min(gaps)


def volume_gate(ratio):
    return bool(.25 <= ratio <= .40)


def axes_gate(mattress, pillows):
    return bool(mattress.extents[2] > mattress.extents[0] > mattress.extents[1]
                and .49 < mattress.bounds[0, 1] < .53 and pillows.centroid[2] < -.35)


def load(path):
    scene = trimesh.load(path, force='scene')
    result = {}
    for node in scene.graph.nodes_geometry:
        transform, geometry = scene.graph[node]
        mesh = scene.geometry[geometry].copy()
        mesh.apply_transform(transform)
        # glTF splits a multi-material Blender object into primitive child nodes.
        ancestors = [node]
        current = node
        while current in scene.graph.transforms.parents:
            current = scene.graph.transforms.parents[current]
            ancestors.append(current)
        name = next((part for part in PARTS if part in ancestors), node)
        result.setdefault(name, []).append(mesh)
    return scene, {name: trimesh.util.concatenate(meshes) for name, meshes in result.items()}


def state_report(state, path, repeat):
    scene, meshes = load(path)
    _, frame = load(ROOT / 'assets/props/quarters/bed.glb')
    bed = trimesh.util.concatenate(tuple(frame.values()))
    counts = {name: crossings(mesh, bed) for name, mesh in sorted(meshes.items())}
    supports = {'Mattress': frame['MattressPlatform'], 'Quilt': meshes['Mattress'],
                'Pillow_L': meshes['Mattress'], 'Pillow_R': meshes['Mattress']}
    gaps = {name: support_gap(meshes[name], support) for name, support in supports.items()}
    for name, mesh in meshes.items():
        if name.endswith(('_Platform', '_Foot')):
            gaps[name] = support_gap(mesh, frame['MattressPlatform'])
        elif name.endswith('_Floor'):
            gaps[name] = float(mesh.bounds[0, 1])
    pairs = {f'{a}/{b}': crossings(meshes[a], meshes[b]) for i, a in enumerate(PARTS) for b in PARTS[i + 1:]}
    pillows = trimesh.util.concatenate([meshes['Pillow_L'], meshes['Pillow_R']])
    tris = sum(len(mesh.faces) for mesh in meshes.values())
    origins = {name: scene.graph[name][0][:3, 3].tolist() for name in PARTS}
    report = {'triangles': tris, 'bounds_gltf_m': scene.bounds.tolist(),
              'frame_crossings': counts, 'soft_part_crossings': pairs,
              'support_gaps_m': gaps, 'origins_gltf_m': origins,
              'byte_identical_reexport': path.read_bytes() == repeat.read_bytes(),
              'axes_y_up_front_z': axes_gate(meshes['Mattress'], pillows),
              'part_bounds_gltf_m': {name: mesh.bounds.tolist() for name, mesh in meshes.items()}}
    report['pass'] = bool(tris <= 15000 and not sum(counts.values()) and not sum(pairs.values())
                          and all(-1e-5 <= gap <= .003 for gap in gaps.values())
                          and report['byte_identical_reexport'] and report['axes_y_up_front_z']
                          and all(np.allclose(origin, [0, 0, 0], atol=1e-8) for origin in origins.values()))
    return report, meshes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--remembered-repeat', type=Path, default=ROOT / 'tmp/bed_soft/remembered-repeat.glb')
    parser.add_argument('--aged-repeat', type=Path, default=ROOT / 'tmp/bed_soft/aged-repeat.glb')
    args = parser.parse_args()
    result = {}
    result['remembered'], clean = state_report('remembered', ROOT / 'assets/props/quarters/bed_soft.glb', args.remembered_repeat)
    result['aged'], aged = state_report('aged', ROOT / 'assets/props/quarters/bed_soft_aged.glb', args.aged_repeat)
    # The foam material's closed plate primitives measure actual retained filling,
    # rather than the volume of an open, torn cover or its bounding box.
    scene = trimesh.load(ROOT / 'assets/props/quarters/bed_soft_aged.glb', force='scene')
    foam = []
    for node in scene.graph.nodes_geometry:
        matrix, key = scene.graph[node]
        mesh = scene.geometry[key].copy()
        if getattr(mesh.visual.material, 'name', None) == 'Foam':
            mesh.apply_transform(matrix)
            mesh.merge_vertices(merge_tex=True, merge_norm=True)
            foam.append(mesh)
    if not foam:
        raise ValueError('No exported Foam material primitives')
    crust = trimesh.util.concatenate(foam)
    mattress = clean['Mattress'].copy()
    mattress.merge_vertices(merge_tex=True, merge_norm=True)
    aged_mattress = aged['Mattress'].copy()
    aged_mattress.merge_vertices(merge_tex=True, merge_norm=True)
    ratio = abs(aged_mattress.volume / mattress.volume)
    foam_ratio = abs(crust.volume / mattress.volume)
    result['mattress_volume'] = {'remembered_m3': abs(float(mattress.volume)),
                                 'aged_crust_and_cover_m3': abs(float(aged_mattress.volume)),
                                 'aged_foam_crust_m3': abs(float(crust.volume)),
                                 'foam_ratio': float(foam_ratio),
                                 'ratio': float(ratio), 'pass': volume_gate(ratio) and volume_gate(foam_ratio),
                                 'remembered_watertight': bool(mattress.is_watertight),
                                 'aged_mattress_watertight': bool(aged_mattress.is_watertight),
                                 'aged_crust_watertight': bool(crust.is_watertight)}
    result['pass'] = bool(all(result[state]['pass'] for state in ('remembered', 'aged'))
                          and result['mattress_volume']['pass'] and mattress.is_watertight
                          and aged_mattress.is_watertight and crust.is_watertight)
    (HERE / 'verify.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2), flush=True)
    if not result['pass']:
        raise SystemExit('Bed soft-goods gates failed')


if __name__ == '__main__':
    main()
