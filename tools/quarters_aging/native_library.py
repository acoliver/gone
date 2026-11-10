"""FLUX refinement at native production density, retaining every input and raw edit."""
import json
import os
import subprocess
import time

from steel_library import ROOT, LIBRARY, SCRATCH


def main():
    path = LIBRARY / 'manifest.json'
    manifest = json.loads(path.read_text())
    for row in manifest['faces']:
        if row.get('resolution_stage') == 'native-2x':
            continue
        name = row['id']
        source = LIBRARY / f'{name}-native-input.png'
        if not source.exists():
            source.write_bytes((LIBRARY / row['image']).read_bytes())
        output = LIBRARY / f'{name}-native-raw.png'
        prompt_path = LIBRARY / f'{name}-native-prompt.txt'
        prompt = ((LIBRARY / f'{name}-prompt.txt').read_text().rstrip()+
            '\nPreserve the grey-green paint pigment and the sparse irregular edge corrosion of the input. '
            'Refine photographic surface detail at higher native resolution. Keep most broad paint intact. '
            'Do not add large new chips, pale patches, repeated markings or coarse noise.\n')
        prompt_path.write_text(prompt)
        pixels = [v*2 for v in row['pixels']]
        seed = row['seed']+500000
        command = ['/Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit',
                   '--model', 'flux2-klein-4b', '--quantize', '4', '--steps', '4',
                   '--image-paths', str(source), '--prompt-file', str(prompt_path),
                   '--seed', str(seed), '--width', str(pixels[0]), '--height', str(pixels[1]),
                   '--output', str(output)]
        if not output.exists():
            while True:
                active = subprocess.run(['pgrep', '-f', 'mflux-generate|[g]enerate.py'], capture_output=True, text=True)
                if active.returncode == 1:
                    break
                if active.returncode != 0:
                    raise RuntimeError(active.stderr)
                print('WAIT GPU', active.stdout.strip(), flush=True)
                time.sleep(15)
            print('NATIVE', name, pixels, flush=True)
            with (SCRATCH / f'{name}-native.log').open('w') as log:
                subprocess.run(command, check=True, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                    env=dict(os.environ, HF_HOME='/Volumes/XS1000/hf-cache', HF_HUB_OFFLINE='1', TMPDIR=str(SCRATCH)))
        output.with_suffix('.metadata.json').write_text(json.dumps(dict(
            command=command, prompt=prompt, input=source.name, parent_raw=row['raw'],
            model='FLUX.2-klein-4B', quantize=4, steps=4, seed=seed, pixels=pixels), indent=2)+'\n')
        row['parent_raw'], row['raw'] = row['raw'], output.name
        row['native_input'], row['pixels'], row['resolution_stage'] = source.name, pixels, 'native-2x'
        row.pop('treatment', None)
        row.pop('neutral_refit', None)
        row['passed'] = False
        if row['kind'] == 'strip':
            row['reference'] = 'broad-neutral-source.png'
            row['palette_reference_reason'] = 'Broad panels and narrow strips share the same painted steel and oxide palette; trim crop remains the edit-layout source.'
        path.write_text(json.dumps(manifest, indent=2)+'\n')
        print('NATIVE COMPLETE', name, flush=True)


if __name__ == '__main__':
    main()
