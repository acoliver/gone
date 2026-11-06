from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter, map_coordinates
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parent
PORT = Path('/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d')
PY = str(PORT / '.venv/bin/python')
BLENDER = '/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender'
SOURCE = ROOT.parents[2] / 'docs/art/corridors/hatch-concept-rusted.png'
CROP = (345, 40, 1075, 1120)
SEEDS = range(430, 436)
ENV_OVERRIDES = {
    'HF_HOME': str(ROOT / 'cache/huggingface'),
    'HF_HUB_OFFLINE': '1',
    'PYTHONDONTWRITEBYTECODE': '1',
    'PYTHONUNBUFFERED': '1',
    'NUMBA_CACHE_DIR': str(ROOT / 'cache/numba'),
    'MPLCONFIGDIR': str(ROOT / 'cache/matplotlib'),
    'TMPDIR': str(ROOT / 'cache/tmp'),
    'XDG_CACHE_HOME': str(ROOT / 'cache/xdg'),
    'HOME': str(ROOT / 'cache/home'),
    'BLENDER_USER_CONFIG': str(ROOT / 'cache/blender/config'),
    'BLENDER_USER_SCRIPTS': str(ROOT / 'cache/blender/scripts'),
    'BLENDER_USER_DATAFILES': str(ROOT / 'cache/blender/datafiles'),
}
ENV = dict(os.environ, **ENV_OVERRIDES)


def note(text):
    with (ROOT / 'recipe.md').open('a') as stream:
        stream.write(text + '\n\n')


def setup():
    for directory in ['inputs', 'meshes', 'renders', 'logs', *[str(Path(v).relative_to(ROOT)) for k, v in ENV_OVERRIDES.items() if str(v).startswith(str(ROOT))]]:
        (ROOT / directory).mkdir(parents=True, exist_ok=True)


def command(name, args):
    args = list(map(str, args))
    log = ROOT / 'logs' / f'{name}.log'
    env_text = ' '.join(f'{k}={shlex.quote(v)}' for k, v in ENV_OVERRIDES.items())
    note(f'### {name}\n\n```sh\ncd {shlex.quote(str(ROOT))}\n{env_text} {shlex.join(args)}\n```')
    started = time.monotonic()
    with log.open('w') as stream:
        result = subprocess.run(args, cwd=ROOT, env=ENV, stdout=stream, stderr=subprocess.STDOUT)
    entry = dict(name=name, argv=args, returncode=result.returncode, seconds=time.monotonic() - started, log=str(log))
    with (ROOT / 'commands.jsonl').open('a') as stream:
        stream.write(json.dumps(entry) + '\n')
    note(f'Return code {entry["returncode"]}; elapsed {entry["seconds"]:.2f} seconds; log `{log.relative_to(ROOT)}`.')
    print(json.dumps(entry), flush=True)
    return entry


def trace_hinges(source):
    from scipy.ndimage import median_filter
    smooth = gaussian_filter(np.asarray(source, dtype=float).mean(axis=2), 1.4)
    gy, gx = np.gradient(smooth)
    polygons, traces = [], []
    # Search windows come from the supplied hardware locations; vertices come from source gradients.
    for name, top_window, bottom_window, right_window in [
        ('upper', (210, 237), (318, 336), (1038, 1051)),
        ('lower', (766, 791), (880, 901), (1038, 1055)),
    ]:
        x0 = 982  # Overlap the fitted leaf so the union has no seam gap.
        top0 = int(np.argmax(np.abs(gy[top_window[0]:top_window[1], 995:1045]).mean(axis=1)) + top_window[0])
        bottom0 = int(np.argmax(np.abs(gy[bottom_window[0]:bottom_window[1], 995:1045]).mean(axis=1)) + bottom_window[0])
        ys = np.arange(top0, bottom0 + 1, 4)
        ys = np.unique(np.r_[ys, bottom0])
        rx = right_window[0] + np.argmin(gx[ys, right_window[0]:right_window[1]], axis=1)
        rx = median_filter(rx, size=3, mode='nearest')
        xr = int(np.median(rx))
        xs = np.unique(np.r_[np.arange(x0, xr + 1, 4), xr])
        ty = top_window[0] + np.argmax(np.abs(gy[top_window[0]:top_window[1], xs]), axis=0)
        by = bottom_window[0] + np.argmax(np.abs(gy[bottom_window[0]:bottom_window[1], xs]), axis=0)
        ty = median_filter(ty, size=3, mode='nearest')
        by = median_filter(by, size=3, mode='nearest')
        # End the column traces before the barrel edge; join using its row trace.
        top_points = [[int(x), int(y)] for x, y in zip(xs, ty) if x < min(rx)]
        bottom_points = [[int(x), int(y)] for x, y in zip(xs, by) if x < min(rx)]
        polygon = top_points + [[int(x), int(y)] for x, y in zip(rx, ys)] + bottom_points[::-1]
        polygons.append(polygon)
        traces.append(dict(name=name, top_search_y=top_window, bottom_search_y=bottom_window,
                           right_search_x=right_window, initial_top_y=top0, initial_bottom_y=bottom0,
                           polygon_source_xy=polygon))
    return polygons, traces


def prepare():
    started = time.monotonic()
    source = Image.open(SOURCE).convert('RGB')
    fit = json.loads((ROOT.parent / 'leaf2/inputs/outline.json').read_text())
    left, top, right, bottom = fit['outline_source_xyxy']
    radius = fit['corner_radius_pixels']
    polygons, traces = trace_hinges(source)
    w, h = CROP[2] - CROP[0], CROP[3] - CROP[1]
    yy, xx = np.mgrid[:h * 4, :w * 4].astype(float)
    xx = CROP[0] + (xx + 0.5) / 4
    yy = CROP[1] + (yy + 0.5) / 4
    qx = np.abs(xx - (left + right) / 2) - ((right - left) / 2 - radius)
    qy = np.abs(yy - (top + bottom) / 2) - ((bottom - top) / 2 - radius)
    sdf = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - radius
    union = sdf <= 0
    # Rasterize polygons at the same subpixel centers as the fitted outline.
    for polygon in polygons:
        inside = np.zeros_like(union)
        for (x1, y1), (x2, y2) in zip(polygon, polygon[1:] + polygon[:1]):
            if y1 == y2:
                continue
            crosses = ((y1 > yy) != (y2 > yy)) & (xx < (x2 - x1) * (yy - y1) / (y2 - y1) + x1)
            inside ^= crosses
        union |= inside
    alpha = np.rint(union.reshape(h, 4, w, 4).mean(axis=(1, 3)) * 255).astype(np.uint8)
    rgb = np.asarray(source.crop(CROP))
    rgba = np.dstack([rgb, alpha])
    source.crop(CROP).save(ROOT / 'inputs/concept-crop.png')
    Image.fromarray(alpha).save(ROOT / 'inputs/outline-mask.png')
    Image.fromarray(rgba).save(ROOT / 'inputs/concept-leaf-rgba.png')
    saved = np.asarray(Image.open(ROOT / 'inputs/concept-leaf-rgba.png'))
    assert np.array_equal(saved[:, :, :3], rgb)
    assert np.array_equal(saved[:, :, :3][alpha > 0], rgb[alpha > 0])
    bbox = Image.fromarray(alpha).getbbox()
    assert bbox[0] > 0 and bbox[1] > 0 and bbox[2] < w and bbox[3] < h
    Image.fromarray(rgba).crop(bbox).save(ROOT / 'inputs/projection-reference.png')
    result = dict(source=str(SOURCE), source_size=source.size, crop_xyxy_half_open=CROP,
        conditioning=str(ROOT / 'inputs/concept-leaf-rgba.png'),
        outline_source_xyxy=[left, top, right, bottom],
        corner_radius_pixels=radius, corner_fit_rms_pixels=fit['corner_fit_rms_pixels'],
        outline_fit_source=str(ROOT.parent / 'leaf2/inputs/outline.json'),
        hinge_traces=traces, hinge_polygons_source_xy=polygons,
        hinge_trace_method='Source RGB mean, Gaussian sigma 1.4. Supplied hinge ROIs constrain top/bottom abs vertical-gradient maxima and right negative horizontal-gradient maxima. Sample every 4 px, median filter size 3, polygon union with the fitted leaf. Numerical tracing only; no image display or visual judgement.',
        alpha_method='Exact fitted rounded-rectangle signed distance UNION hinge polygons; 4x4 subpixel-center coverage. No RGB modification, resizing, relighting or inpainting.',
        alpha_bbox_crop=bbox, foreground_fraction=float((alpha > 0).mean()),
        rgb_bytes_unchanged=True, rgb_bytes_unchanged_inside_mask=True,
        crop_clips_mask=False,
        limitation='No crop clipping. Hinge contours are numerically traced inside supplied search regions, not visually reviewed. Generated geometry and projection fidelity are unjudged. Projection retains source lighting.',
        seconds=time.monotonic() - started)
    (ROOT / 'inputs/outline.json').write_text(json.dumps(result, indent=2))
    note('## Deterministic input\n\n```json\n' + json.dumps(result, indent=2) + '\n```')
    print(json.dumps(result, indent=2), flush=True)


def measure(path):
    import trimesh
    raw = trimesh.load(str(path), force='mesh', process=False)
    mesh = trimesh.Trimesh(vertices=raw.vertices, faces=raw.faces, process=True)
    lo, hi = mesh.bounds
    extent = hi - lo
    xs = np.linspace(lo[0] + .25 * extent[0], lo[0] + .75 * extent[0], 9)
    ys = np.r_[np.linspace(lo[1] + .18 * extent[1], lo[1] + .33 * extent[1], 5), np.linspace(lo[1] + .72 * extent[1], lo[1] + .82 * extent[1], 5)]
    origins = np.array([[x, y, hi[2] + extent[2] + 1] for x in xs for y in ys])
    locations, rays, _ = mesh.ray.intersects_location(origins, np.tile([0, 0, -1.], (len(origins), 1)), multiple_hits=True)
    spans = []
    for i in np.unique(rays):
        z = np.unique(np.round(locations[rays == i, 2], 7))
        if len(z) >= 2:
            spans.append(float(z.max() - z.min()))
    components = trimesh.graph.connected_components(mesh.face_adjacency, nodes=np.arange(len(mesh.faces)), min_len=1)
    return dict(path=str(path), vertices=len(raw.vertices), faces=len(raw.faces), watertight=bool(raw.is_watertight), welded_vertices=len(mesh.vertices), welded_watertight=bool(mesh.is_watertight), bounds=raw.bounds.tolist(), extents=raw.extents.tolist(), components=len(components), largest_component_face_fraction=max(map(len, components)) / len(mesh.faces), units='native normalized Hunyuan units; no metric fitting', off_wheel_slab_ray_span=dict(median=float(np.median(spans)) if spans else None, p10=float(np.percentile(spans, 10)) if spans else None, p90=float(np.percentile(spans, 90)) if spans else None, minimum=min(spans) if spans else None, maximum=max(spans) if spans else None, valid_rays=len(spans), attempted_rays=len(origins), median_over_height=float(np.median(spans) / extent[1]) if spans else None, method='Same as previous run: frontmost minus backmost z at 90 bbox-relative samples, x=25..75%, y=18..33% and 72..82%. Intended off-wheel bands, not verified semantic segmentation. No semantic isolation of wheel or hardware is established.'))


def tile(path, label):
    font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 18)
    panel = Image.new('RGB', (512, 580), '#eeeeee')
    image = Image.open(path).convert('RGBA')
    assert image.size == (512, 512)
    background = Image.new('RGBA', image.size, '#eeeeee')
    background.alpha_composite(image)
    panel.paste(background.convert('RGB'), (0, 68))
    draw = ImageDraw.Draw(panel)
    for i, line in enumerate(label.split('\n')):
        draw.text((10, 5 + 24 * i), line, font=font, fill='black')
    return panel


def sheets(infos):
    views = [('shaded', a) for a in [0, 30, 60, 90, 180]] + [('projection', a) for a in [0, 30]]
    sheet = Image.new('RGB', (512 * 7, 580 * len(infos)), 'white')
    overview = Image.new('RGB', (512 * len(infos), 580 * 3), 'white')
    for row, info in enumerate(infos):
        seed = info['seed']
        directory = ROOT / 'renders' / f'leaf-s{seed}'
        for col, (mode, angle) in enumerate(views):
            label = f'Seed {seed} | {mode} | {angle} deg\nFull mv | front only | 30 steps | r384'
            sheet.paste(tile(directory / f'{mode}-{angle:03d}.png', label), (512 * col, 580 * row))
        for i, (mode, angle) in enumerate([('shaded', 0), ('shaded', 90), ('projection', 30)]):
            overview.paste(tile(directory / f'{mode}-{angle:03d}.png', f'Seed {seed} | {mode} | {angle} deg\nExact concept crop | no visual verdict'), (512 * row, 580 * i))
    sheet.save(ROOT / 'sheet.png')
    overview.save(ROOT / 'overview.png')
    assert Image.open(ROOT / 'sheet.png').size == (3584, 3480)
    assert Image.open(ROOT / 'overview.png').size == (3072, 1740)


def generate():
    for seed in SEEDS:
        target = ROOT / 'meshes' / f'leaf-s{seed}.glb'
        if target.exists():
            raise FileExistsError(f'Refusing to overwrite {target}')
        command(f'shape-{seed}', [PY, PORT / 'generate.py', '--model-path', PORT / 'weights/Hunyuan3D-2mv', '--subfolder', 'hunyuan3d-dit-v2-mv', '--front', ROOT / 'inputs/concept-leaf-rgba.png', '--dtype', 'float16', '--steps', '30', '--guidance-scale', '5', '--octree-resolution', '384', '--seed', seed, '--out', target])


def finish():
    infos = []
    for seed in SEEDS:
        path = ROOT / 'meshes' / f'leaf-s{seed}.glb'
        if not path.exists():
            continue
        started = time.monotonic()
        info = measure(path)
        info['seed'] = seed
        info['measurement_seconds'] = time.monotonic() - started
        for mode in ['shaded', 'projection']:
            args = [BLENDER, '--background', '--factory-startup', '--threads', '8', '--python-exit-code', '1', '--python', ROOT / 'blender_render.py', '--', path, ROOT / 'renders' / f'leaf-s{seed}', mode]
            if mode == 'projection':
                args.append(ROOT / 'inputs/projection-reference.png')
            command(f'render-{seed}-{mode}', args)
        infos.append(info)
        (ROOT / 'stats.json').write_text(json.dumps(infos, indent=2))
    sheets(infos)
    commands = [json.loads(line) for line in (ROOT / 'commands.jsonl').read_text().splitlines()]
    totals = {stage: sum(c['seconds'] for c in commands if c['name'].startswith(stage)) for stage in ['shape', 'render']}
    summary = dict(meshes=infos, seconds_by_stage=totals, failed_commands=[c for c in commands if c['returncode'] != 0], sheets=[str(ROOT / 'sheet.png'), str(ROOT / 'overview.png')], input_limitation=json.loads((ROOT / 'inputs/outline.json').read_text())['limitation'], visual_judgments=False, production_fit=False)
    (ROOT / 'summary.json').write_text(json.dumps(summary, indent=2))
    note('## Completion\n\n```json\n' + json.dumps(summary, indent=2) + '\n```\n\nNo smoothing, decimation, component removal, learned paint, side conditioning or source modification. Five shaded views and two concept-projection views per seed. Each image panel is 512 pixels high plus 68 pixels of labels. The crop includes the complete fitted outline and traced hinge extensions with margin. These are generated scratch candidates, with no visual verdict or production approval. No lighting flattening was applied.')
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    setup()
    mode = sys.argv[1]
    if mode in ['prepare', 'all']:
        prepare()
    if mode in ['generate', 'all']:
        generate()
    if mode in ['finish', 'all']:
        finish()
