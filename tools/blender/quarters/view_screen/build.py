"""Fit the generated wall display with an actual opening, glass and display slab."""
from pathlib import Path
import sys

import bpy
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'wardrobe'))
from batch_tools import build_main, empty, material, materials, panel, rivets

SPEC={
    'bounds_gltf':[[-.90,0,-.04],[.90,1.05,.04]],
    'required_nodes':['ViewScreen','Housing','Bezel','Glass','Display','HousingBack'],
    'parents':{'Housing':'ViewScreen','Bezel':'ViewScreen','Glass':'ViewScreen','Display':'ViewScreen','HousingBack':'Housing'},
    'pivots_gltf':{'ViewScreen':[0,0,0]},
    'materials':['PaintedSteel','BareSteel','DarkSteel','Display','Glass'],
    'visible_details':['Glass','HousingRivets','BezelBottom'],
    'hero_camera_native':[-1.4,-4.0,1.5],'hero_camera_gltf':[-1.4,1.5,4.0],
    'hero_target_native':[0,0,.525],'triangle_limit':15000,
    'room_mount_height_m':1.0,
    'fit_notes':'The earlier capture was front-facing but its missing dark bezel and bright cover made it read as a back panel. A separate inset dark bezel now surrounds the glass and display. Its lower rail is broader than its upper rail, following seed 283. Four faired housing rails leave a real aperture; glass and emissive screen are separate closed parts. Local origin becomes room y=1.0 when wall mounted.',
}


def assemble(guide):
    mats=materials(); paint=mats['PaintedSteel']; bare=mats['BareSteel']; dark=mats['DarkSteel']
    display=material('Display',(.001,.002,.003,1),0,.40)
    display.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value=.08
    glass=material('Glass',(.10,.12,.13,.18),0,.08)
    shader=glass.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Transmission Weight'].default_value=.95
    shader.inputs['IOR'].default_value=1.45
    root=empty('ViewScreen'); housing=empty('Housing',parent=root)
    cloud=np.array([list(v.co) for o in bpy.data.objects if o.name.startswith('Guide_') for v in o.data.vertices])
    mid=cloud[(cloud[:,2]>.3)&(cloud[:,2]<.75)&(cloud[:,1]<0)]
    measured=.90-float(np.quantile(np.abs(mid[:,0]),.95)); rim=.070
    guide['frame_fit']={'sample_count':len(mid),'guide_outer_edge_offset_m':measured,
        'fitted_painted_frame_width_m':rim,'dark_bezel_sides_top_bottom_m':[.055,.060,.100],
        'method':'Outer-edge quantiles locate the silhouette, not the display inset. The approved image supplies the separate dark inner bezel.'}
    for name,dims,centre in [
        ('HousingLeft',(rim,.08,1.05),(-.9+rim/2,0,.525)),
        ('HousingRight',(rim,.08,1.05),(.9-rim/2,0,.525)),
        ('HousingTop',(1.8-2*rim,.08,rim),(0,0,1.05-rim/2)),
        ('HousingBottom',(1.8-2*rim,.08,rim),(0,0,rim/2)),
        ('HousingBack',(1.8-2*rim,.012,1.05-2*rim),(0,.034,.525)),
    ]:panel(name,dims,centre,paint,.003,parent=housing)
    bezel=empty('Bezel',parent=root)
    for name,dims,centre in [
        ('BezelLeft',(.055,.020,.91),(-.8025,-.026,.525)),
        ('BezelRight',(.055,.020,.91),(.8025,-.026,.525)),
        ('BezelTop',(1.55,.020,.060),(0,-.026,.950)),
        ('BezelBottom',(1.55,.020,.100),(0,-.026,.120)),
    ]:panel(name,dims,centre,dark,.002,parent=bezel)
    panel('ScreenBacking',(1.548,.008,.748),(0,-.018,.545),dark,.001,parent=housing)
    panel('Display',(1.546,.004,.746),(0,-.025,.545),display,.0005,parent=root)
    panel('Glass',(1.548,.004,.748),(0,-.034,.545),glass,.0005,parent=root)
    rivets('HousingRivets',[(x,-.0403,z) for x in (-.865,.865) for z in (.10,.30,.525,.75,.95)],bare,radius=.004,parent=housing)


if __name__=='__main__':
    build_main(__file__,'view_screen',assemble,SPEC,(1.8,1.05,.08))
