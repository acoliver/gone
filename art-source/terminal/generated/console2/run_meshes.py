from pathlib import Path
import json, os, subprocess, time
root = Path('art-source/terminal/generated/console2')
port = Path('/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d')
python = port / '.venv/bin/python'
base = [str(python), str(port / 'generate.py'), '--model-path', str(port / 'weights/Hunyuan3D-2mv'), '--subfolder', ' hunyuan3d-dit-v2-mv'.strip(), '--dtype', 'float16', '--steps', '30', '--guidance-scale', '5.0', '--octree-resolution', '384']
jobs = [('console-s510-rgba.png', 410), ('console-s510-rgba.png', 411), ('console-s510-rgba.png', 412), ('console-s513-rgba.png', 410), ('keyboard-s520-rgba.png', 410), ('keyboard-s520-rgba.png', 411)]
env = dict(os.environ, HF_HOME='/Volumes/XS1000/hf-cache', HF_HUB_OFFLINE='1', PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1')
records=[]
manifest=root/'mesh-runs.json'
for image, seed in jobs:
    name=f'{Path(image).stem}-{seed}'
    out=root/'meshes'/f'{name}.glb'
    logpath=root/'logs'/f'mesh-{name}.log'
    cmd=base+['--front',str(root/'inputs'/image),'--seed',str(seed),'--out',str(out)]
    started=time.monotonic()
    print(f'START {name}', flush=True)
    with logpath.open('w') as log:
        result=subprocess.run(cmd,cwd=port,env=env,stdout=log,stderr=subprocess.STDOUT)
    record={'name':name,'input':image,'seed':seed,'seconds':round(time.monotonic()-started,2),'returncode':result.returncode,'mesh':str(out.relative_to(root)) if out.exists() else None,'log':str(logpath.relative_to(root))}
    records.append(record)
    manifest.write_text(json.dumps(records,indent=2)+'\n')
    print(json.dumps(record),flush=True)
    if result.returncode:
        raise SystemExit(result.returncode)
