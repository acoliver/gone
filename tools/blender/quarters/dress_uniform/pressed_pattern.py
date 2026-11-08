"""Lay a sleeve perimeter onto two broad faces joined by rounded pressed folds."""
import numpy as np


def capsule_section(perimeter, distance, radius=.006):
    straight = (perimeter-2*np.pi*radius)/2
    if straight <= 0:
        raise ValueError('Sleeve perimeter is too short for its pressed folds')
    distance = np.asarray(distance) % perimeter
    quarter = np.pi*radius/2
    result = np.empty((len(distance), 2))
    for i, position in enumerate(distance):
        if position < quarter:
            angle = np.pi+position/radius
            result[i] = [-straight/2+radius*np.cos(angle), radius*np.sin(angle)]
        elif position < quarter+straight:
            result[i] = [-straight/2+position-quarter, -radius]
        elif position < quarter+straight+2*quarter:
            angle = -np.pi/2+(position-quarter-straight)/radius
            result[i] = [straight/2+radius*np.cos(angle), radius*np.sin(angle)]
        elif position < quarter+2*straight+2*quarter:
            result[i] = [straight/2-(position-quarter-straight-2*quarter), radius]
        else:
            angle = np.pi/2+(position-quarter-2*straight-2*quarter)/radius
            result[i] = [-straight/2+radius*np.cos(angle), radius*np.sin(angle)]
    return result


def press_rows(points, pattern_uv):
    result = np.asarray(points).copy()
    angle = np.arctan2(.3, .9)
    rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
    for station in np.unique(np.round(pattern_uv[:, 1], 6)):
        ids = np.flatnonzero(np.round(pattern_uv[:, 1], 6) == station)
        circum, first, inverse = np.unique(np.round(pattern_uv[ids, 0], 6), return_index=True, return_inverse=True)
        if len(circum) < 3:
            raise ValueError('Sleeve pattern row has fewer than three perimeter stations')
        ring = points[ids[first], :2]
        lengths = np.linalg.norm(np.roll(ring, -1, axis=0)-ring, axis=1)
        distance = np.r_[0., np.cumsum(lengths[:-1])]
        pressed = capsule_section(lengths.sum(), distance)@rotation.T+ring.mean(0)
        transition = np.clip((-.235-points[ids, 2])/.105, 0, 1)
        result[ids, :2] += (pressed[inverse]-points[ids, :2])*transition[:, None]
    return result
