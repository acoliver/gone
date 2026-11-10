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
    'visible_details':['DrawerPull_0','LampHood','KickPlate'],
    'hero_camera_native':[-1.0,-2.5,1.10],'hero_camera_gltf':[-1.0,1.10,2.5],
    'hero_target_native':[0,0,.30],'triangle_limit':6000,
    'fit_notes':'The generated cabinet-top patch measures .441 m and is faired to the requested .45 m top while the total lamp height retains the .60 m layout envelope. Separate drawer trays and handles remain independent parts. The curved lamp canopy has rounded ends and a satin bare-steel finish so its silhouette remains visible rather than clipping to a white block. This single asset is used on both sides of the bed.',
}


def assemble(guide):
    mats=materials(); paint=mats['PaintedSteel']; bare=mats['BareSteel']; dark=mats['DarkSteel']
    steel=bare.node_tree.nodes['Principled BSDF']
    steel.inputs['Base Color'].default_value=(.32,.35,.36,1)
    steel.inputs['Roughness'].default_value=.40
    dark.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.010,.014,.014,1)
    dark.node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value=.05
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
        ('Plinth',(.44,.36,.05),(0,0,.025)),
        ('KickPlate',(.46,.012,.05),(0,-.179,.025)),
    ]:panel(name,dims,centre,dark if name in {'KickPlate','Plinth'} else paint,.001,parent=body)
    drawer_h=(height-.09)/2
    for i in range(2):
        z=.069+drawer_h*(i+.5)
        drawer=empty(f'Drawer_{i}',(0,-.213,z),parent=drawers)
        drawer['slide_axis']='glTF +Z'; drawer['slide_range_m']=.28
        SPEC['pivots_gltf'][f'Drawer_{i}']=[0,z,.213]
        for name,dims,pos in [
            (f'DrawerFront_{i}',(.458,.020,drawer_h-.002),(0,-.213,z)),
            (f'DrawerSideL_{i}',(.012,.355,drawer_h-.03),(-.22,-.025,z-.007)),
            (f'DrawerSideR_{i}',(.012,.355,drawer_h-.03),(.22,-.025,z-.007)),
            (f'DrawerBottom_{i}',(.428,.355,.012),(0,-.025,z-drawer_h/2+.012)),
            (f'DrawerBack_{i}',(.428,.012,drawer_h-.03),(0,.1465,z-.007)),
        ]:
            obj=panel(name,dims,pos,paint,.001,parent=drawer)
            if name==f'DrawerFront_{i}':recess(obj,(0,-.218,z+.018),(.09,.014,.025))
        panel(f'DrawerPocket_{i}',(.088,.001,.023),(0,-.2115,z+.018),dark,.0004,parent=drawer)
        panel(f'DrawerPull_{i}',(.065,.008,.003),(0,-.215,z+.024),bare,.0006,parent=drawer)
        rivets(f'DrawerRivets_{i}',[(x,-.2233,z) for x in (-.20,.20)],bare,radius=.003,parent=drawer)
    lamp=empty('Lamp',(-.15,.13,height),parent=root)
    cylinder('LampFoot',.022,.010,(-.15,.13,height+.005),dark,sides=24,parent=lamp)
    cylinder('LampStem',.005,.59-height,(-.15,.13,(height+.59)/2),bare,sides=16,parent=lamp)
    sides=24; rings=6
    vertices=[]
    for ring in range(rings):
        elevation=ring*math.pi/(2*rings)
        for i in range(sides):
            angle=i*math.tau/sides
            vertices.append((-.15+.040*math.cos(elevation)*math.cos(angle),
                             .115+.030*math.cos(elevation)*math.sin(angle),
                             .585+.015*math.sin(elevation)))
    apex=len(vertices); vertices.append((-.15,.115,.60))
    faces=[tuple(reversed(range(sides)))]
    faces += [(r*sides+i,r*sides+(i+1)%sides,(r+1)*sides+(i+1)%sides,(r+1)*sides+i)
              for r in range(rings-1) for i in range(sides)]
    faces += [((rings-1)*sides+i,(rings-1)*sides+(i+1)%sides,apex) for i in range(sides)]
    hood=cage('LampHood',vertices,faces,bare,0,parent=lamp)
    for face in hood.data.polygons:
        face.use_smooth=face.normal.z>0
    panel('LampLens',(.056,.040,.003),(-.15,.115,.584),dark,.001,parent=lamp)
    rivets('TopRivets',[(x,-.2253,height-.009) for x in (-.21,.21)],bare,radius=.003,parent=body)
    guide['lamp_hood_fit']={'shape':'Closed ellipsoidal steel canopy with a separate downward lens.',
        'width_m':.08,'depth_m':.06,'rise_m':.015}


if __name__=='__main__':
    build_main(__file__,'bedside',assemble,SPEC,(.5,.60,.45))
