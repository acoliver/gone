"""Fit an armoured display and sloping key deck over the generated console."""
import math
from pathlib import Path
import sys

import bpy
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'wardrobe'))
from batch_tools import attach, build_main, cage, cylinder, empty, material, materials, panel, rivets

SPEC={
    'bounds_gltf':[[-.55,0,-.275],[.55,.69,.275]],
    'required_nodes':['Console','ArmouredHousing','Bezel','Display','ControlPanel','Keys','Toggles'],
    'parents':{'ArmouredHousing':'Console','Bezel':'ScreenPlane','Display':'ScreenPlane',
               'ScreenPlane':'Console','ControlPanel':'Console','Keys':'ControlPanel','Toggles':'ControlPanel'},
    'pivots_gltf':{'Console':[0,0,0]},
    'materials':['PaintedSteel','BareSteel','DarkSteel','Display'],
    'visible_details':['Display','Key_1_4','Toggle_1'],
    'hero_camera_native':[-1.4,-4,2.6],'hero_camera_gltf':[-1.4,2.6,4],
    'hero_target_native':[0,0,.34],'triangle_limit':15000,
    'display_states':['remembered','present'],
    'fit_notes':'The approved seed 332 has a tall solid lower wedge, a painted armoured bezel and long-stem toggles. Front-section guide percentiles set the upper slope. The lower deck is raised to .30-.36 m rather than the earlier .14-.22 m slab. The fixed layout envelope is retained. Twenty-four separate keys and three separate toggles follow the written control count; the hero has additional keys. The display remains an independent emissive part in both states.',
}


def local(obj,parent,position,rotation=(0,0,0)):
    attach(obj,parent)
    obj.matrix_parent_inverse.identity()
    obj.location=position
    obj.rotation_euler=rotation
    return obj


def assemble(guide):
    mats=materials(); paint=mats['PaintedSteel']; bare=mats['BareSteel']; dark=mats['DarkSteel']
    display=material('Display',(.002,.018,.019,1),0,.65)
    display.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value=.15
    display.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value=0
    root=empty('Console')
    cloud=np.array([list(v.co) for o in bpy.data.objects if o.name.startswith('Guide_') for v in o.data.vertices])
    lower=cloud[(cloud[:,2]>.36)&(cloud[:,2]<.42)]
    upper=cloud[(cloud[:,2]>.59)&(cloud[:,2]<.65)]
    measured=float((np.quantile(upper[:,1],.10)-np.quantile(lower[:,1],.10))/.23)
    slope=float(np.clip(measured,.35,.60))
    low=-.045; high=low+slope*.33
    guide['display_face_fit']={'lower_samples':len(lower),'upper_samples':len(upper),
        'guide_dy_dz':measured,'fitted_dy_dz':slope,'lower_deck_height_m':.30,
        'screen_lower_height_m':.36,'screen_upper_height_m':.69}
    profile=[(-.275,0),(.275,0),(.275,.69),(high,.69),(low,.36),(-.275,.30)]
    vertices=[(x,y,z) for x in (-.55,.55) for y,z in profile]; n=len(profile)
    faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    cage('ArmouredHousing',vertices,faces,paint,.006,parent=root)
    screen=empty('ScreenPlane',(0,(low+high)/2-.012,.525),parent=root)
    screen.rotation_euler.x=-math.atan(slope)
    bezel=local(empty('Bezel'),screen,(0,0,0))
    for name,dims,pos in [
        ('BezelLeft',(.075,.030,.344),(-.4825,-.020,0)),
        ('BezelRight',(.075,.030,.344),(.4825,-.020,0)),
        ('BezelTop',(.89,.030,.045),(0,-.020,.1495)),
        ('BezelBottom',(.89,.030,.045),(0,-.020,-.1495)),
    ]:local(panel(name,dims,(0,0,0),paint,.003),bezel,pos)
    local(panel('ScreenGasket',(.894,.008,.258),(0,0,0),dark,.001),screen,(0,-.023,0))
    local(panel('Display',(.874,.004,.238),(0,0,0),display,.001),screen,(0,-.029,0))
    bpy.context.view_layer.update()
    from mathutils import Vector
    points=[screen.matrix_world@Vector((x,-.036,z)) for x in (-.4825,.4825) for z in (-.12,.12)]
    axis=screen.matrix_world.to_3x3()@Vector((0,-1,0))
    rivets('BezelRivets',points,bare,axis=axis,radius=.004,parent=bezel)
    deck_length=math.hypot(low+.275,.06)-.014
    control=panel('ControlPanel',(1.02,deck_length,.018),(0,(-.275+low)/2,.33),paint,.003,parent=root)
    control.rotation_euler.x=math.atan(.06/(low+.275))
    keys=local(empty('Keys'),control,(0,0,0)); toggles=local(empty('Toggles'),control,(0,0,0))
    for row,y in enumerate((-.065,-.010,.045)):
        for col in range(8):
            local(panel(f'Key_{row}_{col}',(.073,.042,.014),(0,0,0),dark,.002),keys,(-.425+col*.12,y,.016))
    for i,x in enumerate((-.28,0,.28)):
        local(cylinder(f'ToggleSocket_{i}',.012,.008,(0,0,0),dark,sides=12),toggles,(x,.088,.014))
        local(cylinder(f'Toggle_{i}',.004,.052,(0,0,0),bare,sides=12),toggles,(x,.088,.041),(math.radians(-18),0,0))
    rivets('HousingRivets',[(x,-.2753,z) for x in (-.48,.48) for z in (.055,.24)],bare,radius=.004,parent=root)
    panel('BaseShoe',(1.05,.50,.018),(0,0,.009),dark,.002,parent=root)


if __name__=='__main__':
    build_main(__file__,'console',assemble,SPEC,(1.1,.69,.55))
