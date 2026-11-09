"""Rasterize referenced sofa finishes into the retained geometry's atlas."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt, gaussian_filter

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'tools/quarters_aging'))
from colour import lab, linear, luminance, srgb
from locker_gates import newly_green, hsv

SOURCE = ROOT / 'art-source/quarters/sofa'
ASSETS = ROOT / 'assets/props/quarters/sofa'
SCRATCH = ROOT / 'tmp/mat/sofa'


def tileable(image):
    result = np.array(image, copy=True)
    band = min(24, min(result.shape[:2]) // 4)
    for axis in [0, 1]:
        for offset in range(band):
            a = [slice(None)] * 3
            b = a.copy()
            a[axis], b[axis] = offset, -1 - offset
            blend = .5 * (1 - offset / band)
            first, last = result[tuple(a)].copy(), result[tuple(b)].copy()
            result[tuple(a)] = first * (1 - blend) + last * blend
            result[tuple(b)] = last * (1 - blend) + first * blend
    return result


def finish_colour(base, masks, aged, kind, dust_scan=None):
    if not aged: return base.copy()
    cavity, up = masks[..., 1:2], masks[..., 2:3]
    crease = .10 * masks[..., :1] + .90 * cavity
    grime = (.55 if kind in {'fabric', 'throw'} else .18) * (1 - crease)
    dirty = base * (1 - grime)
    dust = (.85 if kind in {'fabric', 'throw'} else (.06 if kind == 'foam' else .18)) * up
    pigment = np.array([.86, .82, .74]) if dust_scan is None else dust_scan
    coverage = .3 + .7 * np.clip((np.mean(pigment, axis=-1, keepdims=True) - .5) / .45, 0, 1)
    return dirty * (1 - dust * coverage) + pigment * dust * coverage


def read(path):
    return np.asarray(Image.open(path).convert('RGB'), np.float32) / 255

def flatten_illumination(image):
    colour = linear(image)
    luminance_map = colour @ [.2126, .7152, .0722]
    yy, xx = np.mgrid[:image.shape[0], :image.shape[1]]
    design = np.stack([xx.ravel() / image.shape[1] - .5,
                       yy.ravel() / image.shape[0] - .5,
                       np.ones(xx.size)], -1)
    plane = np.linalg.lstsq(design, np.log(np.maximum(luminance_map.ravel(), 1e-6)), rcond=None)[0]
    shading = np.exp((design[:, :2] @ plane[:2]).reshape(luminance_map.shape))
    corrected = colour / shading[..., None]
    corrected *= colour.mean((0, 1)) / corrected.mean((0, 1))
    result = np.clip(srgb(corrected), 0, 1)
    before = np.linalg.lstsq(design, luminance_map.ravel(), rcond=None)[0]
    after = np.linalg.lstsq(design, luminance(result).ravel(), rcond=None)[0]
    return result, dict(log_linear_plane=plane.tolist(),
                        before_linear_gradient=float(np.linalg.norm(before[:2])),
                        after_linear_gradient=float(np.linalg.norm(after[:2])))



def weave_tile(image):
    flattened, _ = flatten_illumination(image)
    colour = linear(flattened)
    broad = gaussian_filter(colour, (6, 6, 0), mode='wrap')
    fine = colour / np.maximum(broad, 1e-6) * colour.mean((0, 1))
    return tileable(np.clip(srgb(fine), 0, 1))


def clean_metal_scan(image, palette):
    grain = luminance(weave_tile(image))
    variation = 1 + .12 * (grain / grain.mean() - 1)
    return np.clip(palette * variation[..., None], 0, 1)


def sample(image, uv, repeat=False):
    h, w = image.shape[:2]
    uv = uv % 1 if repeat else np.clip(uv, 0, 1)
    x = np.clip((uv[..., 0] * (w - 1)).astype(int), 0, w - 1)
    y = np.clip((uv[..., 1] * (h - 1)).astype(int), 0, h - 1)
    return image[y, x]


def pixels(uv, size):
    points = uv * size - .5
    low = np.maximum(np.floor(points.min(0)).astype(int), 0)
    high = np.minimum(np.ceil(points.max(0)).astype(int) + 1, size)
    yy, xx = np.mgrid[low[1]:high[1], low[0]:high[0]]
    a, b = points[1] - points[0], points[2] - points[0]
    determinant = a[0] * b[1] - a[1] * b[0]
    if abs(determinant) < 1e-10: return None
    qx, qy = xx - points[0, 0], yy - points[0, 1]
    v = (qx * b[1] - qy * b[0]) / determinant
    w = (a[0] * qy - a[1] * qx) / determinant
    u = 1 - v - w
    inside = (u >= -1e-5) & (v >= -1e-5) & (w >= -1e-5)
    return yy[inside], xx[inside], np.stack([u[inside], v[inside], w[inside]], -1)


def statistics(colour):
    colour = np.asarray(colour).reshape(-1, 3)
    return dict(srgb_mean=colour.mean(0).tolist(), srgb_std=colour.std(0).tolist(),
                lab_mean=lab(colour).mean(0).tolist(), lab_std=lab(colour).std(0).tolist(),
                linear_luminance_mean=float(luminance(colour).mean()))


def sources(state):
    aged = state == 'aged'
    names = {'fabric': 'upholstery-aged' if aged else 'upholstery-clean',
             'throw': 'throw-aged' if aged else 'throw-clean', 'foam': 'foam'}
    selected = json.loads((SOURCE / 'selected.json').read_text())
    images, calibration = {}, {}
    for kind, name in names.items():
        flattened, plane = flatten_illumination(read(SOURCE / selected[name]))
        images[kind] = tileable(flattened)
        calibration[kind] = dict(illumination=plane)
    for kind, name in names.items():
        if not aged and kind != 'foam': continue
        crop = read(SOURCE / (name + '-crop.png'))
        if kind == 'foam':
            hue, saturation, value = hsv(crop)
            target = crop[(hue >= 5) & (hue <= 45) & (saturation > .50) & (value > .15)]
            if not len(target): raise ValueError('No tan foam samples in target crop')
            target_linear = linear(np.quantile(target, .90, axis=0))
            method = 'target tan 90th percentile, saturation >0.50; exclude low-chroma warm floor and pore shadows'
        elif kind == 'throw':
            target_linear = linear(np.quantile(crop.reshape(-1, 3), .90, axis=0))
            method = 'target 90th percentile, excluding deep fold shadows'
        else:
            target_linear = linear(crop).mean((0, 1))
            method = 'mean target reflectance of the interior cloth crop'
        gain = target_linear / linear(images[kind]).mean((0, 1))
        images[kind] = np.clip(srgb(linear(images[kind]) * gain), 0, 1)
        calibration[kind].update(linear_rgb_gain=gain.tolist(), method=method, calibrated=statistics(images[kind]))
    locker = ROOT / 'art-source/quarters/locker/faces'
    selection = json.loads((locker / 'selection.json').read_text())
    images['paint'] = tileable(read(locker / selection['left']['chosen']))
    images['steel'] = tileable(read(locker / selection['hardware']['chosen']))
    if not aged:
        # The locker's clean atlas owns the painted and bare-steel palette.
        clean = read(ROOT / 'assets/props/quarters/storage_locker_module/as_built_albedo.png')
        orm = read(ROOT / 'assets/props/quarters/storage_locker_module/as_built_orm.png')
        painted = (orm[..., 2] < .1) & (clean.max(2) > .05)
        bare = (orm[..., 2] > .3) & (orm[..., 1] < .45) & (clean.max(2) > .05)
        for kind, role_mask in [('paint', painted), ('steel', bare)]:
            palette = clean[role_mask]
            if not len(palette): raise ValueError('Missing locker clean role: ' + kind)
            images[kind] = clean_metal_scan(images[kind], palette.mean(0))
    for kind in ['fabric', 'throw']:
        images[kind] = gaussian_filter(images[kind], (6, 6, 0), mode='wrap')
        calibration[kind].update(base_colour_lowpass_sigma_px=6, calibrated=statistics(images[kind]))
    if aged:
        for kind in ['paint', 'steel']:
            mean = images[kind].mean((0, 1))
            images[kind] = mean + (images[kind] - mean) * .10
    dust, plane = flatten_illumination(read(SOURCE / selected['dust']))
    gain = linear(np.array([.86, .82, .74])) / linear(dust).mean((0, 1))
    images['dust'] = tileable(np.clip(srgb(linear(dust) * gain), 0, 1))
    calibration['dust'] = dict(illumination=plane, linear_rgb_gain=gain.tolist(), calibrated=statistics(images['dust']))
    for kind, image in images.items():
        Image.fromarray(np.round(image * 255).astype(np.uint8)).save(SOURCE / (state + '-' + kind + '-source.png'))
    return images, calibration


def build(state):
    directory = SCRATCH / state
    record = json.loads((directory / 'layout.json').read_text())
    size = record['size']
    masks = np.stack([read(directory / (kind + '.png'))[::-1, :, 0] for kind in ['ao', 'cavity', 'up']], -1)
    folds = read(directory / 'fold.png')[::-1, :, 0]
    cloth_cavity = read(directory / 'cloth_cavity.png')[::-1, :, 0]
    masks[..., 1] = .35 * masks[..., 1] + .65 * folds
    masks = np.dstack([masks, np.zeros((size, size), np.float32)])
    albedo = np.zeros((size, size, 4), np.float32)
    nodust = np.zeros_like(albedo)
    normal = np.full((size, size, 3), [.5, .5, 1], np.float32)
    orm = np.full((size, size, 3), [1, 1, 0], np.float32)
    occupied = np.zeros((size, size), bool)
    surfaces, calibration = sources(state)
    report = dict(state=state, size=size, groups={}, source_statistics={}, calibration=calibration)
    selected = json.loads((SOURCE / 'selected.json').read_text())
    for name, file in selected.items():
        report['source_statistics'][name] = dict(selected=file, generated=statistics(read(SOURCE / file)),
                                                reference=statistics(read(SOURCE / (name + '-crop.png'))))
    for group in record['groups']:
        identity, kind = group['identity'], group['role']
        data = np.load(directory / (identity + '.npz'))
        original = {name: np.load(directory / file, mmap_mode='r') for name, file in group['sources'].items()}
        texture = surfaces[kind]
        for uv, old, position in zip(data['uv'], data['source_uv'], data['positions']):
            raster = pixels(uv, size)
            if raster is None: continue
            yy, xx, bary = raster
            if not len(xx): continue
            xyz = bary @ position
            face_normal = np.cross(position[1] - position[0], position[2] - position[0])
            axes = [[1, 2], [0, 2], [0, 1]][int(np.abs(face_normal).argmax())]
            physical_uv = xyz[:, axes] / .24
            if kind in {'fabric', 'throw', 'foam'}:
                x, y, w, h = group['rectangle']
                material_uv = (bary @ uv * size - [x + 8, y + 8]) / [w - 16, h - 16]
                # One full generated image per part; only the fine yarn swatch repeats.
                base = sample(texture, material_uv)
            else:
                base = sample(texture, physical_uv, True)
            if kind in {'fabric', 'throw'}:
                masks[yy, xx, 1] = .35 * cloth_cavity[yy, xx] + .65 * folds[yy, xx]
            dust_scan = sample(surfaces['dust'], physical_uv, True)
            colour = finish_colour(base, masks[yy, xx], state == 'aged', kind, dust_scan)
            alpha = sample(original['albedo'], bary @ old)[..., 3] if 'albedo' in original else np.ones(len(xx))
            albedo[yy, xx, :3], albedo[yy, xx, 3] = colour, alpha
            without_dust = masks[yy, xx, :3].copy()
            without_dust[:, 2] = 0
            nodust[yy, xx, :3] = finish_colour(base, without_dust, state == 'aged', kind, dust_scan)
            nodust[yy, xx, 3] = alpha
            masks[yy, xx, 3] = {'fabric': .1, 'throw': .3, 'foam': .5, 'paint': .7, 'steel': .9}[kind]
            if 'normal' in original:
                normal[yy, xx] = sample(original['normal'], bary @ old)[..., :3]
            if kind in {'fabric', 'throw'}:
                orm[yy, xx, 0] = folds[yy, xx]
            elif kind == 'foam':
                orm[yy, xx, 0] = .75 + .25 * masks[yy, xx, 0]
            else:
                orm[yy, xx, 0] = masks[yy, xx, 0]
            orm[yy, xx, 1] = .98 if kind in {'fabric', 'throw', 'foam'} else (.96 if state == 'aged' else (.35 if kind == 'steel' else .45))
            orm[yy, xx, 2] = 0 if state == 'aged' or kind in {'fabric', 'throw', 'foam'} else (.45 if kind == 'steel' else .02)
            occupied[yy, xx] = True
        x, y, w, h = group['rectangle']
        region = occupied[y:y+h, x:x+w] & (albedo[y:y+h, x:x+w, 3] >= .5)
        values = albedo[y:y+h, x:x+w, :3][region]
        if not len(values): raise ValueError('Empty atlas group: ' + identity)
        report['groups'][identity] = dict(role=kind, colour=statistics(values), visible_texels=int(region.sum()))
        print('RASTER', state, identity, flush=True)
    # Pad inside each assigned rectangle only; alpha padding cannot join islands.
    for group in record['groups']:
        x, y, w, h = group['rectangle']
        region = occupied[y:y+h, x:x+w]
        nearest = distance_transform_edt(~region, return_distances=False, return_indices=True)
        for array in [albedo, nodust, normal, orm, masks]:
            tile = array[y:y+h, x:x+w]
            tile[~region] = tile[nearest[0][~region], nearest[1][~region]]
    ASSETS.mkdir(parents=True, exist_ok=True)
    for kind, array in [('albedo', albedo), ('nodust', nodust), ('normal', normal), ('orm', orm), ('masks', masks)]:
        Image.fromarray(np.round(np.clip(array[::-1], 0, 1) * 255).astype(np.uint8)).save(ASSETS / (state + '_' + kind + '.png'))
    mask = occupied & (albedo[..., 3] >= .5)
    no_green = newly_green(np.zeros_like(albedo[..., :3]), albedo[..., :3], mask)
    report['no_green'] = dict(largest_region=no_green[0], total=no_green[1], threshold='<0.005', **{'pass': no_green[1] < .005})
    if not report['no_green']['pass']: raise ValueError('Sofa finish introduced green')
    report['mask_statistics'] = {name: [float(masks[..., i][mask].min()), float(masks[..., i][mask].mean()), float(masks[..., i][mask].max())] for i, name in enumerate(['ao', 'cavity', 'up'])}
    weave = weave_tile(read(SOURCE / selected['weave']))
    report['weave'] = dict(source=selected['weave'], low_frequency_normalization_sigma_px=6,
                          opposite_edge_maximum_delta=float(max(np.abs(weave[0] - weave[-1]).max(), np.abs(weave[:, 0] - weave[:, -1]).max())),
                          colour=statistics(weave))
    (SOURCE / (state + '-statistics.json')).write_text(json.dumps(report, indent=2) + '\n')
    Image.fromarray(np.round(weave * 255).astype(np.uint8)).save(ASSETS / 'weave.png')
    print('FINISHED', state, report['no_green'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', choices=['as_built', 'aged'], required=True)
    build(parser.parse_args().state)
