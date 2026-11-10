import bpy,sys
from pathlib import Path
O=Path(__file__).resolve().parent;sys.path.insert(0,str(O))
from placement import place
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'finish4/console.blend'))
place(O,{})
print('FIT_PASSED',flush=True)
