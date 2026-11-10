"""Fit a saved cloth surface to the measured hang space, preserving the simulation."""
import argparse
import json
from pathlib import Path
import sys

import bpy

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE.parent/'her_jacket')]
from build import BAYS,RAIL_Y
import space
import silhouette
import brittle
from cloth_tools import fringe,save_state

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--state',choices=['remembered','aged'],required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
bpy.ops.wm.open_mainfile(filepath=str(HERE/f'her_dresses-{a.state}.blend'))
record=json.loads((HERE/f'{a.state}.json').read_text())
for i,config in enumerate(BAYS):
    obj=bpy.data.objects[config['name']]
    record['dresses'][config['name']]['silhouette_fit']=silhouette.fit(obj,RAIL_Y,aged=a.state=='aged')
    record['dresses'][config['name']]['collider_fit']=space.fit(obj,i==0)
    if a.state=='aged':
        brittle.surface(obj.data.materials[0],config['aged_color'])
        brittle.heap(config['name']+'_FibreHeap_Base',-.39 if i==0 else .39,RAIL_Y,bpy.data.materials['DryFadedDressFibres'])
        old=bpy.data.objects[config['name']+'_FrayedYarns']
        bpy.data.objects.remove(old,do_unlink=True)
        fringe(obj,bpy.data.materials['DryFadedDressFibres'],95280+i,
               minimum_z=config['hem']-.2,maximum_z=1.67,
               axis_limit=(-.473,-.23) if i==0 else (.23,.473),
               blockers=[o for o in bpy.context.scene.objects if o.type=='MESH' and (o.get('support') or o.get('placement_only') or o.name.endswith('_Hanger'))])
save_state(HERE,'her_dresses',a.state,record)
