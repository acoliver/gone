"""Pattern-grain crack branches and physical-distance lip breakup for tunic wool."""
import math

import bmesh
import numpy as np
from mathutils.kdtree import KDTree

from bake_down import boundary_samples, boundary_segments
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
    samples = boundary_samples(boundary_segments(obj), .00025)
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
        distance = np.array([tree.find(point)[2] for point in p])
        interpolated = np.einsum('ij,j->i', bary, vertex_distance[ids])
        missed_lip_texels += int(np.sum((distance < .003) & (interpolated >= .003)))
        maximum_distance_error = max(maximum_distance_error, float(np.max(np.abs(interpolated-distance))))
        coordinates = np.c_[pattern*pattern_scale, np.zeros(len(pattern))]
        noise = sum(weight*value_noise(coordinates, wavelength, seed+octave)
                    for octave, (weight, wavelength) in enumerate(zip([.5, .25, .15, .1], [.002, .001, .0007, .0005])))
        opaque = (distance >= .003) | (distance/.003+noise*3.5 >= .35)
        delta = coordinates[:, None, :2]-starts
        t = np.clip(np.sum(delta*deltas, axis=2)/length2, 0, 1)
        nearest = np.linalg.norm(delta-t[:, :, None]*deltas, axis=2).min(1)
        # Branch openings remain sub-3 mm; the main gaping lips are geometry.
        crack = (nearest < .00065) & (pattern[:, 0] < .48) & (pattern[:, 1] > .84)
        tile = pixels[lo[1]:hi[1]+1, lo[0]:hi[0]+1, :3]
        before = tile[inside, 0].copy()
        tile[inside] = (opaque & ~crack)[:, None]
        changed += int(np.sum(before != tile[inside, 0]))
    image.unpack(method='REMOVE')
    image.pixels.foreach_set(pixels.ravel())
    image.save()
    image.reload()
    image.pack()
    report.update(distance_method='per-texel nearest physical lip, sampled at 0.25 mm; no vertex-distance interpolation',
                  grain_paths_m=[p.tolist() for p in paths], branch_length_m=.018,
                  crack_width_m=.0013, changed_texels=changed,
                  missed_lip_texels_by_vertex_interpolation=missed_lip_texels,
                  maximum_distance_interpolation_error_m=maximum_distance_error,
                  transparent_texels=int((pixels[:, :, 0] < .5).sum()))
    return image, report
