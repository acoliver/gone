"""Fit an armoured display, key deck and tapered support over the generated console."""
import json
import math
from pathlib import Path
import sys

import bpy
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(HERE.parent/'wardrobe'))
from batch_tools import attach, build_main, cage, cylinder, empty, material, materials, panel, rivets

from refit import apply_refit, RISE

SPEC={
    'bounds_gltf':[[-.55,0,-.275],[.55,.69+RISE,.275]],
    'required_nodes':['Console','ArmouredHousing','LowerDeckHousing','DesktopSupport','Bezel','Display','ControlPanel','Keys','Toggles'],
    'parents':{'ArmouredHousing':'Console','LowerDeckHousing':'Console','DesktopSupport':'Console','Bezel':'ScreenPlane','Display':'ScreenPlane',
               'ScreenPlane':'Console','ControlPanel':'Console','Keys':'ControlPanel','Toggles':'ControlPanel'},
    'pivots_gltf':{'Console':[0,0,0]},
    'materials':['PaintedSteel','BareSteel','DarkSteel','Display'],
    'visible_details':['Display','Key_1_4','Toggle_1','DesktopSupport'],
    'hero_camera_native':[-1.4,-4,1.8],'hero_camera_gltf':[-1.4,1.8,4],
    'hero_target_native':[0,0,.34],'triangle_limit':15000,
    'display_states':['remembered','present'],
    'fit_notes':'Seed 351 has a broad head carried on a narrower tapered support, not the full-width solid wedge described by the prompt. Guide sections below .32 m determine the support widths. The selected image supports a 4-by-6 key grid instead of the prompted 3-by-8 grid; the verified total remains 24 keys and three separate toggles. The original .69 m head is extended to 16:10 by refit.py for issue #129, retaining the support and deck pose. The display is an independent emissive part in both states.',
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
    bottom=cloud[(cloud[:,2]>.02)&(cloud[:,2]<.08)]
    neck=cloud[(cloud[:,2]>.27)&(cloud[:,2]<.31)]
    bottom_width=float(np.clip(np.ptp(np.quantile(bottom[:,0],[.02,.98])),.66,.78))
    neck_width=float(np.clip(np.ptp(np.quantile(neck[:,0],[.02,.98])),.50,.64))
    guide['support_fit']={'bottom_samples':len(bottom),'neck_samples':len(neck),
        'bottom_width_m':bottom_width,'neck_width_m':neck_width,'top_height_m':.32,
        'fitting_choice':'The generated pedestal is faired to a symmetric closed manufactured support. The selected head/support junction is near image y=555 of its y=160..910 envelope.'}
    vertices=[(x,.025+y,z) for width,depth,z in ((bottom_width,.36,.018),(neck_width,.28,.32))
              for y in (-depth/2,depth/2) for x in (-width/2,width/2)]
    faces=[(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)]
    cage('DesktopSupport',vertices,faces,paint,.004,parent=root)
    panel('BaseShoe',(bottom_width-.015,.35,.018),(0,.025,.009),dark,.002,parent=root)
    lower=cloud[(cloud[:,2]>.36)&(cloud[:,2]<.42)]
    upper=cloud[(cloud[:,2]>.59)&(cloud[:,2]<.65)]
    measured=float((np.quantile(upper[:,1],.10)-np.quantile(lower[:,1],.10))/.23)
    slope=float(np.clip(measured,.35,.60))
    low=-.045; high=low+slope*.27
    guide['display_face_fit']={'lower_samples':len(lower),'upper_samples':len(upper),
        'guide_dy_dz':measured,'fitted_dy_dz':slope,'lower_deck_height_m':.36,
        'screen_lower_height_m':.42,'screen_upper_height_m':.69}
    for name,profile in [
        ('ArmouredHousing',[(low,.42),(.275,.42),(.275,.69),(high,.69)]),
        ('LowerDeckHousing',[(-.275,.31),(.275,.31),(.275,.42),(low,.42),(-.275,.36)]),
    ]:
        vertices=[(x,y,z) for x in (-.55,.55) for y,z in profile]; n=len(profile)
        faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]
        faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        cage(name,vertices,faces,paint,.006,parent=root)
    screen=empty('ScreenPlane',(0,(low+high)/2-.012,.542),parent=root)
    screen.rotation_euler.x=-math.atan(slope)
    bezel=local(empty('Bezel'),screen,(0,0,0))
    for name,dims,pos in [
        ('BezelLeft',(.075,.030,.300),(-.4825,-.020,0)),
        ('BezelRight',(.075,.030,.300),(.4825,-.020,0)),
        ('BezelTop',(.89,.030,.030),(0,-.020,.135)),
        ('BezelBottom',(.89,.030,.030),(0,-.020,-.135)),
    ]:local(panel(name,dims,(0,0,0),paint,.003),bezel,pos)
    local(panel('ScreenGasket',(.894,.008,.244),(0,0,0),dark,.001),screen,(0,-.023,0))
    local(panel('Display',(.874,.004,.238),(0,0,0),display,.001),screen,(0,-.029,0))
    bpy.context.view_layer.update()
    from mathutils import Vector
    points=[screen.matrix_world@Vector((x,-.036,z)) for x in (-.4825,.4825) for z in (-.105,.105)]
    axis=screen.matrix_world.to_3x3()@Vector((0,-1,0))
    rivets('BezelRivets',points,bare,axis=axis,radius=.004,parent=bezel)
    deck_length=math.hypot(low+.275,.06)-.014
    control=panel('ControlPanel',(1.02,deck_length,.018),(0,(-.275+low)/2,.39),paint,.003,parent=root)
    control.rotation_euler.x=math.atan(.06/(low+.275))
    keys=local(empty('Keys'),control,(0,0,0)); toggles=local(empty('Toggles'),control,(0,0,0))
    for row,y in enumerate((-.0675,-.0225,.0225,.0675)):
        for col in range(6):
            local(panel(f'Key_{row}_{col}',(.073,.034,.014),(0,0,0),dark,.002),keys,(-.425+col*.105,y,.016))
    for i,y in enumerate((-.060,0,.060)):
        local(cylinder(f'ToggleSocket_{i}',.012,.008,(0,0,0),dark,sides=12),toggles,(.34,y,.014))
        local(cylinder(f'Toggle_{i}',.004,.052,(0,0,0),bare,sides=12),toggles,(.34,y,.041),(math.radians(-18),0,0))
    rivets('HousingRivets',[(x,-.2753,.335) for x in (-.48,.48)],bare,radius=.004,parent=root)
    apply_refit()


if __name__=='__main__':
    # Keep provenance and constraints with the saved-source construction record.
    SPEC.update(json.loads((HERE/'construction.json').read_text()))
    build_main(__file__,'console',assemble,SPEC,(1.1,.69,.55))
