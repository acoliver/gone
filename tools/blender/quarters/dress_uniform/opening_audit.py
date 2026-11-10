"""Measure physical clearance from the released sleeve cap to the body lips."""
import numpy as np


def armhole_gap(vertices, faces, uv):
    edges = np.sort(np.vstack([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1)
    unique, counts = np.unique(edges, axis=0, return_counts=True)
    boundary = unique[counts == 1]
    coordinates = {}
    for face, values in zip(faces, uv):
        for index, point in zip(face, values):
            coordinates.setdefault(index, []).append(point)
    sleeve, body = [], []
    for edge in boundary:
        pattern = np.array([p for i in edge for p in coordinates[i]])
        if pattern[:, 0].min() > 1.09 and pattern[:, 0].max() < 1.56 and pattern[:, 1].max() < .001:
            sleeve.append(edge)
        if (pattern[:, 0].max() < 1. and pattern[:, 0].min() > .43 and
                pattern[:, 1].min() > .66 and pattern[:, 1].max() < .96 and
                vertices[edge, 0].min() > .15):
            body.append(edge)
    if not sleeve or not body:
        raise ValueError('No released cap and body lips available for physical opening audit')
    segments = vertices[np.array(body)]
    start = segments[:, 0]
    delta = segments[:, 1]-start
    lengths = np.sum(delta*delta, axis=1)
    samples = np.concatenate([np.linspace(*vertices[edge], 9) for edge in sleeve])
    distances = []
    for point in samples:
        fraction = np.clip(np.sum((point-start)*delta, axis=1)/lengths, 0, 1)
        distances.append(np.linalg.norm(point-start-fraction[:, None]*delta, axis=1).min())
    distances = np.array(distances)
    return dict(maximum_clear_gap_m=float(distances.max()), p90_clear_gap_m=float(np.quantile(distances, .9)),
                median_clear_gap_m=float(np.median(distances)), threshold_m=.025,
                pass_gap=bool(np.median(distances) >= .025),
                method='sleeve-cap boundary samples to continuous reduced body-lip segments')
