"""Fit the generated bed frame and rounded headboard, leaving the platform exposed."""
import math
from pathlib import Path
import sys

import bpy
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'wardrobe'))
from batch_tools import build_main, cage, empty, materials, panel, rivets

SPEC={
    'bounds_gltf':[[-.8,0,-1.1],[.8,1.1,1.1]],
    'required_nodes':['Bed','Frame','Headboard','MattressPlatform','FrameSide_L','FrameSide_R'],
    'parents':{'Frame':'Bed','Headboard':'Bed','MattressPlatform':'Frame',
               'FrameSide_L':'Frame','FrameSide_R':'Frame'},
    'pivots_gltf':{'Bed':[0,0,0]},
    'materials':['PaintedSteel','BareSteel','DarkSteel'],
    'visible_details':['MattressPlatform','HeadboardRivets','FootRivets'],
    'hero_camera_native':[-4,-4.6,2.4],'hero_camera_gltf':[-4,2.4,4.6],
    'hero_target_native':[0,0,.5], 'triangle_limit':15000,
    'layout_frame_height_m':.55,'layout_headboard_height_m':1.1,
    'platform_range_m':[.50,.52],
    'fit_notes':'The generated continuous platform, thin side rails and open legs are faired into folded steel parts. The platform and rail upper edge share the layout .55 m frame height; the separate rounded headboard remains 1.10 m tall. The thin faired rail replaces the scan lower skirt, preserving the approved open silhouette. No soft parts or textures are included.',
}


def headboard(mat,parent):
    radius=.10; outline=[(-.8,.15),(.8,.15),(.8,1.0)]
    outline.extend((.7+radius*math.cos(i*math.pi/16),1+radius*math.sin(i*math.pi/16)) for i in range(1,9))
    outline.append((-.7,1.1))
    outline.extend((-.7+radius*math.cos(math.pi/2+i*math.pi/16),1+radius*math.sin(math.pi/2+i*math.pi/16)) for i in range(1,9))
    n=len(outline); vertices=[(x,y,z) for y in (1.0,1.1) for x,z in outline]
    faces=[tuple(range(n)),tuple(reversed(range(n,2*n)))]
    faces.extend((i,i+n,(i+1)%n+n,(i+1)%n) for i in range(n))
    return cage('Headboard',vertices,faces,mat,.003,parent=parent)


def assemble(guide):
    mats=materials(); paint=mats['PaintedSteel']; bare=mats['BareSteel']; dark=mats['DarkSteel']
    root=empty('Bed'); frame=empty('Frame',parent=root)
    samples=np.array([list(v.co) for o in bpy.data.objects if o.name.startswith('Guide_')
                      for v in o.data.vertices if abs(v.co.x)<.65 and abs(v.co.y)<.9 and 0<v.co.z<.6])
    measured=float(np.median(samples[:,2])); platform_z=float(np.clip(measured,*SPEC['platform_range_m']))
    guide['platform_fit']={'sample_count':len(samples),'guide_median_height_m':measured,
        'fitted_height_m':platform_z,'allowed_support_height_m':SPEC['platform_range_m']}
    sides=np.array([list(v.co) for o in bpy.data.objects if o.name.startswith('Guide_')
                    for v in o.data.vertices if .68<abs(v.co.x)<.80 and abs(v.co.y)<.8 and .04<v.co.z<.56])
    measured_low=float(np.quantile(sides[:,2],.03)); rail_low=float(np.clip(measured_low,.485,.495))
    guide['side_rail_fit']={'sample_count':len(sides),'guide_lower_edge_m':measured_low,'fitted_lower_edge_m':rail_low}
    rail_height=.55-rail_low; rail_centre=(.55+rail_low)/2
    for name,dims,centre in [
        ('FrameSide_L',(.07,2.10,rail_height),(-.765,-.05,rail_centre)),
        ('FrameSide_R',(.07,2.10,rail_height),(.765,-.05,rail_centre)),
        ('FrameFootRail',(1.46,.07,rail_height),(0,-1.065,rail_centre)),
        ('FrameHeadRail',(1.46,.07,rail_height),(0,1.015,rail_centre)),
    ]:panel(name,dims,centre,paint,.005,parent=frame)
    panel('MattressPlatform',(1.46,2.03,.028),(0,-.025,platform_z-.014),paint,.002,parent=frame)
    for i,y in enumerate((-.78,-.28,.22,.72)):
        panel(f'CrossMember_{i}',(1.46,.055,.055),(0,y,platform_z-.055),paint,.003,parent=frame)
    for i,(x,y) in enumerate(((-.73,-1.03),(.73,-1.03),(-.73,1.00),(.73,1.00))):
        panel(f'Leg_{i}',(.06,.06,platform_z),(x,y,platform_z/2),paint,.003,parent=frame)
        panel(f'DeckShoe_{i}',(.10,.10,.024),(x,y,.012),dark,.002,parent=frame)
    headboard(paint,root)
    points=[]
    for x in (-.72,.72):points.extend((x,.9997,z) for z in (.25,.45,.65,.85,1.02))
    points.extend((x,.9997,1.02) for x in (-.48,-.24,0,.24,.48))
    rivets('HeadboardRivets',points,bare,radius=.006,parent=root)
    rivets('FootRivets',[(x,-1.1003,.52) for x in (-.64,-.32,0,.32,.64)],bare,radius=.006,parent=frame)
    for side,x in (('L',-.8003),('R',.8003)):
        rivets(f'SideRivets_{side}',[(x,y,.52) for y in (-.85,-.5,-.15,.2,.55,.9)],bare,
               axis=(-1,0,0) if side=='L' else (1,0,0),radius=.006,parent=frame)


if __name__=='__main__':
    build_main(__file__,'bed',assemble,SPEC,(1.6,1.1,2.2))
