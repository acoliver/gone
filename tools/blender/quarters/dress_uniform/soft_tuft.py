"""Short wool tufts curl away from a broad attached root and taper softly."""
import numpy as np


def tuft_sections(root, direction, sideways, normal, width, length):
    t = np.linspace(0., 1., 4)
    root, direction, sideways, normal = map(np.asarray, (root, direction, sideways, normal))
    path = root+t[:, None]*direction*length
    path += np.sin(t*np.pi*.85)[:, None]*normal*length*.28
    path += (1-np.cos(t*np.pi*.75))[:, None]*sideways*length*.16
    breadth = width*(1-.55*t)
    return np.stack([path-sideways*breadth[:, None]/2,
                     path+sideways*breadth[:, None]/2], axis=1)
