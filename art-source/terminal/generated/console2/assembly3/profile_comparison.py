import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'deformed.blend'))
body=bpy.data.objects['ConsoleBody'];after=np.array([v.co[:] for v in body.data.vertices]);before=np.load(O/'source-vertices.npy');faces=np.load(O/'source-faces.npy')
np.save(O/'deformed-vertices.npy',after)
tree=BVHTree.FromPolygons(after.tolist(),faces.tolist())
r=json.loads((O/'geometry-report.json').read_text());checks=[]
for x in [-.25,-.125,0,.125,.25]:
 profile=[]
 for z in np.linspace(.28,.46,181):
  h=tree.ray_cast(Vector((x,-2,float(z))),Vector((0,1,0)))[0];assert h is not None
  profile.append(list(h))
 dy=np.diff(np.array(profile)[:,1]);assert dy.max()<.00002,'New lower-body front reversal'
 checks.append({'x_m':x,'z_range_m':[.28,.46],'samples':181,'maximum_forward_profile_reversal_mm':max(0,float(dy.max()*1000))})
r['deformation']['lower_body_front_monotonicity_checks']=checks
(O/'geometry-report.json').write_text(json.dumps(r,indent=2))
import subprocess
subprocess.run(['/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python',str(O/'draw_profile.py')],check=True)
