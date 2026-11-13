"""#130: correct the source tip fold, retain the generated relief, and thin the medal."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from tunic_details import points
from reduced_clearance import crossing_pairs
sys.path.insert(0, str(HERE / 'medal_v3'))
from export4 import export


def refine(source, original, output):
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(original / 'medal-fitted.blend'))
    original_high = points(bpy.data.objects['Body_High'])
    bpy.ops.wm.open_mainfile(filepath=str(source / 'medal-fitted.blend'))
    high, low = [bpy.data.objects['Body_' + kind] for kind in ['High', 'Low']]
    before = points(high)
    assert before.shape == original_high.shape
    corrected = before.copy()
    # tex2's height transfer applied a front depth to the returning tip skin.
    # Restore that skin's pre-transfer depth instead of smoothing over the fold.
    tip = (before[:, 2] > .0137) & (abs(before[:, 0]) < .001)
    corrected[tip, 1] = original_high[tip, 1]
    # Reduction of the folded high already changed the tip's vertex ordering.
    # Correct the evaluated source before QEM; transferring a displacement onto
    # that invalid low leaves folded triangles even after the high is repaired.
    import shutil
    shutil.copyfile(source / 'target-surface.npz', output / 'target-surface.npz')
    builder = HERE / 'medal_v3/texture/build_pass2.py'
    text = builder.read_text().split('# The high keeps')[0]
    text = text.replace("OUT=ROOT/'tmp/issue130-v3/tex2/geom'", 'OUT=Path(' + repr(str(output)) + ')')
    text = text.replace('    for vertex,point in zip(mesh.vertices,q/1000):',
                        '''    tip=(original[:,2]>13.7)&(abs(original[:,0])<1.)
    q[tip,1]=original[tip,1]
    for vertex,point in zip(mesh.vertices,q/1000):''')
    import types
    projection_path = HERE / 'medal_v3/projection.py'
    projection = types.ModuleType('projection')
    projection.__file__ = str(projection_path)
    projection_text = projection_path.read_text().replace("ROOT/'tmp/issue130-v3/fit1'", repr(str(original)))
    projection_text = projection_text.replace('OUT=' + repr(str(original)), 'OUT=Path(' + repr(str(original)) + ')')
    exec(compile(projection_text, str(projection_path), 'exec'), projection.__dict__)
    sys.modules['projection'] = projection
    namespace = {'__file__': str(builder), '__name__': 'source_reduction'}
    exec(compile(text, str(builder), 'exec'), namespace)
    high = bpy.data.objects['Body_High']
    for vertex, point in zip(high.data.vertices, corrected):
        vertex.co = point
    high.data.update()
    low = namespace['evaluate_low']('Body')
    reduction = namespace['reduce_surface'](low, 5400, .12)
    low_points = points(low)
    with bpy.data.libraries.load(str(source / 'medal-fitted.blend'), link=False) as (_, dest):
        dest.objects = ['Loop_Low', 'Bar_Low']
    for obj, name in zip(dest.objects, ['Loop_Low', 'Bar_Low']):
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
        obj.name = name
        bpy.context.collection.objects.link(obj)
    namespace['unwrap']([bpy.data.objects[p + '_Low'] for p in ['Body', 'Loop', 'Bar']])
    # Fair only the central apex along its face normal, preserving every X/Z.
    radius = np.linalg.norm(corrected[:, [0, 2]], axis=1)
    apex = (radius < .0012) & (corrected[:, 1] < -.003)
    edges = np.array([e.vertices[:] for e in high.data.edges])
    edges = np.vstack([edges, edges[:, ::-1]])
    degree = np.bincount(edges[:, 0], minlength=len(corrected))
    for _ in range(12):
        mean = np.zeros(len(corrected))
        np.add.at(mean, edges[:, 0], corrected[edges[:, 1], 1])
        weight = .45 * np.maximum(0, 1 - (radius / .0012)**2)**2
        corrected[apex, 1] += weight[apex] * (mean[apex] / degree[apex] - corrected[apex, 1])
    scale = .0036 / np.ptp(low_points[:, 1])
    report = dict(depth_scale=scale, tip_restored_high_vertices=int(tip.sum()),
                  apex_faired_vertices=int(apex.sum()), apex_radius_m=.0012,
                  cause='tex2 front-height transfer folded the returning skin at the upper star tip; pre-transfer source depth restored locally.')
    for obj, positions in [(high, corrected), (low, low_points)]:
        positions[:, 1] *= scale
        for vertex, point in zip(obj.data.vertices, positions):
            vertex.co = point
        obj.data.update()
        pairs = crossing_pairs(obj)
        report[obj.name] = dict(crossings=len(pairs), depth_m=float(np.ptp(positions[:, 1])))
        print(obj.name, report[obj.name], flush=True)
        if pairs:
            obj.data.calc_loop_triangles()
            for a, b in pairs[:6]:
                print('RESIDUAL', points(obj)[list(obj.data.loop_triangles[a].vertices)]*1000, points(obj)[list(obj.data.loop_triangles[b].vertices)]*1000, flush=True)
        assert not pairs, (obj.name, pairs[:5])
    # Keep the generated ring shape, thinning its face-normal extent with the body.
    # Its back must not protrude behind the plate's support datum.
    back = max(v.co.y for v in low.data.vertices)
    ring_back = max(v.co.y for v in bpy.data.objects['Loop_Low'].data.vertices) * scale
    ring_base = min(v.co.z for v in bpy.data.objects['Loop_Low'].data.vertices)
    for kind in ['High', 'Low']:
        for vertex in bpy.data.objects['Loop_' + kind].data.vertices:
            vertex.co.x *= scale
            vertex.co.y = vertex.co.y * scale + back - ring_back
            vertex.co.z = ring_base + (vertex.co.z - ring_base) * scale
    report['loop_uniform_scale'] = scale
    report['loop_depth_scale'] = scale
    report['loop_depth_translation_m'] = back - ring_back
    bpy.context.preferences.filepaths.save_version = 0
    for kind in ['High', 'Low']:
        objects = [bpy.data.objects[p + '_' + kind] for p in ['Body', 'Loop', 'Bar']]
        for obj in objects:
            obj.data.update()
        export(objects, output / ('medal-' + kind.lower() + '.glb'))
        payload = []
        for obj in objects:
            obj.data.calc_loop_triangles()
            data = dict(name=obj.name, vertices=[v.co[:] for v in obj.data.vertices],
                        triangles=[list(t.vertices) for t in obj.data.loop_triangles])
            if kind == 'Low':
                data['triangle_uv'] = [[obj.data.uv_layers.active.data[i].uv[:] for i in t.loops] for t in obj.data.loop_triangles]
            payload.append(data)
        (output / (kind.lower() + '-arrays.json')).write_text(json.dumps(payload, separators=(',', ':')))
    report['reduction'] = reduction
    shutil.copyfile(source / 'shape-decisions.json', output / 'shape-decisions.json')
    bpy.ops.wm.save_as_mainfile(filepath=str(output / 'medal-fitted.blend'))
    (output / 'refinement.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ['source', 'original', 'output']:
        parser.add_argument('--' + key, type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    refine(args.source.resolve(), args.original.resolve(), args.output.resolve())
