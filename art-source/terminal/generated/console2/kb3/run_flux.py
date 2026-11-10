from pathlib import Path
import json,subprocess,os,time,shutil
import numpy as np
from PIL import Image
OUT=Path(__file__).resolve().parent
for name in ['design.py','prepare.py','atlas.py','finish.py','contact.py']:
 shutil.copy2(OUT.parent/'kbfinish2'/name,OUT/name)
subprocess.run(['/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python',str(OUT/'design.py')],check=True)
r=json.loads((OUT/'reference_geometry.json').read_text());bb=np.array(r['keyboard_bounds']);lo=bb[:,:2].min(0);hi=bb[:,2:].max(0);margin=(hi-lo)*.04;crop=np.r_[np.floor(lo-margin),np.ceil(hi+margin)].astype(int)
im=Image.open(OUT.parents[1]/'kbmodel/render-top.png');im=im.crop(tuple(crop));w=1024;h=round(im.height/im.width*w/16)*16;im=im.resize((w,h),Image.Resampling.LANCZOS);im.save(OUT/'reference.png')
rects=(np.array([k['rect'] for k in r['keys']])-np.tile(crop[:2],2))*np.tile(np.array([w,h])/(crop[2:]-crop[:2]),2)
(OUT/'reference.json').write_text(json.dumps({'crop':crop.tolist(),'size':[w,h],'rects':rects.tolist()},indent=2))
prompt='Photorealistic straight top-down product photograph of exactly this military keyboard, same key layout, key count, key shapes and positions as the reference; chunky dark charcoal rubber keycaps in black rubber boots; worn olive-green painted steel frame with chips and screws; keycaps BLANK (no symbols, no letters, no numbers); plain uniform light grey background; soft even light; no shadows; nothing else.'
(OUT/'prompt.txt').write_text(prompt+'\n')
env=dict(os.environ,HF_HOME='/Volumes/XS1000/hf-cache',HF_HUB_OFFLINE='1',PYTHONUNBUFFERED='1');records=[]
for seed in range(530,534):
 target=OUT/f'flux-{seed}.png';cmd=['/Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit','--model','flux2-klein-4b','--quantize','4','--steps','8','--guidance','1.0','--width',str(w),'--height',str(h),'--seed',str(seed),'--image-paths',str(OUT/'reference.png'),'--prompt-file',str(OUT/'prompt.txt'),'--metadata','--output',str(target)]
 for attempt in range(2):
  target.unlink(missing_ok=True);start=time.monotonic()
  with (OUT/f'flux-{seed}.log').open('w') as log:result=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
  if result.returncode not in [-6,134]:break
 record={'seed':seed,'exit':result.returncode,'seconds':round(time.monotonic()-start,1),'size':[w,h]};records.append(record);(OUT/'flux-runs.json').write_text(json.dumps(records,indent=2));print(record,flush=True)
 if result.returncode:raise SystemExit(result.returncode)
