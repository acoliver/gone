"""Recognise round fitted rails so polygon facets share one continuous face image."""
import numpy as np


def cylinders(faces):
    grouped = {}
    for face in faces:
        grouped.setdefault(face['part'], []).extend(face['triangles'])
    result = {}
    for part, triangles in grouped.items():
        points = np.unique(np.array(triangles).reshape(-1, 3), axis=0)
        centre = points.mean(0)
        _, vectors = np.linalg.eigh(np.cov((points-centre).T))
        axis = vectors[:, -1]
        if axis[np.argmax(abs(axis))] < 0:
            axis = -axis
        axial = (points-centre) @ axis
        radial = points-centre-axial[:, None]*axis
        radius = np.linalg.norm(radial, axis=-1)
        r = float(radius.max())
        length = float(np.ptp(axial))
        if r < 1e-6 or length < 6*r:
            continue
        horizontal = np.cross(axis, [0., 0., 1.] if abs(axis[2]) < .9 else [0., 1., 0.])
        horizontal /= np.linalg.norm(horizontal)
        vertical = np.cross(axis, horizontal)
        angle = np.arctan2(radial @ vertical, radial @ horizontal)
        # A box's few equal-radius corners must not be mistaken for a tube.
        outer = radius >= .99*r
        angles = np.unique(np.round(angle[outer], 4))
        if len(angles) < 12:
            continue
        gaps = np.diff(np.r_[angles, angles[0]+2*np.pi])
        if gaps.max() > .6:
            continue
        result[part] = dict(centre=centre, axis=axis, horizontal=horizontal,
                            vertical=vertical, low=axial.min(), length=length, radius=r)
    return result


def cylindrical_frame(points, cylinder):
    delta = points-cylinder['centre']
    u = np.arctan2(delta @ cylinder['vertical'], delta @ cylinder['horizontal'])/(2*np.pi)+.5
    v = ((delta @ cylinder['axis'])-cylinder['low'])/cylinder['length']
    coordinates = np.stack([u, v], axis=-1).reshape(-1, 3, 2)
    # Unroll each triangle across the angular seam before interpolation.
    coordinates[..., 0] = coordinates[:, :1, 0]+(coordinates[..., 0]-coordinates[:, :1, 0]+.5)%1-.5
    return coordinates, np.array([2*np.pi*cylinder['radius'], cylinder['length']])
