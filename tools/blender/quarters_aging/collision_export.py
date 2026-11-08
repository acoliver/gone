"""Inspect actual GLB triangles with BVH broad phase and triangle SAT narrow phase."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from triangle_contacts import intersect


def topology(vertices, faces):
    keys = [tuple(np.round(p, 7)) for p in vertices]
    mapping, ids = {}, []
    for p in keys:
        ids.append(mapping.setdefault(p, len(mapping)))
    edges = {}
    for face in faces:
        for a, b in zip(face, np.roll(face, -1)):
            edge = tuple(sorted((ids[a], ids[b])))
            edges[edge] = edges.get(edge, 0) + 1
    boundary = [e for e, count in edges.items() if count == 1]
    graph = {}
    unique = {ids[i]: vertices[i] for i in range(len(ids))}
    for a, b in boundary:
        graph.setdefault(a, []).append(b)
        graph.setdefault(b, []).append(a)
    loops = []
    unbranched = all(len(v) == 2 for v in graph.values())
    remaining = set(graph)
    if unbranched:
        while remaining:
            start = min(remaining)
            group, previous, current = [], None, start
            while True:
                group.append(current)
                remaining.remove(current)
                nxt = next(v for v in graph[current] if v != previous)
                if nxt == start:
                    break
                previous, current = current, nxt
            p = np.asarray([unique[i] for i in group])
            centre = p.mean(0)
            if centre[2] > -.20:
                kind = 'neck'
            elif centre[2] < -.80:
                kind = 'hem' if np.ptp(p[:, 0]) > .25 else 'cuff'
            else:
                kind = 'tear'
            loops.append({'kind': kind, 'vertices': len(group), 'centre_blender_m': centre.tolist()})
    return {'boundary_edges': len(boundary), 'boundary_loops': loops, 'unbranched_boundaries': unbranched,
            'nonmanifold_edges': sum(n > 2 for n in edges.values()),
            'degenerate_edges': sum(a == b for a, b in edges)}


def check(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path.resolve()))
    parts = {}
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH':
            continue
        obj.data.calc_loop_triangles()
        vertices = np.asarray([obj.matrix_world @ v.co for v in obj.data.vertices])
        faces = np.asarray([t.vertices[:] for t in obj.data.loop_triangles])
        tree = BVHTree.FromPolygons(vertices.tolist(), faces.tolist(), all_triangles=True, epsilon=0)
        materials = [obj.data.materials[obj.data.polygons[t.polygon_index].material_index].name for t in obj.data.loop_triangles]
        parts[obj.name] = (vertices, faces, tree, materials)
    fixed = {'Frame', 'Feet', 'Rivets', 'Hanger'}
    result = {'method': 'Exported GLB, BVH candidate overlap then 17-axis triangle/triangle SAT including coplanar overlap; only shared-vertex face adjacency omitted from self checks.',
              'self': {}, 'pairs': {}, 'excluded_unchanged_assembly': {}, 'topology': {}}
    for name, (vertices, faces, tree, materials) in parts.items():
        result['topology'][name] = topology(vertices, faces)
        hits, examples = 0, []
        for i, j in tree.overlap(tree):
            if i >= j:
                continue
            a, b = vertices[faces[i]], vertices[faces[j]]
            if np.any(np.linalg.norm(a[:, None] - b[None, :], axis=2) < 1e-7):
                continue
            if intersect(a, b):
                hits += 1
                if len(examples) < 12:
                    examples.append({'triangles': [i, j], 'centre': ((a.mean(0) + b.mean(0)) / 2).tolist(), 'materials': [materials[i], materials[j]]})
        (result['excluded_unchanged_assembly'] if name in fixed else result['self'])[name] = {'count': hits, 'examples': examples}
    names = sorted(parts)
    for k, name in enumerate(names):
        av, af, at, am = parts[name]
        for other in names[k + 1:]:
            bv, bf, bt, bm = parts[other]
            hits, examples = 0, []
            for i, j in at.overlap(bt):
                a, b = av[af[i]], bv[bf[j]]
                if intersect(a, b):
                    hits += 1
                    if len(examples) < 12:
                        examples.append({'triangles': [i, j], 'centre': ((a.mean(0) + b.mean(0)) / 2).tolist(), 'materials': [am[i], bm[j]]})
            if hits:
                group = 'excluded_unchanged_assembly' if name in fixed and other in fixed else 'pairs'
                result[group][name + '/' + other] = {'count': hits, 'examples': examples}
    result['self_intersections'] = sum(x['count'] for x in result['self'].values())
    result['part_intersections'] = sum(x['count'] for x in result['pairs'].values())
    for name, value in result['topology'].items():
        kinds = [entry['kind'] for entry in value['boundary_loops']]
        intended = name == 'TunicBody' and sorted(kinds) == sorted(['neck', 'hem', 'cuff', 'cuff'] + ['tear'] * 5)
        value['properly_bounded_cloth'] = intended and value['unbranched_boundaries']
        value['pass'] = not value['nonmanifold_edges'] and not value['degenerate_edges'] and (value['boundary_edges'] == 0 or value['properly_bounded_cloth'])
    result['pass'] = result['self_intersections'] == 0 and result['part_intersections'] == 0 and all(v['pass'] for v in result['topology'].values())
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    result = check(args.input)
    args.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k in ['self_intersections', 'part_intersections', 'pass', 'topology']}, indent=2))
