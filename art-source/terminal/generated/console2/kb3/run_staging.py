from pathlib import Path
import subprocess,time,json
OUT=Path(__file__).resolve().parent
BLENDER='/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender'
PY='/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python'
for seed in [410,411]:
 while True:
  records=json.loads((OUT/'shape-runs.json').read_text()) if (OUT/'shape-runs.json').exists() else []
  found=[r for r in records if r['seed']==seed]
  if found:
   if found[0]['exit']:raise SystemExit(found[0]['exit'])
   break
  time.sleep(30)
 with (OUT/f'stage-{seed}.log').open('w') as log:r=subprocess.run([BLENDER,'--background','--factory-startup','--python',str(OUT/'stage_shape.py'),'--',str(seed)],stdout=log,stderr=subprocess.STDOUT)
 print('STAGE',seed,r.returncode,flush=True)
 if r.returncode:raise SystemExit(r.returncode)
with (OUT/'score-shapes.log').open('w') as log:r=subprocess.run([PY,str(OUT/'score_shapes.py')],stdout=log,stderr=subprocess.STDOUT)
print('SCORES',r.returncode,flush=True)
if r.returncode:raise SystemExit(r.returncode)
