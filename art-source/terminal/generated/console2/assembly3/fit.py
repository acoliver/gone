import bpy,json,sys
from pathlib import Path
O=Path(__file__).resolve().parent;sys.path.insert(0,str(O))
from placement import place
bpy.ops.wm.open_mainfile(filepath=str(O/'deformed.blend'))
r=json.loads((O/'geometry-report.json').read_text());place(O,r)
print('FIT_PASSED',flush=True)
