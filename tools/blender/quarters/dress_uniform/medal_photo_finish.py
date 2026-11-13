"""Medal-local material-map calibration against the selected photographic targets."""
import argparse
import json
from pathlib import Path
import shutil

import numpy as np
from PIL import Image

from medal_dry_finish import brass_finish, linear, ribbon_weave, save

ROOT = Path(__file__).resolve().parents[4]


def oxide_field(position):
    p = position * 1000
    waves = []
    for direction, pitch, phase in [([.83, .12, .54], .85, .4),
                                     ([-.37, .21, .90], 1.6, 2.7),
                                     ([.64, -.17, -.75], 3.1, 1.3),
                                     ([.23, .88, .41], .56, 4.1)]:
        waves.append(np.sin((p @ direction) * (2 * np.pi / pitch) + phase))
    return sum(waves) / len(waves)


def calibrated_brass(cavity, edge, noise, aged):
    base = np.broadcast_to([.66, .43, .14], cavity.shape + (3,))
    bare, _, _ = brass_finish(base, np.full_like(cavity, .30), np.zeros_like(cavity), edge, False)
    balance = np.array([.63, .51, .33]) if aged else np.array([.40, .55, .64])
    # Effective atlas reflectance is calibrated under the fixed rig, not an alloy F0 measurement.
    colour = bare * (balance / [.90, .64, .24])
    colour *= (1 + (.22 if aged else .10) * noise[:, :, None])
    colour *= 1 + (.08 if aged else .04) * edge[:, :, None]
    colour *= 1 - .35 * cavity[:, :, None]
    rough = (.98 if aged else .95) - .03 * edge + .025 * noise + .02 * cavity
    metallic = .985 * (1 - cavity) + .45 * cavity
    return np.clip(colour, 0, 1), np.clip(rough, .3, 1), metallic


def photo_ribbon():
    normal, rough, fibre = ribbon_weave()
    xy = normal[:, :, :2] * [1.2, 1.45]
    normal = np.concatenate([xy, np.sqrt(1 - np.sum(xy * xy, axis=2))[:, :, None]], 2)
    rough = np.clip(.55 + (rough - rough.mean()) * 1.4, 0, 1)
    fibre = np.clip(.955 + (fibre - fibre.mean()) * 1.4, .90, 1.)
    return normal, rough, fibre


def finish(bakes, baseline, output, enamel_roughness=.25, enamel_gain=.7):
    output.mkdir(parents=True, exist_ok=True)
    fields = np.load(bakes / 'material-fields.npz')
    enamel = np.flipud(fields['enamel'])
    cavity = np.flipud(fields['tarnish'])
    edge = np.clip((np.flipud(fields['convex']) - .12) / .4, 0, 1)
    occupied = np.flipud(fields['mask'])
    position = np.flipud((np.load(bakes / 'surface_position.npy')[:, :, :3] - .5) / 20)
    noise = oxide_field(position)
    report = {}
    for prefix in ['as_built', 'aged']:
        original = linear(np.asarray(Image.open(baseline / f'{prefix}_albedo.png').convert('RGB'), float) / 255)
        orm = np.asarray(Image.open(baseline / f'{prefix}_orm.png').convert('RGB'), float) / 255
        colour, rough, metal = calibrated_brass(cavity, edge, noise, prefix == 'aged')
        albedo = np.where(enamel[:, :, None], original * enamel_gain, colour)
        orm[:, :, 1] = np.where(enamel, enamel_roughness, rough)
        orm[:, :, 2] = np.where(enamel, 0, metal)
        exposed = occupied & ~enamel & (cavity < .01) & (edge < .01)
        rows, cols = slice(1792, 2048), slice(1725, 1981)
        assert not occupied[rows, cols].any(), 'Suspender rectangle overlaps accepted atlas'
        albedo[rows, cols] = np.median(albedo[exposed], axis=0)
        orm[rows, cols] = np.median(orm[exposed], axis=0)
        save(output / f'{prefix}_albedo.png', albedo, True)
        save(output / f'{prefix}_orm.png', orm)
        shutil.copyfile(baseline / f'{prefix}_normal.png', output / f'{prefix}_normal.png')
        report[prefix] = {'exposed_effective_linear_rgb': albedo[exposed].mean(0).tolist(),
                          'roughness_p10_p50_p90': np.percentile(orm[:, :, 1][exposed], [10, 50, 90]).tolist(),
                          'metallic_p10_p50_p90': np.percentile(orm[:, :, 2][exposed], [10, 50, 90]).tolist()}
    normal, rough, fibre = photo_ribbon()
    save(output / 'ribbon_weave_normal.png', normal * .5 + .5)
    save(output / 'ribbon_weave_roughness.png', np.repeat(rough[:, :, None], 3, 2))
    save(output / 'ribbon_weave_albedo.png', np.repeat(fibre[:, :, None], 3, 2), True)
    (output / 'finish.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for key in ['bakes', 'baseline', 'output']:
        p.add_argument('--' + key, type=Path, required=True)
    p.add_argument('--enamel-roughness', type=float, default=.25)
    p.add_argument('--enamel-gain', type=float, default=.7)
    a = p.parse_args()
    finish(a.bakes.resolve(), a.baseline.resolve(), a.output.resolve(), a.enamel_roughness, a.enamel_gain)
