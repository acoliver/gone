from pathlib import Path
import subprocess,os,time,json,shutil
OUT=Path(__file__).resolve().parent;PORT=Path('/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d');PY=str(PORT/'.venv/bin/python');BLENDER='/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender';env=dict(os.environ,HF_HOME='/Volumes/XS1000/hf-cache',HF_HUB_OFFLINE='1',PYTHONUNBUFFERED='1',PYTHONDONTWRITEBYTECODE='1')
while True:
 scores=json.loads((OUT/'shape-scores.json').read_text()) if (OUT/'shape-scores.json').exists() else []
 if len(scores)==2:break
 time.sleep(30)
choice=json.loads((OUT/'chosen-shape.json').read_text());D=OUT/f"mesh-{choice['seed']}"
for name in ['height.npz','segmentation.npz','matching.json','segmentation.png']:shutil.copy2(D/name,OUT/name)
records=[]
def run(name,cmd,cwd=OUT):
 start=time.monotonic();print('START',name,flush=True)
 with (OUT/f'{name}.log').open('w') as log:r=subprocess.run(cmd,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT)
 record={'stage':name,'exit':r.returncode,'seconds':round(time.monotonic()-start,1)};records.append(record);(OUT/'finishing-runs.json').write_text(json.dumps(records,indent=2));print(record,flush=True)
 if r.returncode:raise SystemExit(r.returncode)
run('paint',[PY,'paint.py','--mesh',str(D/'paint-input.glb'),'--image',str(OUT/'reference-rgba.png'),'--out',str(OUT/'painted-raw.glb'),'--texture-size','2048','--resolution','512','--seed','531','--save-views',str(OUT/'paint-views.png')],PORT)
run('prepare',[BLENDER,'--background','--factory-startup','--python',str(OUT/'prepare.py')])
if not (OUT/'uv.blend').exists():raise RuntimeError('Prepare failed before saving UV blend')
run('atlas',[PY,str(OUT/'atlas.py')])
run('finish',[BLENDER,'--background','--factory-startup','--python',str(OUT/'finish.py')])
if not (OUT/'side.png').exists():raise RuntimeError('Finishing did not produce all renders')
run('contact',[PY,str(OUT/'contact.py')])
print('COMPLETE',flush=True)
