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


def brass_finish(base, original_roughness, cavity, edge, aged):
    variation = np.clip(base / np.array([.66, .43, .14]), .85, 1.15)
    physical = variation * np.array([.90, .64, .24])
    brushing = (original_roughness - .30) * .65
    rough = np.clip(.43 - .10 * edge + brushing, .30, .45)
    if aged:
        film = variation * np.array([.46, .265, .082])
        colour = film * (1 - .25 * edge[:, :, None]) + physical * (.25 * edge[:, :, None])
        rough = np.clip(rough + .10 - .025 * edge, .39, .58)
        metallic = .94 + .035 * edge
        stain = cavity
        oxide = np.array([.045, .022, .006])
    else:
        colour = physical
        metallic = np.full_like(rough, .985)
        stain = cavity * .10
        oxide = np.array([.12, .063, .020])
    colour = colour * (1 - stain[:, :, None]) + oxide * stain[:, :, None]
    rough = rough * (1 - stain) + (.72 if aged else .48) * stain
    metallic = metallic * (1 - stain) + .025 * stain
    return colour, rough, metallic


def ribbon_weave():
    y, x = np.mgrid[:256, :256] / 256
    warp = np.sin(x * 32 * 2 * np.pi)
    rib = np.sin(y * 16 * 2 * np.pi)
    crossing = np.cos(x * 16 * 2 * np.pi) * np.cos(y * 16 * 2 * np.pi)
    nx = .055 * warp * (.8 + .2 * crossing)
    ny = .32 * rib * (.9 + .1 * crossing)
    normal = np.stack([nx, ny, np.sqrt(1 - nx * nx - ny * ny)], -1)
    rough = .43 + .09 * np.cos(y * 16 * 2 * np.pi) + .025 * crossing
    fibre = .965 + .025 * np.cos(y * 16 * 2 * np.pi) + .01 * crossing
    return normal, rough, fibre


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
        untreated, untreated_rough, _ = brass_finish(base, orm[:, :, 1], np.zeros_like(cavity), edge, False)
        albedo, rough, metal = brass_finish(base, orm[:, :, 1], cavity, edge, prefix == 'aged')
        untreated = np.where(enamel[:, :, None], base, untreated)
        control_orm = orm.copy()
        control_orm[:, :, 1] = np.where(enamel, orm[:, :, 1] + .035, untreated_rough)
        control_orm[:, :, 2] = np.where(enamel, 0, .985)
        albedo = np.where(enamel[:, :, None], base, albedo)
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
        report[prefix] = {'exposed_linear_rgb': albedo[exposed].mean(0).tolist(), 'roughness_percentiles': np.percentile(orm[:, :, 1][mask], [0, 50, 100]).tolist(),
                          'metallic_percentiles': np.percentile(orm[:, :, 2][mask], [0, 50, 100]).tolist()}
    normal, rough, fibre = ribbon_weave()
    save(master / 'ribbon_weave_normal.png', normal * .5 + .5)
    save(master / 'ribbon_weave_roughness.png', np.repeat(rough[:, :, None], 3, 2))
    save(master / 'ribbon_weave_albedo.png', np.repeat(fibre[:, :, None], 3, 2), True)
    (output / 'finish.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bakes', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--normal-source', type=Path, required=True)
    a = p.parse_args()
    finish(a.bakes.resolve(), a.output.resolve(), a.normal_source.resolve())
