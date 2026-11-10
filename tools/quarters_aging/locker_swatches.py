"""Generated paint colour and image-derived loss boundaries at physical scale."""
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates, distance_transform_edt, gaussian_filter

from finish_fields import noise
from locker_blisters import blister_field

from colour import linear, srgb, lab

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from prepare_hatch_paint import paint_fields, calibrate_albedo

SOURCE = ROOT / 'art-source/quarters/locker'
PIXELS_PER_METRE = 300.
PANEL_OFFSET = (280, 0)
LOSS_OFFSET = (340, 0)
HORIZONTAL_LOSS_OFFSET = (280, 80)


def paint_field(colour):
    image = Image.fromarray(np.uint8(np.round(np.clip(colour, 0, 1) * 255)))
    return paint_fields(image)[1]


def calibrate(colour, gain, contrast=1.):
    if contrast != 1.:
        energy = linear(colour)
        mean = energy.mean(axis=(0, 1), keepdims=True)
        colour = srgb(np.clip(mean + (energy - mean) * contrast, 0, 1))
    return calibrate_albedo(colour, gain)



def flatten_lighting(colour):
    energy = linear(colour.astype(np.float64))
    h, w = energy.shape[:2]
    yy, xx = np.mgrid[:h, :w]
    design = np.stack([xx.ravel()/w - .5, yy.ravel()/h - .5, np.ones(h*w)], -1)
    luminance = energy @ np.array([.2126, .7152, .0722])
    coefficients = np.linalg.lstsq(design, np.log(np.maximum(luminance, 1e-5)).ravel(), rcond=None)[0]
    illumination = np.exp((design[:, :2] @ coefficients[:2]).reshape(h, w))
    return srgb(np.clip(energy / illumination[..., None], 0, 1))


def calibrated_swatch(colour, row):
    if row['flatten_linear_light']:
        colour = flatten_lighting(colour)
    colour = calibrate(colour, row['linear_rgb_factor'], row['linear_contrast'])
    paint = (paint_field(colour) >= .5)[..., None]
    balanced = calibrate(colour, row['paint_white_balance'])
    return np.where(paint, balanced, colour)

def read_rgb(path):
    return np.asarray(Image.open(path).convert('RGB'), np.float32) / 255


def class_scores(colour, reference):
    scores = {}
    for name, selected, target in [('paint', paint_field(colour) >= .5, paint_field(reference) >= .5),
                                   ('rust', paint_field(colour) < .5, paint_field(reference) < .5)]:
        if not selected.any() or not target.any():
            raise ValueError('no measurable ' + name + ' class')
        observed, expected = lab(colour[selected]), lab(reference[target])
        scores[name + '_mean_delta_e'] = float(np.linalg.norm(observed.mean(0) - expected.mean(0)))
        scores[name + '_std_delta_e'] = float(np.linalg.norm(observed.std(0) - expected.std(0)))
    return scores


def project_swatch(image, points, normals, offset=(0, 0)):
    """Dominant-axis physical projection; every source pixel spans 1/300 metre."""
    axis = abs(normals).argmax(-1)
    uv = np.empty((len(points), 2), np.float64)
    for normal_axis, plane in [(0, (1, 2)), (1, (0, 2)), (2, (0, 1))]:
        selected = axis == normal_axis
        uv[selected] = points[selected][:, plane]
    # Offset keeps the complete 2.4 m locker inside a 2.56 m source, without a
    # repeat across any broad face. Wrapping is only outside that source extent.
    uv = uv * PIXELS_PER_METRE + [180 + offset[0], 12 + offset[1]]
    uv[:, 1] += (axis == 2) * 168
    return np.stack([map_coordinates(image[..., c], [uv[:, 1], uv[:, 0]], order=1, mode='grid-wrap')
                     for c in range(image.shape[-1])], -1)


def edge_variation(fractions):
    fractions = np.asarray(fractions)
    return float(fractions.std() / max(float(fractions.mean()), 1e-8))


def load_swatches():
    document = json.loads((SOURCE / 'albedo-calibration.json').read_text())
    images = {name: calibrated_swatch(read_rgb(SOURCE / row['candidate']), row)
              for name, row in document['regions'].items()}
    return images, document


def edge_reach(loss, source):
    lo, hi = np.quantile(source[..., 0], [.05, .95])
    pigment = np.clip((loss[:, 0] - lo) / (hi - lo), 0, 1)
    return .005 + .020 * pigment ** .08


def aged_colour(points, normals, distance, cavity, hardware, sources, seed, edge_distance):
    images, calibration = load_swatches()
    loss = project_swatch(images['loss'], points, normals, offset=LOSS_OFFSET)
    horizontal = abs(normals).argmax(-1) == 2
    loss[horizontal] = project_swatch(images['loss'], points[horizontal], normals[horizontal], offset=HORIZONTAL_LOSS_OFFSET)
    paint, oxide = material_colours(points, normals, images)
    reach = edge_reach(loss, images['loss'])
    # Millimetre breakup leaves intact gaps even directly on an exposed edge.
    physical = points @ np.array([[.36, -.48, .8], [.8, .60, 0], [-.48, .64, .6]])
    breakup = noise(physical, 43, 9511) * .65 + noise(physical, 173, 9512) * .35
    reach = np.clip(reach + (noise(physical, 131, 9536) - .5) * .010, .005, .025)
    corner = np.clip((cavity - .72) * 5, 0, 1)
    reach += corner * np.clip((noise(physical, 31, 9533) - .65) * 4, 0, 1) * .025
    edge = np.clip((reach - distance) / .004 + .5, 0, 1)
    edge *= np.clip((breakup - .26) / .12, 0, 1)
    phase = points.sum(-1) * 35 + noise(physical, 19, 9530) * 3
    gaps = np.clip((np.sin(phase) + .60) / .25, 0, 1)
    edge *= gaps
    # Explicit separation prevents neighbouring blisters from forming large
    # islands, which a thresholded continuous noise field cannot guarantee.
    broad = blister_field(points, normals, seed)
    rust = np.maximum(edge, broad)
    rust = np.maximum(rust, cavity * np.clip((breakup - .40) * 4, 0, 1) * gaps)
    # Unprotected hardware retains both oxide patches and polished grey edges.
    patches = noise(points, 83, 9515)
    wear = (edge_distance < .0035) & (patches > .59)
    hardware_rust = np.where(patches > .25, .96, .05)
    rust[hardware] = np.where(wear, .02, hardware_rust)[hardware]
    roof = (normals[:, 2] > .7) & ~hardware
    roof_loss = np.clip((noise(points[roof], 18, 9518) - .45) / .06 + .5, 0, 1)
    rust[roof] = np.maximum(rust[roof], roof_loss * gaps[roof])
    # Sparse blisters leave paint shoulders beside the attached runoff. Without
    # them a run disappears into the fixture's broader oxide halo.
    if sources:
        from streak_sources import source_rows
        origins, shapes = source_rows(sources, seed)
        for origin, shape in zip(origins, shapes):
            if shape[1] < .5:
                continue
            x, z, minus_y = origin[:3]
            drop = z - points[:, 2]
            receiver = (drop >= 0) & (drop < shape[0]) & ~hardware
            front = (abs(points[:, 1] + minus_y) < .035) & (abs(normals[:, 1]) > .6)
            side = (abs(points[:, 0] - x) < .035) & (abs(normals[:, 0]) > .6)
            lateral = np.where(front, abs(points[:, 0] - x), abs(points[:, 1] + minus_y))
            receiver &= (front | side) & (lateral < .015) & (drop < .090)
            ragged = noise(physical[receiver], 173, 9522)
            shoulders = np.clip((.012 + .003 * ragged - lateral[receiver]) / .004, 0, 1)
            shoulders *= np.clip((.090 - drop[receiver]) / .018, 0, 1)
            rust[receiver] *= 1 - .94 * shoulders
    colour = paint * (1 - rust[:, None]) + oxide * rust[:, None]
    steel = np.array([.49, .52, .54])
    colour[hardware] = steel * (1 - rust[hardware, None]) + oxide[hardware] * rust[hardware, None]
    smooth_dust = linear(gaussian_filter(images['dust'], sigma=(24, 24, 0)))
    mean_dust = smooth_dust.mean((0, 1), keepdims=True)
    smooth_dust = srgb(mean_dust + (smooth_dust - mean_dust) * .05)
    dust = project_swatch(smooth_dust, points, normals)
    return colour, rust, dust, calibration


def material_colours(points, normals, images=None):
    """Class-conditioned source colours keep the low-resolution field out of RGB."""
    if images is None:
        images, _ = load_swatches()
    colours = []
    for name, want_paint, offset in [('panel', True, PANEL_OFFSET), ('loss', False, LOSS_OFFSET)]:
        image = images[name]
        is_paint = paint_field(image) >= .5
        nearest = distance_transform_edt(is_paint != want_paint, return_distances=False, return_indices=True)
        separated = gaussian_filter(image[tuple(nearest)], sigma=(1.2, 1.2, 0))
        colours.append(project_swatch(separated, points, normals, offset=offset))
    return colours
