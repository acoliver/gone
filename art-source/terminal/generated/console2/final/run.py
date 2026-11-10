from pathlib import Path
import subprocess,sys
O=Path(__file__).resolve().parent;B='/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender';P='/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python'
steps=[('geometry.py','GEOMETRY_DONE'),('fit.py','FIT_DONE'),('bake.py','BAKES_DONE'),('build.py','BUILD_DONE'),('verify_scene.py','SCENE_DONE'),('validate.py','VALIDATE_DONE')]
if len(sys.argv)>1:steps=steps[next(i for i,(s,m) in enumerate(steps) if s==sys.argv[1]):]
for script,marker in steps:
 print('START',script,flush=True)
 command=[P,str(O/script)] if script=='validate.py' else [B,'--background','--factory-startup','--python',str(O/script)]
 with (O/(script[:-3]+'.log')).open('w') as f:r=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT)
 text=(O/(script[:-3]+'.log')).read_text()
 if r.returncode or marker not in text or 'Traceback (most recent call last)' in text:print('FAILED',script,text[-8000:],flush=True);sys.exit(1)
 print('DONE',script,flush=True)
print('FINAL_COMPLETE',flush=True)
