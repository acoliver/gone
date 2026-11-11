"""#130 dry-air oxide film over exposed brass, with deeper protected tarnish."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def linear(rgb):
    return np.where(rgb <= .04045, rgb / 12.92, ((rgb + .055) / 1.055) ** 2.4)


def save(path, value, colour=False):
    if colour:
        value = np.where(value <= .0031308, value * 12.92, 1.055 * np.maximum(value, 0) ** (1 / 2.4) - .055)
    Image.fromarray(np.uint8(np.clip(value, 0, 1) * 255 + .5)).save(path)


def filtered_detail_normal(normal, geometry):
    result = geometry + gaussian_filter(normal - geometry, sigma=(3, 3, 0))
    return result / np.linalg.norm(result, axis=2, keepdims=True)


def finish(bakes, output, normal_source):
    output.mkdir(parents=True, exist_ok=True)
    master = ROOT / 'assets/props/quarters/dress_uniform/medal'
    fields = np.load(bakes / 'material-fields.npz')
    enamel = np.flipud(fields['enamel'])
    convex = np.flipud(fields['convex'])
    cavity = np.flipud(fields['tarnish'])
    mask = np.flipud(fields['mask']) & ~enamel
    edge = np.clip((convex - .12) / .4, 0, 1)
    base = linear(np.asarray(Image.open(bakes / 'as_built_untarnished_albedo.png').convert('RGB'), float) / 255)
    report = {}
    for prefix in ['as_built', 'aged']:
        orm = np.asarray(Image.open(bakes / (prefix + '_untarnished_orm.png')).convert('RGB'), float) / 255
        albedo = base.copy()
        calibration = .13 if prefix == 'as_built' else .15
        untreated = base.copy()
        control_orm = orm.copy()
        untreated_rough = orm[:, :, 1].copy()
        if prefix == 'as_built':
            untreated *= .76
            untreated_rough = np.maximum(.34, untreated_rough + .09) * .6
        untreated = np.where(enamel[:, :, None], base, untreated * calibration)
        control_orm[:, :, 1] = np.where(enamel, orm[:, :, 1] + .035, untreated_rough)
        if prefix == 'aged':
            # Thin oxide preserves the conductor underneath; opaque oxide is confined to recesses.
            film = base * np.array([.45, .49, .62])
            film = film * (1 - .20 * edge[:, :, None]) + base * .64 * (.20 * edge[:, :, None])
            albedo = np.where(enamel[:, :, None], base, film)
            rough = .535 - .075 * edge + (orm[:, :, 1] - .385) * .35
            metal = .89 + .045 * edge
            stain = cavity
            oxide = np.array([.032, .020, .009])
            rough = rough * (1 - stain) + .72 * stain
            metal = metal * (1 - stain) + .025 * stain
        else:
            albedo = np.where(enamel[:, :, None], base, base * .76)
            rough = np.maximum(.34, orm[:, :, 1] + .09)
            metal = orm[:, :, 2]
            stain = cavity * .10
            oxide = np.array([.065, .039, .014])
            rough = rough * (1 - stain) + .48 * stain
            metal = metal * (1 - stain) + .025 * stain
        albedo = np.where(enamel[:, :, None], albedo, albedo * (1 - stain[:, :, None]) + oxide * stain[:, :, None])
        # Calibrate conductor reflectance to the unchanged high-energy direct rig.
        # Keep the hue and metallic mask; attenuation is confined to brass, not enamel.
        albedo = np.where(enamel[:, :, None], albedo, albedo * calibration)
        if prefix == 'as_built':
            rough *= .6
        orm[:, :, 1] = np.where(enamel, orm[:, :, 1] + .035, rough)
        orm[:, :, 2] = np.where(enamel, 0, metal)
        # Reserved empty atlas rectangle, UV pixels x=1725..1981, y=0..256.
        rows, cols = slice(1792,2048), slice(1725,1981)
        assert not np.flipud(fields['mask'])[rows,cols].any(), 'Suspender atlas rectangle overlaps the accepted bake'
        exposed = mask & (cavity < .01) & (convex < .12)
        untreated[rows,cols] = np.median(untreated[exposed],axis=0)
        control_orm[rows,cols] = np.median(control_orm[exposed],axis=0)
        save(output / (prefix + '_untarnished_albedo.png'), untreated, True)
        save(output / (prefix + '_untarnished_orm.png'), control_orm)
        albedo[rows,cols] = np.median(albedo[exposed],axis=0)
        orm[rows,cols] = np.median(orm[exposed],axis=0)
        normal = np.asarray(Image.open(normal_source / (prefix + '_normal.png')).convert('RGB')).copy()
        if prefix == 'as_built':
            # Filter only fine finish; retain the high-to-low geometric normal bake.
            geometry = np.asarray(Image.open(bakes / 'geometry_runtime_normal.png').convert('RGB'), float) / 127.5 - 1
            filtered = filtered_detail_normal(normal.astype(float) / 127.5 - 1, geometry)
            filtered = np.uint8(np.clip(filtered * .5 + .5, 0, 1) * 255 + .5)
            normal = np.where(mask[:, :, None], filtered, normal)
        normal[rows,cols] = [128,128,255]
        Image.fromarray(normal).save(master / (prefix + '_normal.png'))
        save(master / (prefix + '_albedo.png'), albedo, True)
        save(master / (prefix + '_orm.png'), orm)
        report[prefix] = {'linear_reflectance_calibration': calibration, 'exposed_linear_rgb': albedo[exposed].mean(0).tolist(), 'roughness_percentiles': np.percentile(orm[:, :, 1][mask], [0, 50, 100]).tolist(),
                          'metallic_percentiles': np.percentile(orm[:, :, 2][mask], [0, 50, 100]).tolist()}
    # A periodic woven tile, filtered in the runtime shader at minification.
    y, x = np.mgrid[:256, :256] / 256
    warp = np.sin(x * 16 * 2 * np.pi)
    weft = np.sin(y * 16 * 2 * np.pi)
    parity = np.cos(x * 8 * 2 * np.pi) * np.cos(y * 8 * 2 * np.pi)
    nx = .14 * warp * (.6 + .4 * parity)
    ny = .11 * weft * (.6 - .4 * parity)
    normal = np.stack([nx, ny, np.sqrt(1 - nx * nx - ny * ny)], -1) * .5 + .5
    save(master / 'ribbon_weave_normal.png', normal)
    rough = .52 + .065 * parity + .025 * warp * weft
    save(master / 'ribbon_weave_roughness.png', np.repeat(rough[:, :, None], 3, 2))
    fibre = .97 + .015 * parity + .005 * warp * weft
    save(master / 'ribbon_weave_albedo.png', np.repeat(fibre[:, :, None], 3, 2), True)
    (output / 'finish.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bakes', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--normal-source', type=Path, required=True)
    a = p.parse_args()
    finish(a.bakes.resolve(), a.output.resolve(), a.normal_source.resolve())
