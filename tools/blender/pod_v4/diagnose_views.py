"""Ray-classify prepared render surfaces, not collision proxies.

Blender --background --python diagnose_views.py -- --captures <pod_captures output>.
Glass is skipped to identify the opaque surface behind it. Smoke is not geometry.
The NPZ retains each sampled pixel, first-hit surface, world point and normal.
"""
import argparse
import json
import math
from pathlib import Path
import sys

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform


def tree_from_parts(parts):
    vertices, faces, owners, normals = [], [], [], []
    for owner, part in enumerate(parts):
        if part['material'] == 'WindowTint':
            continue
        offset = len(vertices)
        vertices.extend(Vector(v) for v in part['vertices'])
        normals.extend(Vector(n) for n in part['normals'])
        indices = part['indices']
        triangles = [tuple(offset + i for i in indices[j:j+3]) for j in range(0,len(indices),3)]
        faces.extend(triangles)
        owners.extend([owner] * len(triangles))
    return BVHTree.FromPolygons(vertices,faces,all_triangles=True), vertices,faces,owners,normals


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--captures',type=Path,required=True)
    parser.add_argument('--stride',type=int,default=3)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    views = json.loads((args.captures/'measurements.json').read_text())['views']
    labels = ['sealed-close-white','open-head-hinge-contact','flank-row-a-left','flank-row-a-right','flank-row-b-left','flank-row-b-right','flank-mirror-left','flank-mirror-right']
    manifest = {}
    for geometry in ['scene','mirror']:
        parts = json.loads((args.captures/f'{geometry}-geometry.json').read_text())
        tree,vertices,faces,owners,normals = tree_from_parts(parts)
        manifest[geometry] = [{'path':p['path'],'material':p['material']} for p in parts]
        for label in labels:
            if ('mirror' in label) != (geometry == 'mirror'):
                continue
            view = views[label]
            eye = Vector(view['eye'])
            basis = np.array(view['basis']).reshape(3,3).T
            tangent = math.tan(math.radians(view['fov'])/2)
            rows=[]
            for y in range(0,648,args.stride):
                for x in range(0,1152,args.stride):
                    direction = Vector(basis @ np.array([((x+.5)/1152*2-1)*tangent*1152/648,(1-(y+.5)/648*2)*tangent,-1])).normalized()
                    start = eye + direction * view['near']
                    # Godot winds front faces clockwise; BVH geometric normals
                    # therefore point into an outward-facing render triangle.
                    remaining = view['far']
                    while remaining > 0:
                        point,geometric,triangle,distance = tree.ray_cast(start,direction,remaining)
                        if point is None:
                            break
                        cull = parts[owners[triangle]].get('cull_mode',0)
                        front = geometric.dot(direction) > 0
                        if cull == 2 or (cull == 0 and front) or (cull == 1 and not front):
                            break
                        start = point + direction * .00001
                        remaining -= distance + .00001
                    if point is None:
                        rows.append([x,y,-1,0,0,0,0,0,0,0])
                        continue
                    a,b,c = faces[triangle]
                    normal = barycentric_transform(point,vertices[a],vertices[b],vertices[c],normals[a],normals[b],normals[c]).normalized()
                    rows.append([x,y,owners[triangle],*point,*normal,normal.dot(-direction)])
            np.save(args.captures/f'{label}-rays.npy',np.array(rows,dtype=np.float32))
            print('classified',label,len(rows),flush=True)
    (args.captures/'ray-surfaces.json').write_text(json.dumps(manifest,indent=2))


if __name__ == '__main__':
    main()
