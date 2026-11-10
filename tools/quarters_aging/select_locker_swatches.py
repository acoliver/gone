"""Measure FLUX candidates and save reproducible linear-light albedo calibration."""
import json

import numpy as np
from PIL import Image, ImageDraw
from scipy.optimize import least_squares

from colour import linear, lab
from locker_swatches import SOURCE, ROOT, read_rgb, paint_field, calibrate, class_scores, flatten_lighting, calibrated_swatch
from visibility_gates import secondary_correlation


def fit_gain(colour, reference):
    colour, reference = colour.astype(np.float64), reference.astype(np.float64)
    gain = linear(reference).mean((0, 1)) / np.maximum(linear(colour).mean((0, 1)), 1e-6)
    masks = [paint_field(colour) >= .5, paint_field(colour) < .5]
    targets = [lab(reference[paint_field(reference) >= .5]),
               lab(reference[paint_field(reference) < .5])]
    def error(parameters):
        adjusted = calibrate(colour, np.exp(parameters[:3]), np.exp(parameters[3]))
        values = [lab(adjusted[mask]) for mask in masks]
        return np.concatenate([moment(observed, axis=0) - moment(expected, axis=0)
                               for moment in (np.mean, np.std)
                               for observed, expected in zip(values, targets)])
    result = least_squares(error, np.r_[np.log(gain), 0.], max_nfev=40)
    return np.exp(result.x[:3]), float(np.exp(result.x[3]))


def score(colour, reference):
    scores = class_scores(colour, reference)
    scores['secondary_autocorrelation'] = secondary_correlation(colour, 300)
    luminance = linear(colour) @ np.array([.2126, .7152, .0722])
    # Border and global planar illumination are proxies. Image-comparer also
    # checks for baked objects, cast shadows and borders in the selected sheet.
    h, w = luminance.shape
    edge = np.zeros((h, w), bool)
    edge[:16] = edge[-16:] = True
    edge[:, :16] = edge[:, -16:] = True
    scores['border_linear_difference'] = float(abs(luminance[edge].mean() - luminance[~edge].mean()))
    yy, xx = np.mgrid[:h, :w]
    design = np.stack([np.ones(h*w), xx.ravel()/w, yy.ravel()/h], -1)
    coefficients = np.linalg.lstsq(design, luminance.ravel(), rcond=None)[0]
    scores['planar_light_gradient'] = float(np.linalg.norm(coefficients[1:]))
    scores['rust_fraction'] = float((paint_field(colour) < .5).mean())
    scores['rank_score'] = (max(scores[name] for name in scores if name.endswith('delta_e'))
                            + scores['secondary_autocorrelation'] * 8
                            + scores['border_linear_difference'] * 20 + scores['planar_light_gradient'] * 20)
    return scores


def main():
    regions, candidates = {}, {}
    review = json.loads((SOURCE / 'visual-selection.json').read_text())
    for name in ('panel', 'loss', 'dust'):
        reference_name = 'panel-reference.png' if name == 'panel' else f'{name}-crop.png'
        reference = read_rgb(SOURCE / reference_name)
        rows = []
        for path in sorted(SOURCE.glob(f'{name}-[0-9]*.png')):
            seed = int(path.stem.split('-')[1])
            raw = read_rgb(path)
            prepared = flatten_lighting(raw) if name == 'dust' else raw
            gain, contrast = fit_gain(prepared, reference)
            if name == 'loss':
                gain *= [1.1, .95, .85]
            row = dict(seed=seed, candidate=path.name, reference=reference_name,
                       linear_rgb_factor=gain.tolist(), linear_contrast=contrast,
                       flatten_linear_light=name == 'dust',
                       paint_white_balance=[.90, 1.08, 1.26] if name == 'panel' else ([1, 1.02, .96] if name == 'dust' else [1, 1, 1]))
            colour = calibrated_swatch(raw, row)
            scores = score(colour, reference)
            row['scores'] = scores
            rows.append(row)
            print(name, seed, scores, flush=True)
        candidates[name] = rows
        eligible = [row for row in rows if str(row['seed']) not in review['rejected'] and max(value for key, value in row['scores'].items() if key.endswith('delta_e')) <= 8
                    and row['scores']['secondary_autocorrelation'] <= .5
                    and (name != 'panel' or .08 <= row['scores']['rust_fraction'] <= .25)]
        if eligible:
            regions[name] = min(eligible, key=lambda row: row['scores']['rank_score'])
    document = dict(method='sRGB decode, fitted linear RGB multiplicative reflectance factors and mean-preserving linear contrast, then sRGB encode; hatch calibrate_albedo()',
                    illumination='Dust log-linear illumination plane is divided out before calibration. Panel paint alone receives a bounded white balance to remove the source lamp cast; rust pigment is unchanged. All final colour scores include these transforms.',
                    measurement='D65 Lab class means and standard deviations; classes from unchanged hatch paint_fields chroma rule',
                    pixels_per_metre=300, regions=regions, candidates=candidates)
    (SOURCE / 'selection-scores.json').write_text(json.dumps(candidates, indent=2) + '\n')
    if len(regions) != 3:
        raise ValueError('no eligible candidate for ' + str(set(candidates) - set(regions)))
    (SOURCE / 'albedo-calibration.json').write_text(json.dumps(document, indent=2) + '\n')
    sheet = Image.new('RGB', (1536, 3*570), '#24282a')
    draw = ImageDraw.Draw(sheet)
    for index, (name, row) in enumerate(regions.items()):
        y = index * 570
        reference = Image.open(SOURCE / row['reference']).convert('RGB')
        reference.thumbnail((480, 480))
        sheet.paste(reference, (20+(480-reference.width)//2, y+50+(480-reference.height)//2))
        raw = Image.open(SOURCE / row['candidate']).convert('RGB').resize((480, 480))
        sheet.paste(raw, (520, y+50))
        calibrated = calibrated_swatch(read_rgb(SOURCE / row['candidate']), row)
        image = Image.fromarray(np.uint8(np.round(np.clip(calibrated, 0, 1)*255))).resize((480, 480))
        sheet.paste(image, (1030, y+50))
        draw.text((20, y+15), f'{name}: source crop | generated seed {row["seed"]} | calibrated linear albedo', fill='white')
        draw.text((520, y+535), f'Lab max delta {max(v for k,v in row["scores"].items() if k.endswith("delta_e")):.3f}; correlation {row["scores"]["secondary_autocorrelation"]:.3f}', fill='white')
    sheet.save(ROOT / 'tmp/mat/locker/pass3/swatches.png')


if __name__ == '__main__':
    main()
