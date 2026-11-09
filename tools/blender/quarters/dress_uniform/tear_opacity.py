"""Pattern-grain crack branches and physical-distance lip breakup for tunic wool."""
import math

import bmesh
import numpy as np
from mathutils.kdtree import KDTree

from opacity_bake import opacity_bake, value_noise
from tear_paths import grain_walk


def branch_paths(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    uv = bm.loops.layers.uv[0]
    candidates = [np.array(loop[uv].uv) for edge in bm.edges if edge.is_boundary
                  for vertex in edge.verts for loop in vertex.link_loops
                  if vertex.co.x > .075 and vertex.co.z > -.22 and loop[uv].uv.x < .48]
    bm.free()
    if not candidates:
        raise ValueError('No front shoulder lip for grain-aligned crack branches')
    candidates = np.array(candidates)
    scale = np.array([1.1, .8])
    paths = []
    for number, target in enumerate([[.33, .94], [.40, .94]]):
        start = candidates[np.linalg.norm((candidates-target)*scale, axis=1).argmin()]*scale
        main = grain_walk(start, .030, 9570+number, step=.004, angle=-math.pi/2)
        branch = grain_walk(main[4], .018, 9580+number, step=.004,
                            angle=0 if number == 0 else math.pi)
        paths.extend([main, branch])
    return paths, scale


def wool_opacity(obj, out, size=2048, seed=9521):
    image, report = opacity_bake(obj, out, size=size, seed=seed)
    paths, pattern_scale = branch_paths(obj)
    starts = np.concatenate([p[:-1] for p in paths])
    deltas = np.concatenate([np.diff(p, axis=0) for p in paths])
    length2 = np.sum(deltas**2, axis=1)
    from tear_boundaries import labelled_samples, lip_opacity, retained_binding
    samples, erodible = labelled_samples(obj)
    tree = KDTree(len(samples))
    for index, point in enumerate(samples):
        tree.insert(point, index)
    tree.balance()
    positions = np.array([obj.matrix_world @ v.co for v in obj.data.vertices])
    pixels = np.empty(size*size*4, np.float32)
    image.pixels.foreach_get(pixels)
    pixels = pixels.reshape(size, size, 4)
    obj.data.calc_loop_triangles()
    bake_uv = obj.data.uv_layers['BakeUV'].data
    pattern_uv = obj.data.uv_layers[0].data
    vertex_distance = np.array([tree.find(point)[2] for point in positions])
    changed = 0
    missed_lip_texels = 0
    maximum_distance_error = 0.
    for triangle in obj.data.loop_triangles:
        ids = np.array(triangle.vertices)
        corners = np.array([bake_uv[i].uv[:] for i in triangle.loops])*size
        lo = np.maximum(0, np.floor(corners.min(0)).astype(int))
        hi = np.minimum(size-1, np.ceil(corners.max(0)).astype(int))
        if (hi < lo).any():
            continue
        x, y = np.meshgrid(np.arange(lo[0], hi[0]+1)+.5, np.arange(lo[1], hi[1]+1)+.5)
        a, b, c = corners
        determinant = np.linalg.det(np.array([b-a, c-a]))
        if abs(determinant) < 1e-12:
            continue
        v = ((x-a[0])*(c[1]-a[1])-(y-a[1])*(c[0]-a[0]))/determinant
        w = ((b[0]-a[0])*(y-a[1])-(b[1]-a[1])*(x-a[0]))/determinant
        u = 1-v-w
        inside = (u >= 0) & (v >= 0) & (w >= 0)
        if not inside.any():
            continue
        bary = np.c_[u[inside], v[inside], w[inside]]
        p = np.einsum('ij,jk->ik', bary, positions[ids])
        pattern = np.einsum('ij,jk->ik', bary, np.array([pattern_uv[i].uv[:] for i in triangle.loops]))
        nearest_lip = [tree.find(point) for point in p]
        distance = np.array([hit[2] for hit in nearest_lip])
        allowed = erodible[[hit[1] for hit in nearest_lip]]
        interpolated = np.einsum('ij,j->i', bary, vertex_distance[ids])
        missed_lip_texels += int(np.sum((distance < .003) & (interpolated >= .003)))
        maximum_distance_error = max(maximum_distance_error, float(np.max(np.abs(interpolated-distance))))
        coordinates = np.c_[pattern*pattern_scale, np.zeros(len(pattern))]
        # One erosion depth per boundary station avoids opaque islands over the dark inner ply.
        opaque = lip_opacity(distance, np.array([hit[0] for hit in nearest_lip]), seed)
        # The sewn collar binding stays intact; only released lips break up.
        opaque |= ~allowed
        binding = retained_binding(p)
        opaque |= binding
        delta = coordinates[:, None, :2]-starts
        t = np.clip(np.sum(delta*deltas, axis=2)/length2, 0, 1)
        distances = np.linalg.norm(delta-t[:, :, None]*deltas, axis=2)
        closest = distances.argmin(1)
        nearest = distances[np.arange(len(p)), closest]
        on_path = starts[closest]+t[np.arange(len(p)), closest, None]*deltas[closest]
        channel_noise = value_noise(np.c_[on_path, np.zeros(len(p))], .0025, seed+13)
        half_width = np.clip(.00065+.0014*channel_noise, .00015, .00135)
        # Branch openings remain sub-3 mm; the main gaping lips are geometry.
        crack = ((nearest < half_width) & (pattern[:, 0] < .48) & (pattern[:, 1] > .84) &
                 allowed & ~binding)
        tile = pixels[lo[1]:hi[1]+1, lo[0]:hi[0]+1, :3]
        before = tile[inside, 0].copy()
        tile[inside] = (opaque & ~crack)[:, None]
        changed += int(np.sum(before != tile[inside, 0]))
    image.unpack(method='REMOVE')
    image.pixels.foreach_set(pixels.ravel())
    image.save()
    image.reload()
    image.pack()
    density = []
    for triangle in obj.data.loop_triangles:
        pattern = np.array([pattern_uv[i].uv[:] for i in triangle.loops])
        if pattern[:, 0].max() >= 1. or pattern[:, 1].max() >= .06:
            continue
        tex = np.array([bake_uv[i].uv[:] for i in triangle.loops])*size
        edges = np.array([tex[1]-tex[0], tex[2]-tex[0]])
        if abs(np.linalg.det(edges)) < 1e-12:
            continue
        world = positions[np.array(triangle.vertices)]
        jacobian = np.linalg.solve(edges, np.array([world[1]-world[0], world[2]-world[0]]))
        density.extend(np.linalg.svd(jacobian, compute_uv=False).tolist())
    report['hem_texel_m_quantiles'] = np.quantile(density, [0., .5, .95, 1.]).tolist()
    report.update(distance_method='per-texel nearest physical lip, sampled at 0.25 mm; no vertex-distance interpolation',
                  grain_paths_m=[p.tolist() for p in paths], pattern_scale_m=pattern_scale.tolist(),
                  branch_length_m=.018,
                  crack_width_m=.0013, crack_width_range_m=[.0003, .0027], changed_texels=changed,
                  erosion_method='boundary-station noise with monotone inward opacity, 0.15 to 2.85 mm',
                  retained_crest='release labels plus the collar-side binding (abs x <160 mm, z >-190 mm); no grain perforations',
                  missed_lip_texels_by_vertex_interpolation=missed_lip_texels,
                  maximum_distance_interpolation_error_m=maximum_distance_error,
                  transparent_texels=int((pixels[:, :, 0] < .5).sum()))
    return image, report
