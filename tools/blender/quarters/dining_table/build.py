"""Fair the generated round tabletop and pedestal to the layout diameter."""
import math
from pathlib import Path
import sys

import bpy
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'wardrobe'))
from batch_tools import build_main, cylinder, empty, materials, rivets

SPEC={
    'bounds_gltf':[[-.45,0,-.45],[.45,.75,.45]],
    'required_nodes':['DiningTable','Top','Base','Pedestal','DeckPlate'],
    'parents':{'Top':'DiningTable','Base':'DiningTable','Pedestal':'Base','DeckPlate':'Base'},
    'pivots_gltf':{'DiningTable':[0,0,0]},
    'materials':['PaintedSteel','BareSteel','DarkSteel'],
    'visible_details':['TopRivets','Pedestal'],
    'hero_camera_native':[-1.6,-2.3,1.6],'hero_camera_gltf':[-1.6,1.6,2.3],
    'hero_target_native':[0,0,.375],'triangle_limit':6000,
    'fit_notes':'The generated mid-height radial profile sets the pedestal radius. Its axis and the tabletop are faired to concentric manufactured surfaces; the top is constrained to the layout 0.90 m diameter. The rolled edge is real bevel geometry.',
}


def assemble(guide):
    mats=materials(paint_color=(.072,.095,.092,1)); paint=mats['PaintedSteel']; bare=mats['BareSteel']; dark=mats['DarkSteel']
    paint.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.46
    bare.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.20,.23,.22,1)
    root=empty('DiningTable'); base=empty('Base',parent=root)
    points=np.array([list(v.co) for o in bpy.data.objects if o.name.startswith('Guide_') for v in o.data.vertices])
    mid=points[(points[:,2]>.22)&(points[:,2]<.57)]
    measured=float(np.quantile(np.linalg.norm(mid[:,:2],axis=1),.70))
    radius=float(np.clip(measured,.045,.09))
    guide['pedestal_fit']={'sample_count':len(mid),'guide_radius_m':measured,'fitted_radius_m':radius}
    cylinder('Top',.45,.045,(0,0,.7275),paint,sides=96,edge=.007,parent=root)
    cylinder('Pedestal',radius,.68,(0,0,.375),paint,sides=32,edge=.003,parent=base)
    cylinder('DeckPlate',.27,.035,(0,0,.0175),paint,sides=64,edge=.004,parent=base)
    cylinder('StemCollar',radius+.010,.012,(0,0,.041),bare,sides=32,edge=.001,parent=base)
    heads=[]
    for i in range(16):
        point=(.405*math.cos(i*math.tau/16),.405*math.sin(i*math.tau/16),.7493)
        heads.append(cylinder(f'TopRivet_{i}',.005,.002,point,dark,sides=12,edge=0,parent=root))
    bpy.ops.object.select_all(action='DESELECT')
    for head in heads:head.select_set(True)
    bpy.context.view_layer.objects.active=heads[0]
    bpy.ops.object.join();heads[0].name='TopRivets'
    rivets('BaseBolts',[(.22*math.cos(i*math.tau/8),.22*math.sin(i*math.tau/8),.0353) for i in range(8)],bare,axis=(0,0,1),radius=.007,parent=base)


if __name__=='__main__':
    build_main(__file__,'dining_table',assemble,SPEC,(.9,.75,.9))
