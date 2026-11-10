from pathlib import Path
import subprocess,os,json,time
OUT=Path(__file__).resolve().parent
PORT=Path('/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d')
env=dict(os.environ,HF_HOME='/Volumes/XS1000/hf-cache',HF_HUB_OFFLINE='1',PYTHONUNBUFFERED='1',PYTHONDONTWRITEBYTECODE='1')
records=[]
for seed in [410,411]:
 cmd=[str(PORT/'.venv/bin/python'),'generate.py','--model-path','weights/Hunyuan3D-2mv','--subfolder','hunyuan3d-dit-v2-mv','--dtype','float16','--steps','30','--guidance-scale','5.0','--octree-resolution','384','--front',str(OUT/'reference-rgba.png'),'--seed',str(seed),'--out',str(OUT/f'shape-{seed}.glb')]
 start=time.monotonic()
 with (OUT/f'shape-{seed}.log').open('w') as log:r=subprocess.run(cmd,cwd=PORT,env=env,stdout=log,stderr=subprocess.STDOUT)
 record={'seed':seed,'exit':r.returncode,'seconds':round(time.monotonic()-start,1)};records.append(record);(OUT/'shape-runs.json').write_text(json.dumps(records,indent=2));print(record,flush=True)
 if r.returncode:raise SystemExit(r.returncode)
