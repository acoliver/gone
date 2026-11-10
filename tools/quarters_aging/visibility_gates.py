"""Visibility measurements use aligned real-renderer captures in linear light."""
import numpy as np
from scipy.ndimage import maximum_filter, binary_erosion
from scipy.signal import fftconvolve
from skimage.measure import find_contours

from colour import luminance


def dust_visibility(aged, disabled, up):
    if not up.any():
        raise ValueError('no up-facing receiver in dust control')
    return float(np.mean(luminance(aged)[up] - luminance(disabled)[up]))
def trail_metrics(colour, receiver, cx, source_y, pixels_per_metre, control=None):
    """Contiguous narrow rust runs, contrasted against paint on both sides."""
    from locker_gates import hsv
    hue, saturation, value = hsv(colour)
    # Translucent oxide has lower saturation than opaque substrate. Contrast
    # against both paint shoulders is still required on every row of the run.
    rust = (hue >= 5) & (hue <= 50) & (saturation >= .18) & (value > .10)
    if control is not None:
        rust &= control >= .15
    from locker_swatches import paint_field
    paint = paint_field(colour) >= .5
    lum = luminance(colour)
    height, width = receiver.shape
    radius = max(1, int(np.floor(.004 * pixels_per_metre)))
    centre = int(round(cx))
    qualifying = []
    widths, contrasts = [], []
    for y in range(max(0, int(np.ceil(source_y))), min(height, int(source_y + .205 * pixels_per_metre))):
        best = None
        for x in range(max(0, centre-radius), min(width, centre+radius+1)):
            if not (receiver[y, x] and rust[y, x]):
                continue
            left = right = x
            while left > 0 and rust[y, left-1] and receiver[y, left-1]: left -= 1
            while right < width-1 and rust[y, right+1] and receiver[y, right+1]: right += 1
            physical_width = (right-left+1) / pixels_per_metre
            if not .001 <= physical_width <= .015:
                continue
            flank_width = max(1, int(np.ceil(.004 * pixels_per_metre)))
            a = slice(max(0, left-flank_width), left)
            b = slice(right+1, min(width, right+1+flank_width))
            flank_a = receiver[y, a] & paint[y, a] & ~rust[y, a]
            flank_b = receiver[y, b] & paint[y, b] & ~rust[y, b]
            if not flank_a.any() or not flank_b.any():
                continue
            contrast = min(float(lum[y, a][flank_a].mean()), float(lum[y, b][flank_b].mean())) - float(lum[y, left:right+1].mean())
            if contrast >= .03:
                best = (physical_width, contrast, left, right)
                break
        qualifying.append((y, best))
    longest = 0
    run_start = None
    best_start = None
    previous = None
    for y, row in qualifying:
        if row is None:
            run_start, previous = None, None
            continue
        widths.append(row[0])
        contrasts.append(row[1])
        connected = previous is not None and row[2] <= previous[3]+1 and row[3] >= previous[2]-1
        if run_start is None or not connected:
            run_start = y
        previous = row
        length = y-run_start+1
        if (run_start-source_y) / pixels_per_metre <= .010 and length > longest:
            longest, best_start = length, run_start
    return dict(length_m=longest / pixels_per_metre,
                onset_m=None if best_start is None else (best_start-source_y) / pixels_per_metre,
                width_m=float(np.median(widths)) if widths else 0.,
                linear_contrast=float(np.median(contrasts)) if contrasts else 0.,
                passed=longest / pixels_per_metre >= .040)


def boundary_orientation(field, valid):
    """Gradient orientations on a lightly filtered material boundary, 10° bins.

    One capture pixel of smoothing removes raster quantisation, while preserving
    the much larger atlas-texel stair runs visible at the close-up camera.
    """
    from scipy.ndimage import gaussian_filter
    smooth = gaussian_filter(field.astype(float), 1.)
    gy, gx = np.gradient(smooth)
    gradient = np.hypot(gx, gy)
    boundary = binary_erosion(valid, iterations=3) & (smooth > .12) & (smooth < .88) & (gradient > .025)
    if boundary.sum() < 50:
        raise ValueError('insufficient close-up paint/rust boundary')
    angle = (np.degrees(np.arctan2(gy[boundary], gx[boundary])) + 5) % 180
    histogram, _ = np.histogram(angle, bins=18, range=(0, 180), weights=gradient[boundary])
    median = float(np.median(histogram))
    ratio = float(max(histogram[0], histogram[9]) / max(median, 1e-8))
    return ratio, histogram.tolist(), int(boundary.sum())




def strip_metrics(colour, receiver, cx, rows, pixels_per_metre, rust_classifier):
    yy, xx = np.indices(receiver.shape)
    centre = receiver & rows[:, None] & (abs(xx - cx) <= .0075 * pixels_per_metre)
    flank = receiver & rows[:, None] & (abs(xx - cx) >= .010 * pixels_per_metre) & (abs(xx - cx) <= .025 * pixels_per_metre)
    if centre.sum() < 8 or flank.sum() < 8:
        return None
    rust = rust_classifier(colour)
    lum = luminance(colour)
    fraction = float(rust[centre].mean())
    contrast = float(lum[flank].mean() - lum[centre].mean())
    # Median contiguous rust run across each row, containing the source axis.
    widths = []
    for y in np.flatnonzero(rows):
        x = int(round(cx))
        if not (0 <= x < rust.shape[1]) or not centre[y, x] or not rust[y, x]:
            continue
        left = right = x
        while left > 0 and rust[y, left - 1] and receiver[y, left - 1]: left -= 1
        while right + 1 < rust.shape[1] and rust[y, right + 1] and receiver[y, right + 1]: right += 1
        widths.append((right - left + 1) / pixels_per_metre)
    width = float(np.median(widths)) if widths else 0.
    return dict(rust_fraction=fraction, linear_contrast=contrast, width_m=width,
                passed=fraction >= .35 and contrast >= .04 and .004 <= width <= .015)


def longest_straight_boundary(rust, valid, pixels_per_metre):
    """Longest contour chord with every point within 1 mm of the chord.

    The prop silhouette is excluded because a trimmed island at the mesh edge
    cannot tell us anything about the material's corrosion boundary.
    """
    interior = binary_erosion(valid, iterations=2)
    longest = 0.
    for contour in find_contours(rust.astype(float), .5):
        if len(contour) < 3:
            continue
        for start in range(len(contour) - 2):
            for end in range(start + 2, len(contour)):
                points = contour[start:end + 1]
                indices = np.round(points).astype(int)
                if not interior[indices[:, 0], indices[:, 1]].all():
                    break
                delta = points[-1] - points[0]
                length = np.linalg.norm(delta)
                if length == 0: break
                if length / pixels_per_metre <= longest:
                    continue
                relative = points - points[0]
                errors = abs(relative[:, 0] * delta[1] - relative[:, 1] * delta[0]) / length
                if errors.max() / pixels_per_metre > .001:
                    continue
                longest = max(longest, length / pixels_per_metre)
    return float(longest)


def secondary_correlation(colour, pixels_per_metre, valid=None):
    image = luminance(colour)
    mask = np.ones_like(image) if valid is None else valid.astype(float)
    if np.var(image[mask > 0]) < 1e-10:
        raise ValueError('constant albedo has no measurable autocorrelation')
    image = (image - image[mask > 0].mean()) * mask
    def correlate(a, b):
        return fftconvolve(a, b[::-1, ::-1], mode='full')
    count = np.maximum(correlate(mask, mask), 1)
    total_a, total_b = correlate(image, mask), correlate(mask, image)
    covariance = correlate(image, image) - total_a * total_b / count
    variance_a = correlate(image ** 2, mask) - total_a ** 2 / count
    variance_b = correlate(mask, image ** 2) - total_b ** 2 / count
    correlation = covariance / np.sqrt(np.maximum(variance_a * variance_b, 1e-20))
    height, width = image.shape
    yy, xx = np.indices(correlation.shape)
    dy, dx = abs(yy - height + 1), abs(xx - width + 1)
    eligible = (np.hypot(dx, dy) / pixels_per_metre > .05) & (dx < width / 2) & (dy < height / 2)
    eligible &= count >= mask.sum() * .25
    peaks = eligible & (correlation == maximum_filter(correlation, size=3))
    return float(max(0., correlation[peaks].max(initial=0)))
