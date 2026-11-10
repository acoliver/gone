from pathlib import Path
import subprocess,sys
O=Path(__file__).resolve().parent
B='/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender'
P='/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python'
steps=[('geometry.py','geometry.log','GEOMETRY_REPORT'),('fit.py','fit.log','FIT_PASSED'),('profile_comparison.py','profile.log','SIDE_PROFILE_COMPARISON_DONE'),('bake.py','bake.log','BAKES_DONE'),('build.py','build.log','ASSEMBLY_DONE'),('check_scene.py','scene-check.log','SCENE_CHECKS_PASSED'),('validate.py','validation.log','"validation"')]
if len(sys.argv)>1:steps=steps[next(i for i,step in enumerate(steps) if step[0]==sys.argv[1]):]
for script,log,marker in steps:
 print('START',script,flush=True)
 command=([P,str(O/script)] if script=='validate.py' else [B,'--background','--factory-startup','--python',str(O/script)])
 with (O/log).open('w') as f:result=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT)
 text=(O/log).read_text()
 if result.returncode or marker not in text or 'Traceback (most recent call last)' in text:
  print('FAILED',script,result.returncode,text[-8000:],flush=True);sys.exit(1)
 print('DONE',script,flush=True)
print('ASSEMBLY3_COMPLETE',flush=True)
