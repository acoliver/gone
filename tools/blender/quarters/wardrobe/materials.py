"""Generate and measure wardrobe face images without reconstructing their wear."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / 'art-source/quarters/wardrobe'
SCRATCH = ROOT / 'tmp/mat1/wardrobe'
RUNTIME = ROOT / 'assets/props/quarters'
sys.path.insert(0, str(ROOT / 'tools/quarters_aging'))
from bake_finishes import design_paint
from colour import linear
from locker_faces import paint_fields, scores, eligible
from locker_gates import hsv
from select_locker_faces import calibrate, from_lab
from colour import lab

FACES = {
    'door-outer': dict(size=[.95, 1.98], pixels=[736, 1536], crop=[817, 119, 890, 352], hatch=True),
    'door-inner': dict(size=[.95, 1.98], pixels=[736, 1536], crop=[817, 119, 890, 352], hatch=True),
    'left': dict(size=[.65, 2.2], pixels=[448, 1536], crop=[445, 338, 535, 411]),
    'right': dict(size=[.65, 2.2], pixels=[448, 1536], crop=[704, 273, 831, 319]),
    'back': dict(size=[.952, 2.2], pixels=[672, 1536], crop=[817, 119, 890, 352], hatch=True),
    'top': dict(size=[.952, .626], pixels=[672, 448], crop=[656, 272, 720, 304]),
    'bottom': dict(size=[.952, .626], pixels=[672, 448], crop=[656, 272, 720, 304]),
    'frame': dict(size=[.08, 2.2], pixels=[64, 1536], crop=[438, 259, 459, 319]),
    'hardware': dict(size=[.2, .2], pixels=[512, 512], crop=[550, 814, 806, 1032], hatch=True),
    'left-inner': dict(size=[.65, 2.2], pixels=[448, 1536], crop=[445, 338, 535, 411]),
    'right-inner': dict(size=[.65, 2.2], pixels=[448, 1536], crop=[704, 273, 831, 319]),
    'ceiling': dict(size=[.952, .626], pixels=[672, 448], crop=[656, 272, 720, 304]),
    'header': dict(size=[.952, .06], pixels=[768, 64], crop=[438, 259, 841, 274]),
}


def measure(image, reference, face):
    result = scores(image, reference, face)
    result['no_green'] = green_fraction(image)
    result['pixels_per_metre'] = float(min(np.array(image.size) / face['size']))
    colour = np.asarray(image.convert('RGB'), float) / 255
    smooth = np.asarray(image.convert('RGB').filter(ImageFilter.GaussianBlur(result['pixels_per_metre'] * .003)), float) / 255
    h, w = colour.shape[:2]
    difference = (colour - smooth)[h//5:4*h//5, w//5:4*w//5]
    result['broad_high_frequency'] = float(np.sqrt(np.mean(difference**2)))
    return result


def calibrate_means(image, reference, contrast=1):
    observed = lab(np.asarray(image.convert('RGB'), float) / 255)
    expected = lab(np.asarray(reference.convert('RGB'), float) / 255)
    source_paint = paint_fields(image)[1] >= .5
    target_paint = paint_fields(reference)[1] >= .5
    pairs = [(source_paint, target_paint), (~source_paint, ~target_paint)]
    if any(not a.any() or not b.any() for a, b in pairs):
        raise ValueError('mean calibration requires both pigment classes')
    source = np.array([observed[a].mean(0) for a, _ in pairs])
    target = np.array([expected[b].mean(0) for _, b in pairs])
    difference = source[0] - source[1]
    projected = np.outer(difference, difference) / np.dot(difference, difference)
    # Preserve pigment means without forcing quiet paint to inherit source grain.
    matrix = (np.eye(3) + np.outer(target[0]-target[1]-difference, difference) / np.dot(difference, difference)
              + (contrast-1)*(np.eye(3)-projected))
    centre, desired = source.mean(0), target.mean(0)
    colour = from_lab((observed-centre) @ matrix.T + desired)
    result = Image.fromarray(np.uint8(np.round(colour*255)))
    return result, dict(method='global Lab affine fitted to pigment means; no spatial masks',
                        lab_affine_matrix=matrix.tolist(), lab_input_centre=centre.tolist(),
                        lab_output_centre=desired.tolist(), perpendicular_contrast=contrast)


def face_passes(row, hardware=False):
    return eligible(row, hardware) and row['no_green'] < .005 and row['pixels_per_metre'] >= 600


def green_fraction(image):
    hue, saturation, _ = hsv(np.asarray(image.convert('RGB'), float) / 255)
    return float(((hue >= 70) & (hue <= 170) & (saturation > .23)).mean())


def channels(image, metres, hardware):
    colour, paint = paint_fields(image)
    height = paint * .0015
    if hardware:
        luminance = linear(colour) @ [.2126, .7152, .0722]
        height = (luminance - luminance.mean()) * .0003
    dy, dx = np.gradient(height)
    density = np.array(image.size) / metres
    normal = np.dstack([-dx * density[0], dy * density[1], np.ones_like(dx)])
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    albedo = np.dstack([colour, 1 - paint])
    orm = np.dstack([np.ones_like(paint), .91 * (1 - paint) + .69 * paint,
                    np.zeros_like(paint), np.zeros_like(paint)])
    normal = np.dstack([normal * .5 + .5, np.ones_like(paint)])
    return tuple(Image.fromarray(np.uint8(np.round(np.clip(data, 0, 1) * 255)))
                 for data in (albedo, normal, orm))


def prepare():
    SOURCE.mkdir(parents=True, exist_ok=True)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    for name, face in FACES.items():
        concept = 'docs/art/corridors/hatch-concept-rusted.png' if face.get('hatch') else 'docs/art/quarters/concept-now.png'
        crop = Image.open(ROOT / concept).convert('RGB').crop(face['crop'])
        crop.save(SOURCE / f'{name}-source.png')
        crop.resize(face['pixels'], Image.Resampling.LANCZOS).save(SOURCE / f'{name}-input.png')
        prompt = (
            'Edit the reference into a flat, evenly lit, shadowless, edge-to-edge aged painted steel material image. '
            'Preserve the reference muted grey-green paint and reddish brown iron oxides. '
            'This is one complete face of a wardrobe aboard a sealed sterile dry oxygenated ship after 1000 years. '
            'No mould, moss, vegetation or biological decay. Remove hardware, seams, perspective and cast shadows. '
            'Do not draw an object, frame or a border. Preserve ragged irregular paint-loss boundaries. '
            'Paint fails most at the outer edges and corners, with isolated worn fixture outlets. '
            'Keep the broad central painted field quiet, with sparse different-sized irregular corrosion patches. '
            'A few narrow rusty trails descend from fixture outlets with gently wandering paths and tapered ends. '
            'No straight stripes, geometric cutouts, regular blotches or repeating motifs. ')
        if name in ('top', 'bottom'):
            prompt += ('This face is horizontal. No downward trails. A fine soft even low-contrast warm grey dust veil '
                       'lies over the paint and corrosion. No cloudy patches, swirls, drifts or stains. ')
        if name == 'ceiling':
            prompt += ('This face is the downward-facing interior roof. No settled dust or vertical runoff. '
                       'Preserve the quiet old paint and irregular edge corrosion. ')
        if name == 'hardware':
            prompt = ('Remove all hardware, objects, seams, borders, perspective and shadows. Preserve the extensive '
                      'dark reddish brown rust and orange corrosion of this reference. Fill the whole image with '
                      'only continuous flat heavily corroded steel, lit flat and evenly. Fine irregular pits and '
                      'dark cavities intermix with orange oxide and small grey metal flecks. No repeating shapes. '
                      'Sealed sterile dry oxygenated ship after 1000 years; no biological growth. ')
        if name.startswith('door'):
            prompt += ('This full upright leaf has faint narrow rusty runs under small vent outlets in the upper quarter '
                       'and one recessed latch near mid-height, without drawing the hardware. ')
        if name == 'header':
            prompt = ('Edit this reference into a flat evenly lit grey-green painted steel material image. '
                      'The image covers a horizontal strip 0.952 metres wide and 0.06 metres tall. '
                      'Retain the muted grey paint and dark reddish brown iron oxide palette. '
                      'Small broken irregular chips and oxide patches cluster close to the upper and lower edges '
                      'and at the two end corners, leaving the broad middle painted. '
                      'No continuous border, frame, dark stripe or wide rust band. No vertical trails. '
                      'Intact paint has slow gentle uneven pigment variation, not speckles, plaster or pebbles. '
                      'Do not draw an object, seam, hardware, perspective or shadows. '
                      'Sealed sterile dry oxygenated ship after 1000 years. No biological growth or saturated green. ')
        (SOURCE / f'{name}-prompt.txt').write_text(prompt.rstrip() + '\n')
    (SOURCE / 'face-layout.json').write_text(json.dumps(dict(
        faces=FACES, paint_height_m=.0015, hardware_pitch_m=.2,
        mapping='Direct whole-face projection in each mesh local frame; no procedural wear composition',
        clean_paint_srgb=design_paint().tolist()), indent=2) + '\n')


def generate(names, count, offset):
    prepare()
    for index, (name, face) in enumerate(FACES.items()):
        if names and name not in names:
            continue
        for seed in range(97000 + index * 100 + offset, 97000 + index * 100 + offset + count):
            output = SOURCE / f'{name}-{seed}.png'
            if output.exists():
                if not output.with_suffix('.metadata.json').exists():
                    raise ValueError(f'incomplete generation: {output}')
                continue
            command = ['/Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit',
                       '--model', 'flux2-klein-4b', '--quantize', '4', '--steps', '4',
                       '--image-paths', str(SOURCE / f'{name}-input.png'),
                       '--prompt-file', str(SOURCE / f'{name}-prompt.txt'), '--seed', str(seed),
                       '--width', str(face['pixels'][0]), '--height', str(face['pixels'][1]), '--output', str(output)]
            print('GENERATE', name, seed, flush=True)
            with (SCRATCH / f'{name}-{seed}.log').open('w') as log:
                subprocess.run(command, cwd=ROOT, check=True, stdout=log, stderr=subprocess.STDOUT,
                               env=dict(os.environ, HF_HOME='/Volumes/XS1000/hf-cache', HF_HUB_OFFLINE='1',
                                        PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(SCRATCH)))
            image = Image.open(output).convert('RGB')
            if image.size != tuple(face['pixels']):
                raise ValueError(f'wrong generated size: {image.size}')
            metadata = dict(seed=seed, face=name, model='black-forest-labs/FLUX.2-klein-4B',
                            steps=4, quantize=4, command=command, crop=face['crop'],
                            prompt=(SOURCE / f'{name}-prompt.txt').read_text(),
                            reference=f'{name}-source.png', input=f'{name}-input.png')
            output.with_suffix('.metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
            print('GENERATED', name, seed, flush=True)


def mute_green(image):
    colour = np.asarray(image.convert('RGB'), float) / 255
    hue, saturation, value = hsv(colour)
    selected = (hue >= 70) & (hue <= 170) & (saturation > .23)
    gain = np.minimum(1., .225 / np.maximum(saturation, 1e-6))
    muted = value[..., None] - (value[..., None] - colour) * gain[..., None]
    colour[selected] = muted[selected]
    return Image.fromarray(np.uint8(np.round(colour * 255)))


def select(names):
    selection_path = SOURCE / 'selection.json'
    selection = json.loads(selection_path.read_text()) if selection_path.exists() else {}
    candidates_path = SOURCE / 'candidate-scores.json'
    candidates = json.loads(candidates_path.read_text()) if candidates_path.exists() else {}
    for name, face in FACES.items():
        if names and name not in names:
            continue
        reference = Image.open(SOURCE / f'{name}-source.png').convert('RGB')
        rejected = {path.name: json.loads(path.with_suffix('.metadata.json').read_text()).get('visual_rejection')
                    for path in SOURCE.glob(name + '-[0-9]*.png') if path.stem.rsplit('-', 1)[1].isdigit()}
        rows = [dict(row, eligible=False, visual_rejection=rejected[row['raw']])
                for row in candidates.get(name, []) if rejected.get(row['raw'])]
        for path in sorted(SOURCE.glob(name + '-[0-9]*.png')):
            if not path.stem.rsplit('-', 1)[1].isdigit():
                continue
            raw = Image.open(path).convert('RGB')
            metadata = json.loads(path.with_suffix('.metadata.json').read_text())
            if metadata.get('visual_rejection'):
                continue
            seed = metadata['seed']
            for amount in (0., .33, .67, 1.):
                input_image = raw
                if amount:
                    a, b = lab(np.asarray(raw) / 255), lab(np.asarray(reference) / 255)
                    quantiles = np.linspace(0, 1, 257)
                    corrected = np.stack([np.interp(a[..., c], np.quantile(a[..., c], quantiles),
                                                    np.quantile(b[..., c], quantiles)) for c in range(3)], -1)
                    input_image = Image.fromarray(np.uint8(np.round(from_lab(a + (corrected-a)*amount) * 255)))
                chosen = f'{path.stem}-grade{round(amount*100)}.png'
                cached = next((row for row in candidates.get(name, []) if row['chosen'] == chosen), None)
                if cached is not None and (SOURCE / chosen).exists():
                    image = Image.open(SOURCE / chosen).convert('RGB')
                    calibration = cached['calibration']
                else:
                    image, calibration = calibrate(input_image, reference)
                image = mute_green(image)
                image.save(SOURCE / chosen)
                values = measure(image, reference, face)
                row = dict(seed=seed, raw=path.name, chosen=chosen, calibration=calibration,
                           quantile_amount=amount, scores=values,
                           eligible=face_passes(values, name == 'hardware'))
                rows.append(row)
                print('SCORE', name, seed, amount, row['eligible'], values, flush=True)
            if name != 'hardware':
                for contrast in (1, 2, 4, 6):
                    image, calibration = calibrate_means(raw, reference, contrast)
                    image = mute_green(image)
                    chosen = f'{path.stem}-means{contrast}.png'
                    image.save(SOURCE / chosen)
                    values = measure(image, reference, face)
                    row = dict(seed=seed, raw=path.name, chosen=chosen, calibration=calibration,
                               scores=values, eligible=face_passes(values))
                    rows.append(row)
                    print('MEANS', name, seed, contrast, row['eligible'], values, flush=True)
                grades = [row for row in rows if row['raw'] == path.name and 'quantile_amount' in row]
                for base in grades:
                    image = Image.open(SOURCE / base['chosen']).convert('RGB')
                    for radius in (.6, 1., 1.5):
                        denoised = mute_green(image.filter(ImageFilter.GaussianBlur(radius)))
                        chosen = Path(base['chosen']).stem + f'-denoise{radius:g}.png'
                        denoised.save(SOURCE / chosen)
                        values = measure(denoised, reference, face)
                        row = dict(base, chosen=chosen, scores=values, eligible=face_passes(values),
                                   denoise_radius_px=radius,
                                   denoise_radius_m=radius/values['pixels_per_metre'])
                        rows.append(row)
                        print('DENOISE', name, seed, radius, row['eligible'], values, flush=True)
        if not rows:
            raise ValueError(f'no generated images: {name}')
        candidates[name] = rows
        valid = [row for row in rows if row['eligible']]
        if valid:
            chosen = min(valid, key=lambda row: sum(v for k, v in row['scores'].items() if k.endswith('delta_e'))
                         + abs(row['scores']['broad_rust']-.15)*15
                         + (0 if name == 'hardware' else row['scores']['broad_high_frequency'] * 1000))
            selection[name] = chosen
            print('SELECTED', name, chosen['seed'], flush=True)
        else:
            selection.pop(name, None)
            print('NO PASSING CANDIDATE', name, flush=True)
        candidates_path.write_text(json.dumps(candidates, indent=2) + '\n')
        selection_path.write_text(json.dumps(selection, indent=2) + '\n')
    missing = set(FACES) - selection.keys()
    if missing:
        raise SystemExit('Missing passing faces: ' + ', '.join(sorted(missing)))
    pack(selection)
    print('ALL FACES PACKED', flush=True)


def pack(selection):
    rectangles = {
        'door-outer': [8, 8, 744, 1544], 'door-inner': [760, 8, 1496, 1544],
        'left': [1512, 8, 1960, 1544], 'right': [4, 1560, 452, 3096],
        'back': [460, 1560, 1132, 3096], 'frame': [1976, 8, 2040, 1544],
        'top': [8, 3112, 680, 3560], 'bottom': [696, 3112, 1368, 3560],
        'hardware': [1384, 3112, 1896, 3624],
        'left-inner': [1140, 1560, 1588, 3096],
        'right-inner': [1596, 1560, 2044, 3096],
        'ceiling': [8, 3576, 680, 4024],
        'header': [696, 3640, 1464, 3704],
    }
    atlases = [np.zeros((4096, 2048, 4), np.uint8) for _ in range(3)]
    for name, row in selection.items():
        image = Image.open(SOURCE / row['chosen']).convert('RGB')
        x0, y0, x1, y1 = rectangles[name]
        for atlas, channel in zip(atlases, channels(image, FACES[name]['size'], name == 'hardware')):
            atlas[y0-4:y1+4, x0-4:x1+4] = np.pad(np.asarray(channel), ((4, 4), (4, 4), (0, 0)), mode='edge')
    for kind, data in zip(('albedo', 'normal', 'orm'), atlases):
        Image.fromarray(data).save(RUNTIME / f'wardrobe_aged_{kind}.png')
    layout = json.loads((SOURCE / 'face-layout.json').read_text())
    for name, rectangle in rectangles.items():
        layout['faces'][name]['uv_rectangle'] = (np.array(rectangle) / [2048, 4096, 2048, 4096]).tolist()
    (SOURCE / 'face-layout.json').write_text(json.dumps(layout, indent=2) + '\n')
    (HERE / 'material-layout.json').write_text(json.dumps(layout, indent=2) + '\n')
    Image.new('RGB', (4, 4), tuple(np.uint8(np.round(design_paint()*255)))).save(RUNTIME / 'wardrobe_as_built_paint.png')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'generate', 'select'])
    parser.add_argument('--face', action='append', choices=list(FACES))
    parser.add_argument('--count', type=int, default=4)
    parser.add_argument('--offset', type=int, default=0)
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare()
    elif args.action == 'generate':
        generate(args.face, args.count, args.offset)
    else:
        select(args.face)


if __name__ == '__main__':
    main()
