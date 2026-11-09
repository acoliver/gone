"""Simplify wool panels without moving vertices or retessellating fitting supports."""
import math

import bmesh
import bpy

from bake_down import boundary_hausdorff


def reduce_body(dense, target):
    patch = dense.vertex_groups['DetailPatch'].index
    protected = {v.index for v in dense.data.vertices if any(g.group == patch and g.weight > 0 for g in v.groups)}
    low = dense.copy()
    low.data = dense.data.copy()
    bpy.context.collection.objects.link(low)
    dense.data.calc_loop_triangles()
    initial = len(dense.data.loop_triangles)
    for degrees in [2, 4, 6, 8, 10]:
        bm = bmesh.new()
        bm.from_mesh(dense.data)
        bm.verts.index_update()
        locked = {v for face in bm.faces if any(v.index in protected for v in face.verts) for v in face.verts}
        edges = [edge for edge in bm.edges if not edge.is_boundary and not any(v in locked for v in edge.verts)]
        bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(degrees), use_dissolve_boundaries=False,
                                verts=[], edges=edges)
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
        count = len(bm.faces)
        print('Fixed-support wool dissolve', degrees, count, 'target', target, flush=True)
        if count <= target:
            bm.to_mesh(low.data)
            bm.free()
            break
        bm.free()
    else:
        raise ValueError(f'Cannot reach {target} wool triangles with unchanged fitting-support faces and a 10 degree dissolve limit')
    low.data.update()
    report = dict(source_triangles=initial, target_triangles=target, triangles=count,
                  source='angle-limited dissolve outside immutable fitting-support faces; no vertex motion',
                  maximum_dissolve_angle_degrees=degrees, protected_source_vertices=len(protected),
                  boundary_hausdorff_upper_m=boundary_hausdorff(dense, low))
    report['pass'] = count <= target and report['boundary_hausdorff_upper_m'] <= .0015
    return low, report
