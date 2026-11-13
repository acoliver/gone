from pathlib import Path
import os, json, subprocess, shlex, time
from PIL import Image, ImageDraw, ImageFont, ImageOps
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
PORT=Path('/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d')
PY=str(PORT/'.venv/bin/python')
FLUX='/Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit'
BLENDER='/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender'
for d in ['logs','cache/numba','cache/matplotlib','cache/tmp','cache/xdg']:
 (ROOT/d).mkdir(parents=True,exist_ok=True)
ENV=dict(os.environ,HF_HOME='/Volumes/XS1000/hf-cache',HF_HUB_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',NUMBA_CACHE_DIR=str(ROOT/'cache/numba'),MPLCONFIGDIR=str(ROOT/'cache/matplotlib'),TMPDIR=str(ROOT/'cache/tmp'),XDG_CACHE_HOME=str(ROOT/'cache/xdg'),OMP_NUM_THREADS='8')
def dump(p,x): Path(p).write_text(json.dumps(x,indent=2)+'\n')
def note(s):
 with (ROOT/'recipe.md').open('a') as f:f.write(s+'\n\n')
def fail(x):
 p=ROOT/'failures.json'; xs=json.loads(p.read_text()) if p.exists() else []; xs.append(x);dump(p,xs)
def queue_gpu():
 # Shape/image jobs are serialized across sessions; CPU simulation/rendering is not a Metal inference job.
 while True:
  out=subprocess.check_output(['ps','-axo','pid=,command='],text=True)
  busy=[]
  for line in out.splitlines():
   line=line.strip();parts=line.split(None,1)
   if len(parts)!=2:continue
   pid,cmd=parts
   if int(pid)==os.getpid():continue
   if ('/bin/python' in cmd or 'python3 ' in cmd or '/mflux-generate-' in cmd) and any(s in cmd for s in ['generate.py --','paint.py --','mflux-generate-flux','mflux-generate-z-image']):busy.append(line)
  if not busy:return
  print('QUEUE foreign inference '+str(busy),flush=True);time.sleep(45)
def run(name,args,gpu=False,cwd=None):
 args=list(map(str,args));log=ROOT/'logs'/f'{name}.log'
 if gpu:queue_gpu()
 note(f'## {name}\n\nWorking directory: `{cwd or ROOT}`\n\n```sh\n'+ ' '.join(f'{k}={shlex.quote(ENV[k])}' for k in ['HF_HOME','HF_HUB_OFFLINE','PYTHONDONTWRITEBYTECODE','NUMBA_CACHE_DIR','MPLCONFIGDIR','TMPDIR','XDG_CACHE_HOME'])+' '+shlex.join(args)+'\n```')
 print('START',name,flush=True);t=time.monotonic()
 with log.open('w') as f:
  p=subprocess.Popen(args,cwd=cwd or ROOT,env=ENV,stdout=f,stderr=subprocess.STDOUT)
  dump(ROOT/'active-job.json',{'name':name,'pid':p.pid,'log':str(log)})
  rc=p.wait()
 row={'name':name,'argv':args,'returncode':rc,'seconds':round(time.monotonic()-t,2),'log':str(log)}
 with (ROOT/'commands.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
 note(f'Return code {rc}; duration {row["seconds"]} seconds; log `{log.relative_to(ROOT)}`.')
 if rc:fail(row)
 print('END',name,row,flush=True)
 return rc==0
CONCEPTS=[('Selected concept 202',REPO/'tmp/ceiling-concepts/beam-armoured-strip/seed-202_seed_202.png'),('Isolated beam 210',REPO/'tmp/ceiling-models/refine/beam/seed-210.png')]
def sheet(rows,path,cols=4,tw=540,th=390):
 canvas=Image.new('RGB',(cols*tw,((len(rows)+cols-1)//cols)*th),(37,39,41));d=ImageDraw.Draw(canvas);font=ImageFont.truetype('/System/Library/Fonts/Menlo.ttc',15)
 for i,(label,p) in enumerate(rows):
  x=i%cols*tw;y=i//cols*th;d.text((x+8,y+8),label,fill='white',font=font)
  if p and Path(p).exists():
   with Image.open(p) as im:
    if im.mode=='RGBA':
     bg=Image.new('RGBA',im.size,(235,235,235,255));im=Image.alpha_composite(bg,im)
    im=ImageOps.contain(im.convert('RGB'),(tw-12,th-45));canvas.paste(im,(x+(tw-im.width)//2,y+38+(th-45-im.height)//2))
 canvas.save(path,quality=93)
 return canvas.size
