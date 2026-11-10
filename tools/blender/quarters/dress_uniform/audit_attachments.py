"""Audit authored attachment bases on a finished tunic without changing geometry."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from attachment_metrics import base_indices, rigid_normal
from common import surface_tree


def audit(out):
    bpy.ops.wm.open_mainfile(filepath=str(out/'finished.blend'))
    record = json.loads(bpy.context.scene['tunic5_record'])
    report = {}
    for name, binding in record['bindings'].items():
        if name == 'Collar':
            continue
        obj = bpy.data.objects[name]
        original = np.asarray(binding['original'])
        points = np.array([obj.matrix_world @ v.co for v in obj.data.vertices])
        authored = json.loads(obj['attachment'])
        indices = base_indices(original, authored['base_blender_m'])
        support = ('Collar' if name.startswith('CollarInsignia') else
                   'Placket' if name == 'Buttons' else 'TunicBody')
        tree = surface_tree(bpy.data.objects[support])
        groups = []
        for ids in binding['groups']:
            base = np.intersect1d(indices, ids)
            hits = [tree.find_nearest(Vector(points[i])) for i in base]
            distances = [hit[3] for hit in hits]
            angle = None
            if binding['rigid']:
                normal = np.asarray([hit[1][:] for hit in hits]).mean(0)
                normal /= np.linalg.norm(normal)
                outward = np.array([0, 0, 1]) if name.startswith('ShoulderBoard') else np.array([0, -1, 0])
                own = rigid_normal(original[ids], points[ids],
                                   np.flatnonzero(np.isin(ids, base)), outward)
                angle = float(np.degrees(np.arccos(np.clip(own@normal, -1, 1))))
            groups.append(dict(base_vertices=len(base), minimum_base_distance_m=min(distances),
                               maximum_base_distance_m=max(distances), normal_error_degrees=angle,
                               within_2mm=max(distances) <= .002))
        report[name] = dict(support=support, groups=groups,
                            within_2mm=all(group['within_2mm'] for group in groups))
    report['all_bases_within_2mm'] = all(item['within_2mm'] for item in report.values())
    (out/'attachment-audit.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    result = audit(args.out.resolve())
    raise SystemExit(0 if result['all_bases_within_2mm'] else 1)
