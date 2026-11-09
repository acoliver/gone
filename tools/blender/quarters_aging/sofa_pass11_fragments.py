"""Nine-vertex convex reductions of the existing cut-residue fragment shapes."""
import bmesh
import bpy
import numpy as np

from fabric_mesh import material, new_object
from sofa_decay_debris import load_templates


def compact(points, thickness=.44):
    bm = bmesh.new()
    for point in points:
        bm.verts.new(point)
    bmesh.ops.convex_hull(bm, input=list(bm.verts))
    bm.verts.index_update()
    hull = sorted({v for face in bm.faces for v in face.verts}, key=lambda v: v.index)
    points = np.array([v.co[:] for v in hull])
    bm.free()
    if len(points) < 9:
        raise ValueError('Cut-residue source needs at least nine hull vertices')
    selected = set()
    for axis in range(3):
        selected.update([int(points[:, axis].argmin()), int(points[:, axis].argmax())])
    while len(selected) < 9:
        distances = np.linalg.norm(points[:, None]-points[sorted(selected)][None, :], axis=2).min(1)
        selected.add(int(distances.argmax()))
    result = points[sorted(selected)].copy()
    result -= result.mean(0)
    axes = np.linalg.svd(result, full_matrices=False)[2]
    result = result@axes.T
    result *= np.array([1., .78, thickness])/np.ptp(result, axis=0)
    return result


def library(source, out):
    out.mkdir(parents=True, exist_ok=True)
    templates = load_templates(source)
    objects = set()
    mat = material('CompactFoamTemplate', (.32, .18, .075))
    for name, points, _ in templates:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
        points = compact(points, thickness=.30+.04*(int(name[-2:]) % 8))
        bm = bmesh.new()
        for point in points:
            bm.verts.new(point)
        bmesh.ops.convex_hull(bm, input=list(bm.verts))
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
        bm.verts.index_update()
        vertices = [v.co[:] for v in bm.verts]
        faces = [tuple(v.index for v in f.verts) for f in bm.faces]
        bm.free()
        if len(faces) != 14:
            raise ValueError(f'{name}: nine-vertex convex fragment has {len(faces)} triangles, expected 14')
        objects.add(new_object(name, vertices, faces, mat))
    path = out/'fragment-library.blend'
    bpy.data.libraries.write(str(path), objects)
    for obj in objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    return path
