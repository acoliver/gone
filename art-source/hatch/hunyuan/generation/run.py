from __future__ import annotations
import json, os, shlex, subprocess, sys, time
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parent
PORT = Path('/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d')
PY = str(PORT / '.venv/bin/python')
FLUX = '/Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit'
BLENDER = '/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender'
SOURCE = ROOT.parents[1] / 'docs/art/corridors/hatch-concept-rusted.png'
ENV = dict(os.environ, HF_HOME='/Volumes/XS1000/hf-cache', HF_HUB_OFFLINE='1', PYTHONDONTWRITEBYTECODE='1', NUMBA_CACHE_DIR=str(ROOT/'cache/numba'), MPLCONFIGDIR=str(ROOT/'cache/matplotlib'), TMPDIR=str(ROOT/'cache/tmp'), PYTHONUNBUFFERED='1')
RECORD = ROOT/'commands.jsonl'

def note(text):
    with (ROOT/'recipe.md').open('a') as f: f.write(text+'\n\n')

def run(name, args, timeout=1500, metal_retry=True):
    for attempt in range(1, 3 if metal_retry else 2):
        log = ROOT/'logs'/f'{name}-{attempt}-{time.monotonic_ns()}.log'
        cmd = shlex.join([str(x) for x in args])
        note(f'### {name}, attempt {attempt}\n\n```sh\ncd {shlex.quote(str(ROOT))}\nHF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR={ROOT}/cache/numba MPLCONFIGDIR={ROOT}/cache/matplotlib TMPDIR={ROOT}/cache/tmp {cmd}\n```')
        start = time.monotonic()
        with log.open('w') as f:
            try:
                p = subprocess.run(args, cwd=ROOT, env=ENV, stdout=f, stderr=subprocess.STDOUT, timeout=timeout)
                code = p.returncode
            except subprocess.TimeoutExpired:
                code = -999
        elapsed = time.monotonic()-start
        entry = dict(name=name, attempt=attempt, argv=[str(x) for x in args], seconds=elapsed, returncode=code, log=str(log))
        with RECORD.open('a') as f: f.write(json.dumps(entry)+'\n')
        note(f'Return code {code}; elapsed {elapsed:.2f} seconds; log `{log.relative_to(ROOT)}`.')
        print(json.dumps(entry), flush=True)
        if code == 0: return True
        text = log.read_text(errors='replace').lower()
        metal = code == -999 or any(word in text for word in ['metal', 'command buffer', 'gpu timeout'])
        if attempt == 1 and metal and metal_retry:
            note('Metal error or command hang: wait 60 seconds, then retry once. Only this runner\'s timed-out child was terminated.')
            time.sleep(60)
        else: return False
    return False

def matte(path, out):
    image = np.array(Image.open(path).convert('RGB'))
    # The edited backgrounds are requested to be white; only near-white low-chroma regions are keyed.
    white = (image.min(2) >= 235) & ((image.max(2).astype(int)-image.min(2).astype(int)) <= 18)
    labels, count = ndimage.label(white)
    sizes = np.bincount(labels.ravel()); sizes[0] = 0
    background_labels = np.flatnonzero(sizes >= 48)
    alpha = np.where(np.isin(labels, background_labels), 0, 255).astype('uint8')
    Image.fromarray(np.dstack([image,alpha])).save(out)
    fill = float((alpha>0).mean())
    center = float((alpha[alpha.shape[0]//3:2*alpha.shape[0]//3,alpha.shape[1]//3:2*alpha.shape[1]//3]>0).mean())
    return dict(path=str(out), foreground_fraction=fill, central_third_foreground_fraction=center, alpha_bbox=Image.fromarray(alpha).getbbox())

def inputs():
    for folder in ['inputs','prompts','logs','meshes','renders','cache/numba','cache/matplotlib','cache/tmp']:
        (ROOT/folder).mkdir(parents=True,exist_ok=True)
    if not (ROOT/'weights').exists(): (ROOT/'weights').symlink_to(PORT/'weights',target_is_directory=True)
    if not (ROOT/'recipe.md').exists():
        note('# GONE Hunyuan hatch prototype\n\nAll generated files and temporary caches are under this directory. The port source and game files are not modified. No Era3D or Instant-NSR is used. No visual judgments are made. Commands are serialized, including all paint jobs. Timings are measured wall-clock seconds.\n\nRun from this directory with the port Python: `'+PY+' '+str(ROOT/'run.py')+' inputs`, then `shape`, then `finish`. Or use `all`.\n\nFull shape model: hunyuan3d-dit-v2-mv, fp16, 30 steps, CFG 5.0, octree 384, seeds 410/411/412/413. A paired seed-410 front+left trial is added per category. Native model coordinates are x=horizontal, y=up, z=front, with no assumed physical units. No geometry smoothing, decimation, or component removal.\n\nPaint selection is provisional and numerical: watertight first, then alpha-silhouette IoU, then largest-component face fraction. This cannot certify semantic fidelity or mechanical usability. Driver inspection is required. Every mesh gets concept-derived front-projection texture; selected two per category also get Hunyuan Paint with default 50-step Delight, paint resolution 768 and texture 2048.\n\nA/B slab thickness is measured by front-to-back ray intersections through off-wheel interior patches, excluding silhouette/hardware bands; statistics describe ray span, not a guaranteed separated semantic slab. C has no leaf, so leaf thickness is not applicable.\n\nPreparation command:\n```sh\n'+PY+' '+str(ROOT/'run.py')+' inputs\n```')
    image = Image.open(SOURCE)
    image.crop((255,25,985,1050)).save(ROOT/'inputs/concept-assembly-crop.png')
    image.crop((365,77,875,960)).save(ROOT/'inputs/concept-leaf-crop.png')
    prompts = {
      'A': 'Isolate the entire closed ship hatch assembly from this reference: the rounded rectangular riveted outer frame ring, the closed rusted olive grey steel door leaf, circular central handwheel, hinges on the right, latch dogs on the left. Remove the surrounding wall, floor, background, pipes and everything outside the outer frame. Preserve the exact reference proportions, hardware positions and extensive rust and peeling paint. Straight-on orthographic front view, vertical upright, whole assembly fully visible with a generous margin on all sides, flat even lighting, plain pure white background, no ground plane, no shadows, no text.',
      'B': 'Extract only the closed rusted steel door LEAF from this reference, including its circular handwheel, hinges attached on its RIGHT edge and latch dogs on its LEFT edge. Completely remove the outer riveted frame ring, surrounding wall and floor. The leaf is a tall rounded rectangle door slab. Retain its proportions, original rust and peeling olive grey paint and all leaf-mounted hardware. Straight-on orthographic front view of the detached door leaf, upright, entire slab and hardware fully visible with generous white margins. Pure white background with no shadows, no wall, no mounting frame, no text.',
      'C': 'Extract only the OUTER FRAME RING of this ship hatch from the reference. REMOVE the entire door slab, circular wheel and all door hardware. Show an EMPTY OPEN rounded rectangular steel riveted perimeter frame with a large pure white open hole through its centre. Retain the narrow thick raised corroded olive grey riveted rim and the right-side hinge mounting plates of the frame. No door, no wheel, no solid panel inside the frame, no wall, no floor. Straight-on orthographic front product view of the empty frame, upright, whole ring fully visible with generous pure white margins. Pure white background and pure white centre opening, flat even lighting, no shadows or text.'
    }
    results = {}
    for cat,prompt in prompts.items():
        prompt_path=ROOT/'prompts'/f'{cat}-front.txt'; prompt_path.write_text(prompt+'\n')
        out=ROOT/'inputs'/f'{cat}-front.png'
        source=ROOT/'inputs'/('concept-leaf-crop.png' if cat=='B' else 'concept-assembly-crop.png')
        if not out.exists():
            ok=run(f'flux-{cat}-front',[FLUX,'--model','flux2-klein-4b','--quantize','4','--steps','4','--width','768','--height','1024','--seed','310','--image-paths',str(source),'--prompt-file',str(prompt_path),'--metadata','--output',str(out)])
            if not ok: continue
        results[cat]=matte(out,ROOT/'inputs'/f'{cat}-front-rgba.png')
        if cat=='C' and results[cat]['central_third_foreground_fraction'] > 0.15:
            note('C front edit did not yield a numerically empty centre. Retry with an explicit empty-ring edit; this is a mask check, not a visual judgment.')
            retry_prompt=ROOT/'prompts/C-empty.txt'
            retry_prompt.write_text('Remove absolutely everything inside the frame opening: all solid steel, door, slab, wheel, centre panel, mechanism. Replace the entire inside area with pure white empty background. Keep ONLY the narrow outer rounded rectangular riveted perimeter steel frame, and its right hinge attachment plates. A hollow open frame ring with an empty white hole occupying most of its interior. Keep the same upright front view and pure white background.\n')
            retry_out=ROOT/'inputs/C-front-empty.png'
            if not retry_out.exists(): run('flux-C-empty',[FLUX,'--model','flux2-klein-4b','--quantize','4','--steps','4','--width','768','--height','1024','--seed','311','--image-paths',str(out),'--prompt-file',str(retry_prompt),'--output',str(retry_out)])
            if retry_out.exists():
                results[cat]=matte(retry_out,ROOT/'inputs/C-front-rgba.png')
            if results[cat]['central_third_foreground_fraction'] > 0.15:
                results[cat]['skip_reason']='FLUX did not produce a sufficiently empty frame opening (central-third foreground > 15%); no C shapes generated.'
                note(results[cat]['skip_reason']); continue
        side_prompt=ROOT/'prompts'/f'{cat}-left.txt'
        side_prompt.write_text('Show the EXACT same isolated '+ {'A':'closed hatch and outer frame assembly','B':'detached door leaf without a frame','C':'empty open hatch frame ring without a door'}[cat]+' from its strict LEFT SIDE, a 90 degree orthographic side view, edge-on, not an oblique view. Preserve its vertical height, rust and olive grey paint, hardware and proportions. The steel '+('frame has an open centre and a shallow mounting flange' if cat=='C' else 'door is a thin slab with the handwheel protruding only forward, hinges on the far right edge and latch dogs on its left edge')+'. The slab thickness is about one twentieth of its height, not a deep box. Entire object fully in frame with generous margins. Pure white background, no wall, no shadows, no text. Do not show the broad front face.\n')
        side=ROOT/'inputs'/f'{cat}-left.png'
        if not side.exists(): run(f'flux-{cat}-left',[FLUX,'--model','flux2-klein-4b','--quantize','4','--steps','4','--width','768','--height','1024','--seed','320','--image-paths',str(out if cat!='C' or not (ROOT/'inputs/C-front-empty.png').exists() else ROOT/'inputs/C-front-empty.png'),'--prompt-file',str(side_prompt),'--metadata','--output',str(side)])
        if side.exists(): results[cat]['left']=matte(side,ROOT/'inputs'/f'{cat}-left-rgba.png')
    (ROOT/'inputs.json').write_text(json.dumps(results,indent=2))
    note('Input alpha diagnostics:\n```json\n'+json.dumps(results,indent=2)+'\n```\nNear-white key: RGB minimum >=235, chroma range <=18, white connected region at least 48 pixels. Interior white regions are also removed so C retains its opening. Input images must be inspected by the driver; mask checks do not establish semantic correctness.')

def shape():
    config=json.loads((ROOT/'inputs.json').read_text())
    for cat,entry in config.items():
        if 'skip_reason' in entry: continue
        for seed,multi in [(410,False),(411,False),(412,False),(413,False),(410,True)]:
            if multi and 'left' not in entry: continue
            name=f'{cat}-s{seed}-'+('mv' if multi else 'sv')
            target=ROOT/'meshes'/f'{name}.glb'
            if target.exists(): continue
            args=[PY,str(PORT/'generate.py'),'--model-path',str(PORT/'weights/Hunyuan3D-2mv'),'--subfolder','hunyuan3d-dit-v2-mv','--front',entry['path'],'--dtype','float16','--steps','30','--guidance-scale','5','--octree-resolution','384','--seed',str(seed),'--out',str(target)]
            if multi: args+=['--left',entry['left']['path']]
            run('shape-'+name,args)

if __name__=='__main__':
    mode=sys.argv[1]
    if mode in ('inputs','all'): inputs()
    if mode in ('shape','all'): shape()
    if mode in ('finish','all'):
        import finish
        finish.main()
