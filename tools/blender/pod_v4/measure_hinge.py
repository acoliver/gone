"""Measure #88 lid sweep against the bay, mesh contact, and live get-up eye."""
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parents[2] / 'tmp/pods/fix3'


def main():
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'pod-v4-working.blend'))
    bpy.context.view_layer.update()
    pivot = bpy.data.objects['PodLid'].matrix_world.translation.copy()
    vertices = []
    faces = []
    for name in ('PodLid', 'WindowPane'):
        obj = bpy.data.objects[name]
        offset = len(vertices)
        vertices += [obj.matrix_world @ v.co for v in obj.data.vertices]
        faces += [[offset + i for i in p.vertices] for p in obj.data.polygons]
    base = bpy.data.objects['PodBase']
    base_bvh = BVHTree.FromPolygons([v.co for v in base.data.vertices], [list(p.vertices) for p in base.data.polygons], all_triangles=False)
    def transformed(angle):
        rotation = Matrix.Rotation(-math.radians(angle),3,'X')
        return [pivot + rotation @ (v - pivot) for v in vertices]
    def rear(angle):
        return max(0, -2.393/2-min(v.z for v in transformed(angle)))
    # 8 m room, 2.393 m pods, 2.5 m aisle and the unchanged 150 mm exit reserve.
    maximum_offset = 4 - 2.393 - 1.25 - .15
    budget = maximum_offset - .02
    low, high = 0.0, 75.0
    for _ in range(40):
        middle = (low + high)/2
        if rear(middle) <= budget:
            low = middle
        else:
            high = middle
    # Production reserves 1 µm in Float32 row placement and rounds the angle
    # down so the unchanged strict 150 mm exit-clearance check remains true.
    chosen = 67.7295
    offset = .206999
    assert low - .001 < chosen <= low
    rows = []
    for step in range(math.ceil(chosen * 10) + 1):
        angle = min(step/10,chosen)
        vv = transformed(angle)
        tree = BVHTree.FromPolygons(vv,faces,all_triangles=False)
        intersections = len(base_bvh.overlap(tree))
        assert intersections == 0, (angle, intersections)
        # The axis point is a retained outer head-edge vertex.
        contact = tree.find_nearest(pivot)[3]
        base_contact = base_bvh.find_nearest(pivot)[3]
        rows.append(dict(angle=angle,rear=rear(angle),top=max(v.y for v in vv),intersections=intersections,axis_lid_distance=contact,axis_base_distance=base_contact))
    vv = transformed(chosen)
    tree = BVHTree.FromPolygons(vv,faces,all_triangles=False)
    eye = [Vector(v) for v in [(0,.545,-.575),(0,1.695,.575),(0,1.695,.8865),(0,1.695,1.5065),(0,1.605,1.5065)]]
    stationary = [base_bvh]
    for name in ('Couch', 'Pillow'):
        obj = bpy.data.objects[name]
        stationary.append(BVHTree.FromPolygons([obj.matrix_world @ v.co for v in obj.data.vertices], [list(p.vertices) for p in obj.data.polygons], all_triangles=False))
    minimum_eye = min(bvh.find_nearest(eye[i].lerp(eye[i+1],j/100))[3] for bvh in [tree] + stationary for i in range(4) for j in range(101))
    # Keep the rod out of automatic centerline reach. The curved low foot,
    # not the nominal maximum-length envelope, determines floor clearance.
    rod_axis = Vector((math.sin(math.radians(82)), 0, math.cos(math.radians(82))))
    rod_center = Vector((0, .022, -1.4 + (4 - 2.393/2 - offset)))
    rod_clearance = min(base_bvh.find_nearest(rod_center + rod_axis * (j/100 - .5))[3] for j in range(101)) - .022
    assert rod_clearance > 0
    result = dict(pivot=pivot[:],empty_angle=chosen,player_angle=chosen,row_wall_offset=offset,aisle_width=2.5,exit_reserve=.15,rear_swing=rear(chosen),wall_clearance=offset-rear(chosen),ceiling_clearance=3.2-max(v.y for v in vv),minimum_live_eye_clearance=minimum_eye,rod_surface_clearance=rod_clearance,sweep=rows)
    assert result['ceiling_clearance'] >= .05 and minimum_eye >= .13
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'hinge.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='sweep'},indent=2),flush=True)


if __name__ == '__main__':
    main()
