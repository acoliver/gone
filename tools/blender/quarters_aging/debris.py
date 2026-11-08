"""Scatter a small library of source-mesh fragments as one seeded debris mesh."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import recalc


def fragments(source):
    """Use three triangles from the generated/fitted source as flake templates."""
    source.data.calc_loop_triangles()
    triangles = source.data.loop_triangles
    result = []
    for fraction in (.23, .51, .79):
        face = triangles[min(len(triangles) - 1, int(len(triangles) * fraction))]
        p = np.array([source.data.vertices[i].co[:] for i in face.vertices])
        p -= p.mean(0)
        _, _, axes = np.linalg.svd(p, full_matrices=False)
        p = p @ axes.T
        p[:, 2] = 0
        p /= max(np.ptp(p[:, 0]), np.ptp(p[:, 1]), 1e-8)
        result.append(p)
    return result


def scatter(source, config, seed):
    rng = np.random.default_rng(seed)
    templates = fragments(source)
    vertices, faces = [], []
    center = np.array(config['center_blender_m'], dtype=float)
    center[2] = -config['drop_height_m'] if 'drop_height_m' in config else center[2]
    radius = np.array(config['radius_xy_m'])
    # Separated cells prevent random flakes from intersecting one another.
    columns = int(np.ceil(np.sqrt(config['count'])))
    actual = 0
    for j in range(columns):
        for i in range(columns):
            xy = (np.array((i + .5, j + .5)) / columns * 2 - 1) + rng.uniform(-.15, .15, 2) / columns
            r2 = float(xy @ xy)
            if r2 > 1:
                continue
            size = rng.uniform(*config['piece_size_m'])
            angle = rng.uniform(0, 2 * np.pi)
            c, s = np.cos(angle), np.sin(angle)
            points = templates[actual % len(templates)].copy() * size
            points[:, :2] = points[:, :2] @ np.array(((c, s), (-s, c)))
            thickness = config['piece_thickness_m'] + config['heap_height_m'] * (1 - r2) ** 2
            offset = center + np.array((*tuple(xy * radius), config['floor_gap_m']))
            n = len(vertices)
            vertices.extend((points + offset).tolist())
            vertices.extend((points + offset + (0, 0, thickness)).tolist())
            faces.extend([(n, n + 2, n + 1), (n + 3, n + 4, n + 5),
                          (n, n + 1, n + 4, n + 3), (n + 1, n + 2, n + 5, n + 4),
                          (n + 2, n, n + 3, n + 5)])
            actual += 1
    data = bpy.data.meshes.new(config['name'])
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(config['name'], data)
    bpy.context.collection.objects.link(obj)
    mat = bpy.data.materials.get(config['material']) or bpy.data.materials.new(config['material'])
    mat.diffuse_color = (*config['color'], 1)
    mat.use_nodes = True
    mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = (*config['color'], 1)
    mat.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value = 1
    data.materials.append(mat)
    obj['aged_export'] = True
    recalc(obj)
    return {'pieces': actual, 'seed': seed, 'floor_z_m': float(center[2]), 'templates': 3}


def main():
    from build import run
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--params', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    run(args.source, json.loads(args.params.read_text()), args.output, stages={'debris'})


if __name__ == '__main__':
    main()
