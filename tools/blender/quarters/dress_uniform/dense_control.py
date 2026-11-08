"""Audit the frozen dense body with the same SAT predicate as exported contacts."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from triangle_contacts import intersect


def audit(out):
    bpy.ops.wm.open_mainfile(filepath=str(out/'simulated.blend'))
    record = json.loads(bpy.context.scene['tunic5_record'])
    obj = bpy.data.objects['TunicBody']
    obj.data.calc_loop_triangles()
    vertices = np.array([obj.matrix_world @ v.co for v in obj.data.vertices])
    faces = np.array([t.vertices[:] for t in obj.data.loop_triangles])
    tree = BVHTree.FromPolygons(vertices.tolist(), faces.tolist(), all_triangles=True)
    contacts = []
    for i, j in tree.overlap(tree):
        if i >= j:
            continue
        a, b = vertices[faces[i]], vertices[faces[j]]
        if np.any(np.linalg.norm(a[:, None]-b[None, :], axis=2) < 1e-7):
            continue
        if intersect(a, b):
            contacts.append([i, j])
    motion = record['simulation']['last_five_frames_motion_m']
    result = dict(self_contacts=len(contacts), self_contact_requirement='< 50',
                  last_five_frames_motion_m=motion, motion_requirement='< 0.001 m',
                  exclusions=record['rest_contact_policy']['exclusion_vertices'],
                  examples=contacts[:20], frames=record['simulation']['frames'],
                  pass_control=len(contacts) < 50 and motion < .001)
    (out/'dense-control.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    result = audit(args.out.resolve())
    raise SystemExit(0 if result['pass_control'] else 1)
