"""Separate fine settled powder from broad paint variation on large tops."""
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

from colour import lab
from locker_faces import paint_fields
from select_locker_faces import from_lab


def soften_dust(image, size_m):
    size = np.asarray(size_m, float)
    if size.shape != (2,) or not np.isfinite(size).all() or np.any(size <= 0):
        raise ValueError('dust requires two positive physical dimensions')
    colour, paint = paint_fields(image)
    selected = paint > .8
    if not selected.any():
        raise ValueError('dust requires a painted source')
    values = lab(colour)
    centre = values[selected].mean(0)
    sigma = .003*np.array(image.size)/size
    low = gaussian_filter(values, (sigma[1], sigma[0], 0))
    # Keep the generated fine detail at its physical pitch, reducing only the
    # broad paint clouds. Oxide and its feathered transition remain untouched.
    powder = centre + .15*(low-centre) + .8*(values-low)
    weight = np.clip((paint-.5)/.3, 0, 1)[..., None]
    output = np.uint8(np.round(from_lab(values*(1-weight)+powder*weight)*255))
    output[paint <= .5] = np.asarray(image.convert('RGB'))[paint <= .5]
    return Image.fromarray(output)
