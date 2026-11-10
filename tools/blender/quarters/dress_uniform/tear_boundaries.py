"""Distinguish released tear lips from the still-sewn shoulder binding."""
import bmesh
import numpy as np


def retained_binding(points):
    points = np.asarray(points)
    return (np.abs(points[:, 0]) < .16) & (points[:, 2] > -.19)


def lip_opacity(distance, boundary_points, seed):
    from opacity_bake import value_noise
    noise = sum(weight*value_noise(boundary_points, wavelength, seed+octave)
                for octave, (weight, wavelength) in enumerate(zip([.5, .25, .15, .1],
                                                                 [.002, .001, .0007, .0005])))
    erosion = np.clip(.0014+.0028*noise, .00015, .00285)
    return np.asarray(distance) >= erosion


def release_weights(obj):
    group = obj.vertex_groups['Lip shrink'].index
    return np.array([next((g.weight for g in v.groups if g.group == group), 0.)
                     for v in obj.data.vertices])


def labelled_samples(obj, spacing=.00025):
    weights = release_weights(obj)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    points, erodible = [], []
    for edge in bm.edges:
        if not edge.is_boundary:
            continue
        a, b = [obj.matrix_world @ v.co for v in edge.verts]
        released = all(weights[v.index] >= .5 for v in edge.verts)
        allowed = min(a.z, b.z) < -.24 or released
        count = max(1, int(np.ceil((b-a).length/spacing)))
        for t in np.linspace(0., 1., count+1):
            points.append(a.lerp(b, float(t)))
            erodible.append(allowed)
    bm.free()
    return points, np.array(erodible, dtype=bool)
