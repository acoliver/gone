"""Read native bounds from saved sources for independent exported-axis checks."""
import argparse
import json
from pathlib import Path
import sys

import bpy

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from cloth_tools import native_bounds

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('prop',choices=['her_jacket','her_dresses'])
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
folder=HERE.parent/a.prop
for state in ('remembered','aged'):
    bpy.ops.wm.open_mainfile(filepath=str(folder/f'{a.prop}-{state}.blend'))
    path=folder/f'{state}.json'
    record=json.loads(path.read_text())
    record['bounds_blender_native_m']=native_bounds()
    path.write_text(json.dumps(record,indent=2)+'\n')
