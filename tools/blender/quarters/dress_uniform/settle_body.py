"""Settle already sewn stitches as shared vertices, removing stitch collision conflicts."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulate import HERE, SCRATCH, cloth, measure, mesh_object
from sleeves import weld_data


def main(args):
    source = json.loads((SCRATCH / f'{args.source}-body.json').read_text())
    bpy.ops.wm.open_mainfile(filepath=str(SCRATCH / f'{args.source}-body.blend'))
    original = bpy.data.objects['BakedBodyPattern']
    faces = [tuple(p.vertices) for p in original.data.polygons]
    vertices, stitched_faces, mapping = weld_data(source['positions'], faces, source['metadata']['seams'])
    obj = mesh_object('JoinedBodyForSettling', vertices, stitched_faces)
    pins = obj.vertex_groups.new(name='HangerPins')
    pins.add(sorted({mapping[i] for i in source['metadata']['pins']}), 1, 'REPLACE')
    mod = cloth(obj, args)
    deps = bpy.context.evaluated_depsgraph_get()
    for frame in range(1, args.frames + 1):
        bpy.context.scene.frame_set(frame)
        positions = np.array([tuple(v.co) for v in obj.evaluated_get(deps).data.vertices])
        if frame == args.frames - 5:
            previous = positions.copy()
        if frame % 20 == 0:
            print('joined body frame', frame, flush=True)
    expanded = np.array([positions[mapping[i]] for i in range(len(source['positions']))])
    old = np.array([previous[mapping[i]] for i in range(len(source['positions']))])
    metrics = measure(expanded, source['metadata'], old)
    print(json.dumps(metrics), flush=True)
    for i, vertex in enumerate(original.data.vertices):
        vertex.co = expanded[i]
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.context.scene.frame_set(1)
    (SCRATCH / f'{args.trial}-body.json').write_text(json.dumps({'metadata': source['metadata'], 'metrics': metrics, 'positions': expanded.tolist()}, indent=2))
    bpy.ops.wm.save_as_mainfile(filepath=str(SCRATCH / f'{args.trial}-body.blend'))
    trials = json.loads((HERE / 'cloth-trials.json').read_text())
    trials['body'].append({'trial': args.trial, 'settings': vars(args), 'metrics': metrics, 'method': 'Sewing springs from source trial joined into shared stitches before a second gravity settling pass; shoulder pins only, self-collision enabled.'})
    (HERE / 'cloth-trials.json').write_text(json.dumps(trials, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default='body-b')
    parser.add_argument('--trial', default='body-f')
    parser.add_argument('--frames', type=int, default=240)
    parser.add_argument('--quality', type=int, default=25)
    parser.add_argument('--bending', type=float, default=5)
    parser.add_argument('--sewing', type=float, default=10)
    main(parser.parse_args(sys.argv[sys.argv.index('--') + 1:]))
