"""Refresh sewn facings and collider-fitted fraying on a saved drape, without cloth resimulation."""
import argparse
import json
from pathlib import Path
import sys

import bpy

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from cloth_tools import fringe,save_state
from tailoring import add_tailoring

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--state',choices=['remembered','aged'],default='remembered')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
bpy.ops.wm.open_mainfile(filepath=str(HERE/f'her_jacket-{a.state}.blend'))
for obj in list(bpy.context.scene.objects):
    if obj.name.startswith(('Lapel_','JacketButton_')) or (a.state=='aged' and obj.name=='Jacket_FrayedYarns'):
        bpy.data.objects.remove(obj,do_unlink=True)
obj=bpy.data.objects['Jacket']
add_tailoring(obj,aged=a.state=='aged')
if a.state=='aged':
    yarn=bpy.data.materials['PaleDryFibres']
    fringe(obj,yarn,95273,minimum_z=.27,maximum_z=.83,
           blockers=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.get('support')])
record=json.loads((HERE/f'{a.state}.json').read_text())
record['tailoring']='Surface-fitted lapel facings and three retained 8 mm buttons'
save_state(HERE,'her_jacket',a.state,record)
