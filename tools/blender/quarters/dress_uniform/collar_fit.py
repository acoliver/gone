"""Fit a standing collar from its sewn curve, not individual shoulder-face frames."""
import json

import numpy as np


def curve_frames(points):
    tangent = np.roll(points, -1, axis=0)-np.roll(points, 1, axis=0)
    tangent[:, 2] = 0.
    tangent /= np.linalg.norm(tangent, axis=1)[:, None]
    area = np.sum(points[:, 0]*np.roll(points[:, 1], -1)-points[:, 1]*np.roll(points[:, 0], -1))
    if abs(area) < 1e-10:
        raise ValueError('Standing collar has a collapsed sewn curve')
    normal = np.c_[tangent[:, 1], -tangent[:, 0], np.zeros(len(points))]*np.sign(area)
    up = np.tile([0., 0., 1.], (len(points), 1))
    return np.stack([tangent, normal, up], axis=1)


def fit_standing_collar(body, collar, binding):
    attachment = json.loads(collar['attachment'])
    bases = np.asarray(attachment['base_blender_m'])
    columns = np.asarray(attachment['top_blender_m'])-bases
    original = np.asarray(binding['original'])
    fraction = np.clip(np.einsum('ijk,jk->ij', original[:, None]-bases, columns)/
                       np.sum(columns**2, axis=1), 0, 1)
    station = np.linalg.norm(original[:, None]-bases-columns*fraction[:, :, None], axis=2).argmin(1)
    vertices = np.array([body.matrix_world @ vertex.co for vertex in body.data.vertices])
    anchors, normals = [], []
    for entry in binding['entries']:
        triangle = vertices[list(entry['triangle'])]
        anchors.append(np.asarray(entry['weights'])@triangle)
        normal = np.cross(triangle[1]-triangle[0], triangle[2]-triangle[0])
        normals.append(normal/np.linalg.norm(normal))
    anchors, normals = np.asarray(anchors), np.asarray(normals)
    curve = np.array([anchors[station == i].mean(0) for i in range(len(bases))])
    support_normals = np.array([normals[station == i].mean(0) for i in range(len(bases))])
    support_normals /= np.linalg.norm(support_normals, axis=1)[:, None]
    source_frames = curve_frames(bases)
    frames = curve_frames(curve)
    offsets = np.einsum('ij,ikj->ik', original-bases[station], source_frames[station])
    destination = curve[station]+np.einsum('ij,ijk->ik', offsets, frames[station])
    destination += support_normals[station]*.002
    return destination
