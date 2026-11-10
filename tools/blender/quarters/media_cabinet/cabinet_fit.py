"""Fair three approved cabinet bays into folded shells with separate door leaves."""
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'wardrobe'))
from batch_tools import attach, cylinder, empty, hinge_origin, materials, panel, recess, rivets


def assemble_bank(guide,spec,width,height,depth,modular):
    mats=materials(); paint=mats['PaintedSteel']; bare=mats['BareSteel']; dark=mats['DarkSteel']
    name='OverBedLockers' if modular else 'MediaCabinet'
    root=empty(name); body=empty('Carcass',parent=root)
    cloud=np.array([list(v.co) for obj in bpy.data.objects if obj.name.startswith('Guide_') for v in obj.data.vertices])
    front=cloud[(cloud[:,1]<-depth*.30)&(cloud[:,2]>height*.20)&(cloud[:,2]<height*.85)]
    guide['bay_fitting']={'front_samples':len(front),'front_x_quantiles_m':np.quantile(front[:,0],[0,1/3,2/3,1]).tolist(),
        'fitted_equal_bays_m':width/3,'constraint':'Three equal manufactured bays follow the approved image; raw scan seam noise is faired.'}
    plinth=0 if modular else .06
    bay=width/3; t=.018
    for i in range(3):
        left=-width/2+i*bay; cx=left+bay/2
        part=empty(f'Module_{i}',(cx,0,0),parent=body) if modular else body
        for suffix,dims,pos in [
            ('SideL',(t,depth,height-plinth),(left+t/2,0,(height+plinth)/2)),
            ('SideR',(t,depth,height-plinth),(left+bay-t/2,0,(height+plinth)/2)),
            ('Back',(bay-2*t,t,height-plinth),(cx,depth/2-t/2,(height+plinth)/2)),
            ('Top',(bay-2*t,depth-t,t),(cx,-t/2,height-t/2)),
            ('Bottom',(bay-2*t,depth-t,t),(cx,-t/2,plinth+t/2)),
        ]:panel(f'Bay_{i}_{suffix}',dims,pos,paint,.002,parent=part)
        if not modular:
            panel(f'KickPlate_{i}',(bay-.04,depth-.06,plinth),(cx,0,plinth/2),dark,.002,parent=part)
        leaf_h=height-plinth-2*t-.006
        door=panel(f'Door_{i}',(bay-2*t-.006,.018,leaf_h),(cx,-depth/2+.012,(height+plinth)/2),paint,.002)
        pivot=(left+.018,-depth/2-.003,plinth+t+.003)
        hinge_origin(door,pivot); attach(door,part if modular else root)
        spec['pivots_gltf'][f'Door_{i}']=[pivot[0],pivot[2],-pivot[1]]
        door['opening_axis']='glTF +Y'; door['opening_range_degrees']=[0,100]
        latch_x=left+bay-.085; latch_z=(height+plinth)/2
        recess(door,(latch_x,-depth/2+.006,latch_z),(.045,.012,.10))
        panel(f'LatchPocket_{i}',(.043,.001,.098),(latch_x,-depth/2+.0125,latch_z),dark,.0004,parent=door)
        panel(f'Latch_{i}',(.065,.007,.014),(latch_x,-depth/2+.001,latch_z),bare,.001,parent=door)
        for j,z in enumerate((plinth+.10,height-.10)):
            cylinder(f'Hinge_{i}_{j}',.006,.052,(pivot[0],pivot[1],z),bare,sides=16,parent=part)
        points=[(left+.045,-depth/2+.0025,z) for z in (plinth+.06,(height+plinth)/2,height-.06)]
        points.extend((left+bay-.045,-depth/2+.0025,z) for z in (plinth+.06,height-.06))
        rivets(f'DoorRivets_{i}',points,bare,parent=door)
    if modular:
        panel('MountingRail',(width-.08,.018,.045),(0,depth/2-.014,height/2),dark,.002,parent=body)
