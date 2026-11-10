"""Sew sleeve caps to the settled body and bake the continuous garment surface."""
import argparse
import json
import math
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulate import HERE, ROOT, SCRATCH, activate, cloth, mesh_object


def weld_data(vertices, faces, pairs):
    parent = list(range(len(vertices)))
    def root(i):
        while parent[i] != i:
            i = parent[i]
        return i
    for a, b in pairs:
        parent[root(b)] = root(a)
    groups = {}
    for i in range(len(vertices)):
        groups.setdefault(root(i), []).append(i)
    mapping, result = {}, []
    for group in groups.values():
        n = len(result)
        result.append(np.mean([vertices[i] for i in group], axis=0).tolist())
        for i in group:
            mapping[i] = n
    return result, [tuple(mapping[i] for i in f) for f in faces], mapping


def main(args):
    source = json.loads((SCRATCH / f'{args.body}-body.json').read_text())
    bpy.ops.wm.open_mainfile(filepath=str(SCRATCH / f'{args.body}-body.blend'))
    original = bpy.data.objects['BakedBodyPattern']
    source_faces = [tuple(p.vertices) for p in original.data.polygons]
    corner_uv = [tuple(v.uv) for v in original.data.uv_layers.active.data]
    vertices, faces, mapping = weld_data(source['positions'], source_faces, source['metadata']['seams'])
    body_count = len(vertices)
    body_faces = len(faces)
    seams, sleeves = [], {}
    for name, sign, column in [('Sleeve_L', 1, 28), ('Sleeve_R', -1, 0)]:
        front = [mapping[row[column]] for row in source['metadata']['grids'][0]]
        back = [mapping[row[column]] for row in source['metadata']['grids'][1]]
        under = max(j for j in range(31) if front[j] == back[j] and j < 29)
        loop = front[under:] + list(reversed(back[under + 1:-1]))
        n = len(loop)
        top = np.array([vertices[i] for i in loop])
        center = top.mean(0)
        rings = []
        first_index, first_face = len(vertices), len(faces)
        for k in range(22):
            t = k / 21
            # Sleeve cap at the armhole, then straight gravity-aligned tapered tube.
            ring = []
            for j, p in enumerate(top):
                theta = 2 * math.pi * j / n
                # Top loop starts at the armpit, travels up the front and down the back.
                rx = .060 * (1 - t) + .042 * t
                ry = .053 * (1 - t) + .040 * t
                target = np.array((sign * (.326 + .013 * t) - sign * rx * math.cos(theta), -.008 - .027 * t - ry * math.sin(theta), -.425 - .44 * t))
                cap = min(1, t * 5)
                pos = (1 - cap) * (p + np.array((sign * .002, 0, 0))) + cap * target
                ring.append(len(vertices))
                vertices.append(pos.tolist())
            rings.append(ring)
        for k in range(21):
            for j in range(n):
                q = (rings[k][j], rings[k][(j + 1) % n], rings[k + 1][(j + 1) % n], rings[k + 1][j])
                if sign < 0:
                    q = tuple(reversed(q))
                faces.append(q)
                u0 = 1.1 if sign > 0 else 1.7
                coords = [(u0 + .45 * j / n, k / 21), (u0 + .45 * (j + 1) / n, k / 21), (u0 + .45 * (j + 1) / n, (k + 1) / 21), (u0 + .45 * j / n, (k + 1) / 21)]
                corner_uv.extend(list(reversed(coords)) if sign < 0 else coords)
        seams.extend(zip(loop, rings[0]))
        sleeves[name] = {'start_vertex': first_index, 'end_vertex': len(vertices), 'start_face': first_face, 'end_face': len(faces), 'armhole': loop, 'cap': rings[0], 'cuff': rings[-1]}
    original.hide_render = True
    original.hide_viewport = True
    obj = mesh_object('SleevedPattern', vertices, faces, seams)
    uv = obj.data.uv_layers.new(name='FlatPattern')
    for i, point in enumerate(corner_uv):
        uv.data[i].uv = point
    pins = obj.vertex_groups.new(name='HangerPins')
    pins.add(list(range(body_count)), 1, 'REPLACE')
    positions = np.asarray(vertices)
    sewing_gap = float(max(np.linalg.norm(positions[a] - positions[b]) for a, b in seams))
    print('pre-stitch cap placement gap', sewing_gap, flush=True)
    stitched_v, stitched_f, stitch_map = weld_data(positions, faces, seams)
    obj.modifiers.clear()
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.context.scene.frame_set(1)
    obj = mesh_object('SleevedPattern', stitched_v, stitched_f)
    uv = obj.data.uv_layers.new(name='FlatPattern')
    for i, point in enumerate(corner_uv):
        uv.data[i].uv = point
    pins = obj.vertex_groups.new(name='HangerPins')
    pins.add(list(range(body_count)), 1, 'REPLACE')
    mod = cloth(obj, args)
    bpy.context.scene.gravity = (0, 0, -9.81)
    deps = bpy.context.evaluated_depsgraph_get()
    previous = None
    for frame in range(1, args.frames + 1):
        bpy.context.scene.frame_set(frame)
        evaluated = obj.evaluated_get(deps)
        positions = np.array([tuple(v.co) for v in evaluated.data.vertices])
        if frame == args.frames - 5:
            previous = positions.copy()
        if frame % 10 == 0:
            print('sleeve frame', frame, flush=True)
    metrics = {'pre_stitch_cap_placement_gap_m': sewing_gap, 'stitched_cap_gap_m': 0.0, 'last_five_frames_displacement_m': float(np.linalg.norm(positions - previous, axis=1).max())}
    print(json.dumps(metrics), flush=True)
    result_v, result_f = positions.tolist(), stitched_f
    baked = mesh_object('TunicBody', result_v, result_f)
    uv = baked.data.uv_layers.new(name='FlatPattern')
    for i, point in enumerate(corner_uv):
        uv.data[i].uv = point
    baked['export'] = True
    baked['body_faces'] = body_faces
    baked['sleeve_faces'] = json.dumps({n: [s['start_face'], s['end_face']] for n, s in sleeves.items()})
    # Baked springs become stitched shared vertices, not loose export edges.
    obj.hide_render = True
    obj.hide_viewport = True
    obj.modifiers.clear()
    for i, v in enumerate(obj.data.vertices):
        v.co = positions[i]
    obj['export'] = False
    (SCRATCH / f'{args.trial}-sleeves.json').write_text(json.dumps({'metrics': metrics, 'sleeves': sleeves, 'body_faces': body_faces}, indent=2))
    bpy.context.scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(SCRATCH / f'{args.trial}-sleeves.blend'))
    trials = json.loads((HERE / 'cloth-trials.json').read_text())
    trials['sleeves'].append({'trial': args.trial, 'settings': {**vars(args), **json.loads(obj['cloth_settings'])}, 'metrics': metrics, 'method': 'Sleeve cap placement within 2 mm, joined into shared armhole stitches before gravity settling. Body surface pinned, sleeves free with self-collision.'})
    (HERE / 'cloth-trials.json').write_text(json.dumps(trials, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--body', default='body-p')
    parser.add_argument('--trial', default='sleeve-h')
    parser.add_argument('--frames', type=int, default=480)
    parser.add_argument('--quality', type=int, default=30)
    parser.add_argument('--bending', type=float, default=5)
    parser.add_argument('--sewing', type=float, default=10)
    main(parser.parse_args(sys.argv[sys.argv.index('--') + 1:]))
