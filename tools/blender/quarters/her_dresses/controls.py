"""Export matched effect-off controls from the same saved aged geometry."""
import argparse
from pathlib import Path
import sys

import bpy

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE.parent/'her_jacket')]
from cloth_tools import export
from refine import disable_dust

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--no-fold-dust',action='store_true')
p.add_argument('--no-fibres',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
if not a.no_fold_dust and not a.no_fibres:p.error('Select an effect to disable')
bpy.ops.wm.open_mainfile(filepath=str(HERE/'her_dresses-aged.blend'))
if a.no_fold_dust:disable_dust()
if a.no_fibres:
    for obj in bpy.context.scene.objects:
        if 'FibreHeap' in obj.name or 'FrayedYarns' in obj.name:obj['aged_export']=False
export(a.output)
