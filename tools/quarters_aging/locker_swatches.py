"""Generated paint colour and image-derived loss boundaries at physical scale."""
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates

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
    return .031 + .049 * pigment


def aged_colour(points, normals, distance, cavity, hardware):
    images, calibration = load_swatches()
    panel = project_swatch(images['panel'], points, normals, offset=PANEL_OFFSET)
    loss = project_swatch(images['loss'], points, normals, offset=LOSS_OFFSET)
    horizontal = abs(normals).argmax(-1) == 2
    loss[horizontal] = project_swatch(images['loss'], points[horizontal], normals[horizontal], offset=HORIZONTAL_LOSS_OFFSET)
    # The heavy-loss image's paint islands decide the irregular edge-band
    # boundary. Geometry supplies exposure, never an independent noise pattern.
    panel_paint = paint_field(panel[None])[0]
    loss_paint = paint_field(loss[None])[0]
    reach = edge_reach(loss, images['loss'])
    intensity = np.clip((reach - distance) / .010 + cavity * .20, 0, 1)
    boundary = np.clip(((1 - loss_paint) - .35) / .20, 0, 1)
    blend = intensity * boundary
    blend[hardware | (normals[:, 2] > .7)] = 1
    colour = panel * (1 - blend[:, None]) + loss * blend[:, None]
    rust = 1 - (panel_paint * (1 - blend) + loss_paint * blend)
    dust = project_swatch(images['dust'], points, normals)
    return colour, rust, dust, calibration
