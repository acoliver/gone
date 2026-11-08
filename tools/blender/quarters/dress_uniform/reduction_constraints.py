"""Keep the supported crest and garment outline during game-mesh reduction."""
import bmesh
import numpy as np

from common import surface_tree


def protect_outline(body, hanger):
    body.data.update()
    tree = surface_tree(hanger)
    group = body.vertex_groups.get('Keep') or body.vertex_groups.new(name='Keep')
    group.remove(list(range(len(body.data.vertices))))
    uv = body.data.uv_layers['FlatPattern'].data
    panel = {loop.vertex_index for loop in body.data.loops if uv[loop.index].uv.x < 1.}
    sections = {}
    for index in sorted(panel):
        point = body.data.vertices[index].co
        sections.setdefault(int(np.floor(point.z/.01)), []).append(index)
    indices = set()
    for section in sections.values():
        x = np.array([body.data.vertices[i].co.x for i in section])
        indices.update(i for i, value in zip(section, x)
                       if min(value-x.min(), x.max()-value) <= .001)
    for vertex in body.data.vertices:
        point = body.matrix_world @ vertex.co
        _, _, _, distance = tree.find_nearest(point)
        if distance <= .006:
            indices.add(vertex.index)
    if indices:
        group.add(sorted(indices), 1., 'REPLACE')
    return dict(protected_vertices=len(indices), hanger_distance_m=.006,
                silhouette_section_height_m=.01, silhouette_band_m=.001)


def relax_interior(body, passes=4, factor=.3, maximum_motion=.001):
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.verts.ensure_lookup_table()
    deform = bm.verts.layers.deform.active
    keep = body.vertex_groups['Keep'].index
    movable = [v for v in bm.verts if not v.is_boundary and v[deform].get(keep, 0.) < .5]
    initial = {v: v.co.copy() for v in movable}
    for _ in range(passes):
        bmesh.ops.smooth_vert(bm, verts=movable, factor=factor,
                              use_axis_x=True, use_axis_y=True, use_axis_z=True)
        for vertex, start in initial.items():
            delta = vertex.co-start
            if delta.length > maximum_motion:
                vertex.co = start+delta.normalized()*maximum_motion
    motion = max(((v.co-start).length for v, start in initial.items()), default=0.)
    bm.to_mesh(body.data)
    bm.free()
    return dict(passes=passes, factor=factor, boundary_fixed=True, keep_fixed=True,
                maximum_allowed_motion_m=maximum_motion, measured_maximum_motion_m=motion,
                moved_vertices=len(movable))
