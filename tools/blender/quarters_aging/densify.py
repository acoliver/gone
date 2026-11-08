"""Dense working surfaces, locally refined bands and areal-mass bookkeeping."""
import bmesh
import numpy as np
from mathutils.bvhtree import BVHTree

from common import apply


def densify(obj, levels=2, bands=()):
    original_count = len(obj.data.vertices)
    mod = obj.modifiers.new('Dense simulation surface', 'SUBSURF')
    mod.subdivision_type = 'CATMULL_CLARK'
    mod.levels = levels
    mod.quality = 3
    mod.uv_smooth = 'PRESERVE_BOUNDARIES'
    apply(obj, mod)
    for predicate in bands:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        reference = BVHTree.FromBMesh(bm)
        edges = [e for e in bm.edges if predicate((e.verts[0].co+e.verts[1].co)/2)]
        result = bmesh.ops.subdivide_edges(bm, edges=edges, cuts=1, use_grid_fill=True)
        vertices = [v for v in result['geom_inner'] if isinstance(v, bmesh.types.BMVert)]
        for _ in range(3):
            bmesh.ops.smooth_vert(bm, verts=vertices, factor=.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
            for v in vertices:
                point, _, _, _ = reference.find_nearest(v.co)
                v.co = point
        bm.to_mesh(obj.data)
        bm.free()
    lengths = np.array([(obj.data.vertices[e.vertices[0]].co-obj.data.vertices[e.vertices[1]].co).length for e in obj.data.edges])
    return {'unaged_vertices': original_count, 'dense_vertices': len(obj.data.vertices),
            'mass_multiplier': original_count/len(obj.data.vertices),
            'edge_quantiles_m': np.quantile(lengths, [.1, .5, .9]).tolist()}


def triangulate(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=list(bm.faces), quad_method='BEAUTY')
    bm.to_mesh(obj.data)
    bm.free()
