"""Fit the generated two-drawer bedside unit and its separate reading lamp."""
import math
from pathlib import Path
import sys

import bpy
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'wardrobe'))
from batch_tools import build_main, cage, cylinder, empty, materials, panel, recess, rivets

SPEC={
    'bounds_gltf':[[-.25,0,-.225],[.25,.60,.225]],
    'required_nodes':['Bedside','Carcass','Drawers','Drawer_0','Drawer_1','Lamp','LampStem','LampHood'],
    'parents':{'Carcass':'Bedside','Drawers':'Bedside','Drawer_0':'Drawers','Drawer_1':'Drawers','Lamp':'Bedside','LampStem':'Lamp','LampHood':'Lamp'},
    'pivots_gltf':{'Bedside':[0,0,0]},
    'materials':['PaintedSteel','BareSteel','DarkSteel'],
    'visible_details':['DrawerPull_0','LampHood'],
    'hero_camera_native':[-1.0,-2.5,.85],'hero_camera_gltf':[-1.0,.85,2.5],
    'hero_target_native':[0,0,.30],'triangle_limit':6000,
    'fit_notes':'The generated cabinet-top patch sets carcass height while the total unit and lamp retain the .60 m layout envelope. The two drawer trays, recessed handles and fixed lamp assembly remain independent parts. This single asset is instanced on both sides of the bed.',
}


def assemble(guide):
    mats=materials(); paint=mats['PaintedSteel']; bare=mats['BareSteel']; dark=mats['DarkSteel']
    root=empty('Bedside'); body=empty('Carcass',parent=root); drawers=empty('Drawers',parent=root)
    cloud=np.array([list(v.co) for o in bpy.data.objects if o.name.startswith('Guide_') for v in o.data.vertices])
    top=cloud[(np.abs(cloud[:,0])<.19)&(np.abs(cloud[:,1])<.15)&(cloud[:,2]>.30)&(cloud[:,2]<.50)]
    measured=float(np.quantile(top[:,2],.80)); height=.45
    guide['carcass_top_fit']={'sample_count':len(top),'guide_height_m':measured,'fitted_height_m':height}
    for name,dims,centre in [
        ('Top',(.50,.45,.018),(0,0,height-.009)),
        ('Side_L',(.018,.45,height-.05),(-.241,0,(height+.05)/2)),
        ('Side_R',(.018,.45,height-.05),(.241,0,(height+.05)/2)),
        ('Back',(.464,.018,height-.05),(0,.216,(height+.05)/2)),
        ('Bottom',(.464,.432,.018),(0,-.009,.059)),
        ('KickPlate',(.46,.39,.05),(0,0,.025)),
    ]:panel(name,dims,centre,dark if name=='KickPlate' else paint,.002,parent=body)
    drawer_h=(height-.09)/2
    for i in range(2):
        z=.066+drawer_h*(i+.5)
        drawer=empty(f'Drawer_{i}',(0,-.213,z),parent=drawers)
        drawer['slide_axis']='glTF +Z'; drawer['slide_range_m']=.28
        SPEC['pivots_gltf'][f'Drawer_{i}']=[0,z,.213]
        for name,dims,pos in [
            (f'DrawerFront_{i}',(.458,.020,drawer_h-.006),(0,-.213,z)),
            (f'DrawerSideL_{i}',(.012,.355,drawer_h-.03),(-.22,-.025,z-.007)),
            (f'DrawerSideR_{i}',(.012,.355,drawer_h-.03),(.22,-.025,z-.007)),
            (f'DrawerBottom_{i}',(.428,.355,.012),(0,-.025,z-drawer_h/2+.012)),
            (f'DrawerBack_{i}',(.428,.012,drawer_h-.03),(0,.1465,z-.007)),
        ]:
            obj=panel(name,dims,pos,paint,.001,parent=drawer)
            if name==f'DrawerFront_{i}':recess(obj,(0,-.218,z+.018),(.10,.014,.035))
        panel(f'DrawerPocket_{i}',(.098,.001,.033),(0,-.2115,z+.018),dark,.0004,parent=drawer)
        panel(f'DrawerPull_{i}',(.07,.008,.009),(0,-.222,z+.018),bare,.001,parent=drawer)
        rivets(f'DrawerRivets_{i}',[(x,-.2233,z) for x in (-.20,.20)],bare,radius=.003,parent=drawer)
    lamp=empty('Lamp',(-.15,.13,height),parent=root)
    cylinder('LampFoot',.035,.012,(-.15,.13,height+.006),dark,sides=24,parent=lamp)
    cylinder('LampStem',.010,.58-height,(-.15,.13,(height+.58)/2),bare,sides=16,parent=lamp)
    arc=np.linspace(0,math.pi,13)
    profile=[(.085+.050*math.cos(a),.565+.035*math.sin(a)) for a in arc]
    count=len(profile)
    vertices=[(x,y,z) for x in (-.210,-.090) for y,z in profile]
    faces=[tuple(reversed(range(count))),tuple(range(count,2*count))]
    faces += [(i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count)]
    hood=cage('LampHood',vertices,faces,bare,.0005,parent=lamp)
    for face in hood.data.polygons:
        face.use_smooth=abs(face.normal.x)<.01
    panel('LampLens',(.100,.070,.003),(-.15,.085,.564),dark,.001,parent=lamp)
    rivets('TopRivets',[(x,-.2253,height-.009) for x in (-.21,.21)],bare,radius=.003,parent=body)
    guide['lamp_hood_fit']={'shape':'Closed elliptical steel canopy with a separate downward lens, not a painted rectangular block.',
        'width_m':.12,'depth_m':.10,'rise_m':.035}


if __name__=='__main__':
    build_main(__file__,'bedside',assemble,SPEC,(.5,.60,.45))
