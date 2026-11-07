import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
HY = Path('/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d')
PY = HY / '.venv/bin/python'
FLUX = '/Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit'
BLENDER = '/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender'
SOURCE = PROJECT / 'docs/art/corridors/hatch-concept-rusted.png'
OBJECTS = {
    'upper-strap-hinge': {'crop': [850, 185, 1080, 395], 'description': 'the same upper strap hinge, its mounting plate and vertical knuckle barrel together as one whole object', 'flux_seed': 590},
    'latch-dog': {'crop': [380, 200, 565, 350], 'description': 'the same upper latch dog, its horizontal handle lug and keeper together as one whole object', 'flux_seed': 591},
    'handwheel': {'crop': [490, 340, 890, 740], 'description': 'the same handwheel, its circular rim, six spokes and central hub together as one whole object', 'flux_seed': 592},
}


def environment():
    env = dict(os.environ)
    paths = {'HOME': 'cache/home', 'XDG_CACHE_HOME': 'cache/xdg', 'TMPDIR': 'cache/tmp', 'NUMBA_CACHE_DIR': 'cache/numba', 'MPLCONFIGDIR': 'cache/matplotlib', 'BLENDER_USER_CONFIG': 'cache/blender/config', 'BLENDER_USER_SCRIPTS': 'cache/blender/scripts', 'BLENDER_USER_DATAFILES': 'cache/blender/datafiles'}
    for key, value in paths.items():
        path = ROOT / value
        path.mkdir(parents=True, exist_ok=True)
        env[key] = str(path)
    env.update(HF_HOME='/Volumes/XS1000/hf-cache', HF_HUB_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1', PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1', U2NET_HOME='/Users/acoliver/.u2net')
    return env


def record(text):
    with (ROOT / 'recipe.md').open('a') as out:
        out.write(text + '\n')


def command(label, args, env, timeout):
    log = ROOT / 'logs' / (label + '.log')
    keys = ['HOME', 'XDG_CACHE_HOME', 'TMPDIR', 'NUMBA_CACHE_DIR', 'MPLCONFIGDIR', 'BLENDER_USER_CONFIG', 'BLENDER_USER_SCRIPTS', 'BLENDER_USER_DATAFILES', 'HF_HOME', 'HF_HUB_OFFLINE', 'HF_HUB_DISABLE_TELEMETRY', 'PYTHONDONTWRITEBYTECODE', 'PYTHONUNBUFFERED', 'U2NET_HOME']
    invocation = ' '.join(k + '=' + shlex.quote(env[k]) for k in keys) + ' ' + shlex.join([str(x) for x in args])
    record(f'\n## {label}\n\n```sh\ncd {shlex.quote(str(ROOT))}\n{invocation} > {shlex.quote(str(log))} 2>&1\n```')
    print('START', label, flush=True)
    started = time.monotonic()
    with log.open('w') as output:
        try:
            result = subprocess.run([str(x) for x in args], cwd=ROOT, env=env, stdout=output, stderr=subprocess.STDOUT, timeout=timeout)
            code = result.returncode
        except subprocess.TimeoutExpired:
            output.write(f'\nOwn child exceeded {timeout} seconds; subprocess.run killed that child.\n')
            code = 124
    elapsed = time.monotonic() - started
    item = {'label': label, 'command': invocation, 'returncode': code, 'wall_seconds': elapsed, 'log': str(log)}
    with (ROOT / 'commands.jsonl').open('a') as out:
        out.write(json.dumps(item) + '\n')
    record(f'\nReturn code {code}; wall time {elapsed:.3f} seconds; log `{log.relative_to(ROOT)}`.')
    print('END', label, code, round(elapsed, 3), flush=True)
    return item


def execute_with_metal_retry(label, args, env, timeout):
    attempts = []
    for attempt in range(2):
        result = command(f'{label}-attempt{attempt + 1}', args, env, timeout)
        attempts.append(result)
        if result['returncode'] == 0:
            return attempts
        message = Path(result['log']).read_text(errors='replace').lower()
        metal_failure = any(x in message for x in ['metal', 'command buffer', 'gpu timeout', 'gpu hang']) or result['returncode'] == 124
        if attempt == 0 and metal_failure:
            record('\nMetal failure or stalled GPU process: wait 60 seconds, then retry once with the same settings.')
            print('WAIT 60', label, flush=True)
            time.sleep(60)
        else:
            break
    return attempts


def prepare():
    from PIL import Image
    for name in ['inputs', 'meshes', 'renders', 'sheets', 'logs']:
        (ROOT / name).mkdir(parents=True, exist_ok=True)
    env = environment()
    (ROOT / '.gdignore').write_text('')
    (ROOT / 'recipe.md').write_text('# Whole-object door hardware prototype\n\nAll output is private to this directory. No game or tracked files changed. No generated mesh cleanup, fitting, squashing, texturing or quality judgments. The driver judges the images.\n\nRead: driver-notes.md final section, leaf3 recipe and inputs, and HUNYUAN3D_WORKFLOW_ANALYSIS.md. Leaf3 used a masked crop directly, not a FLUX edit; this prototype adds the explicitly requested FLUX isolation stage.\n\nSource: `' + str(SOURCE) + '`. Crop boxes below are source pixels, half-open xyxy; RGB crops are copied without resampling. The upper latch dog is selected around source y 225..325; the crop includes its keeper. Crops are generous to include the hinge barrel and all wheel geometry.\n\nFLUX.2-klein-4b, 4-bit, 4 steps, output 768x768, seeds 590/591/592. The preserved edit RGB is matted with existing U2-Net weights for Hunyuan; both edit and RGBA input are saved. Hunyuan full non-turbo, front only, float16, 30 steps, CFG 5, requested octree 512, seeds 600..603 per object. A failed 512 run falls back to 384 after the single Metal retry where applicable. Each subprocess wall time includes model load and export. Timeout 1800 seconds per shape/edit attempt.\n\nCPU Cycles clay renders: neutral grey, three area lights, orthographic front/30/60/90 degrees. Meshes are rendered without geometry edits. Comparison sheets put the concept crop at left and the four seeds to its right, front row then 30-degree row.\n\nPreparation/orchestration command:\n```sh\nPYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python -B ' + str(ROOT / 'run.py') + ' prepare\nPYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 nohup /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python -B ' + str(ROOT / 'run.py') + ' all > ' + str(ROOT / 'logs/driver.log') + ' 2>&1 &\n```\n\nHelper implementations: `run.py`, `matte.py`, `render.py`. U2-Net and Hugging Face caches are read from existing external caches. Writable home, temporary files, Blender and Python caches are redirected here. Foreign GPU work may contend; no foreign process is signalled.\n')
    image = Image.open(SOURCE).convert('RGB')
    assert image.size == (1199, 1312)
    for name, spec in OBJECTS.items():
        folder = ROOT / 'inputs' / name
        folder.mkdir(exist_ok=True)
        image.crop(spec['crop']).save(folder / 'concept-crop.png')
        prompt = f"Isolate {spec['description']} from the reference image. Same object, isolated, plain grey background, no other parts. Keep its exact shape, proportions, orientation and mechanical details. Remove the door, wall and surrounding hardware; show only this complete object centered with a clear margin on all sides."
        spec['prompt'] = prompt
        (folder / 'prompt.txt').write_text(prompt + '\n')
        record(f'\n## Input {name}\n\nCrop: `{spec["crop"]}`. PIL operation: `Image.open(SOURCE).convert("RGB").crop({spec["crop"]}).save("inputs/{name}/concept-crop.png")`.\n\nPrompt: {prompt}\n\nFLUX seed: {spec["flux_seed"]}; Hunyuan seeds: 600, 601, 602, 603.')
    (ROOT / 'inputs/specs.json').write_text(json.dumps(OBJECTS, indent=2))
    print('PREPARED', flush=True)


def mesh_stats(path):
    import numpy as np
    import trimesh
    mesh = trimesh.load(path, force='mesh', process=False)
    bounds = mesh.bounds
    extents = mesh.extents
    components = trimesh.graph.connected_components(mesh.face_adjacency, nodes=np.arange(len(mesh.faces)), min_len=1)
    return {'triangles': len(mesh.faces), 'vertices': len(mesh.vertices), 'bounds_xyz': bounds.tolist(), 'extents_xyz': extents.tolist(), 'aspect_ratios': {'width_over_height': float(extents[0] / extents[1]), 'depth_over_height': float(extents[2] / extents[1]), 'width_over_depth': float(extents[0] / extents[2]), 'longest_over_shortest': float(extents.max() / extents.min())}, 'connected_components': len(components), 'component_triangles_descending': sorted((len(c) for c in components), reverse=True), 'axes': 'glTF: x width, y height, z depth; face-adjacency components without mesh cleanup'}


def sheets():
    from PIL import Image, ImageDraw, ImageOps
    for name in OBJECTS:
        cell, header, rowlabel = 420, 76, 30
        canvas = Image.new('RGB', (5 * cell, header + 2 * (cell + rowlabel)), '#e0e0e0')
        draw = ImageDraw.Draw(canvas)
        draw.text((18, 12), name + ': concept at left; raw untextured meshes; no visual assessment', fill='black', font_size=22)
        for col, title in enumerate(['Concept crop', 'Seed 600', 'Seed 601', 'Seed 602', 'Seed 603']):
            draw.text((col * cell + 16, 48), title, fill='black', font_size=20)
        for row, angle in enumerate([0, 30]):
            y = header + row * (cell + rowlabel)
            draw.text((16, y + 4), 'Front' if angle == 0 else '30 degrees', fill='black', font_size=18)
            for col in range(5):
                file = ROOT / 'inputs' / name / 'concept-crop.png' if col == 0 else ROOT / 'renders' / f'{name}-s{599 + col}' / f'clay-{angle:03d}.png'
                image = Image.open(file).convert('RGBA')
                tile = Image.new('RGBA', (cell - 16, cell - 16), '#eeeeee')
                image.thumbnail(tile.size, Image.Resampling.LANCZOS)
                tile.alpha_composite(image, ((tile.width - image.width) // 2, (tile.height - image.height) // 2))
                canvas.paste(tile.convert('RGB'), (col * cell + 8, y + rowlabel + 8))
        canvas.save(ROOT / 'sheets' / f'{name}-comparison.png')


def run_all():
    env = environment()
    specs = json.loads((ROOT / 'inputs/specs.json').read_text())
    results = {'settings': {'model': 'Hunyuan3D-2mv full non-turbo', 'view': 'front only', 'steps': 30, 'cfg': 5, 'requested_octree_resolution': 512, 'seeds': [600, 601, 602, 603]}, 'inputs': specs, 'runs': [], 'issues': [], 'edits': []}
    def save():
        (ROOT / 'stats.json').write_text(json.dumps(results, indent=2))
    for name, spec in specs.items():
        folder = ROOT / 'inputs' / name
        args = [FLUX, '--model', 'flux2-klein-4b', '--quantize', '4', '--steps', '4', '--seed', str(spec['flux_seed']), '--image-paths', folder / 'concept-crop.png', '--prompt', spec['prompt'], '--width', '768', '--height', '768', '--metadata', '--output', folder / 'isolated.png']
        attempts = execute_with_metal_retry(f'flux-{name}', args, env, 1800)
        results['edits'].append({'object': name, 'attempts': attempts})
        save()
        if attempts[-1]['returncode'] != 0:
            raise RuntimeError(f'FLUX failed for {name}')
        matte = command(f'matte-{name}', [PY, '-B', ROOT / 'matte.py', folder / 'isolated.png', folder / 'front-rgba.png'], env, 300)
        if matte['returncode'] != 0:
            raise RuntimeError(f'Matting failed for {name}')
    (ROOT / 'INPUTS_READY').write_text('Three FLUX edits and U2-Net RGBA inputs saved.\n')
    for name in specs:
        for seed in range(600, 604):
            output = ROOT / 'meshes' / f'{name}-s{seed}.glb'
            attempts = []
            for resolution in [512, 384]:
                args = [PY, '-B', HY / 'generate.py', '--model-path', HY / 'weights/Hunyuan3D-2mv', '--subfolder', 'hunyuan3d-dit-v2-mv', '--front', ROOT / 'inputs' / name / 'front-rgba.png', '--dtype', 'float16', '--steps', '30', '--guidance-scale', '5', '--octree-resolution', str(resolution), '--seed', str(seed), '--out', output]
                current = execute_with_metal_retry(f'shape-{name}-s{seed}-r{resolution}', args, env, 1800)
                for attempt in current:
                    attempt['octree_resolution'] = resolution
                attempts.extend(current)
                if current[-1]['returncode'] == 0:
                    break
                results['issues'].append({'object': name, 'seed': seed, 'resolution': resolution, 'attempts': current, 'action': 'fallback to 384' if resolution == 512 else 'generation failed'})
                save()
            if attempts[-1]['returncode'] != 0:
                raise RuntimeError(f'Shape failed for {name} seed {seed}')
            stats = mesh_stats(output)
            stats.update(object=name, seed=seed, mesh=str(output), octree_resolution=resolution, wall_seconds=attempts[-1]['wall_seconds'], total_attempt_wall_seconds=sum(a['wall_seconds'] for a in attempts), attempts=attempts)
            results['runs'].append(stats)
            save()
            render = command(f'render-{name}-s{seed}', [BLENDER, '--background', '--factory-startup', '--threads', '8', '--python-exit-code', '1', '--python', ROOT / 'render.py', '--', output, ROOT / 'renders' / f'{name}-s{seed}'], env, 600)
            if render['returncode'] != 0:
                raise RuntimeError(f'Render failed for {name} seed {seed}')
            stats['render_wall_seconds'] = render['wall_seconds']
            save()
    sheets()
    record('\n## Completion\n\nTwelve raw meshes, forty-eight clay renders, three comparison sheets and stats.json produced. No visual assessment performed. See stats.json and commands.jsonl for exact timings, attempts and resolution per run.\n')
    (ROOT / 'READY_TO_VERIFY').write_text('All generation and renders finished; verify before DONE.\n')
    print('READY_TO_VERIFY', flush=True)


if __name__ == '__main__':
    try:
        if sys.argv[1] == 'prepare':
            prepare()
        elif sys.argv[1] == 'all':
            run_all()
        else:
            raise ValueError(sys.argv[1])
    except Exception:
        import traceback
        (ROOT / 'FAILED').write_text(traceback.format_exc())
        raise
