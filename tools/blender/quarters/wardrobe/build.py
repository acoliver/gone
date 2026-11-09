"""Fit the approved open wardrobe with clean manufactured panels and hardware."""
import math
from pathlib import Path
import sys

import bpy

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from batch_tools import (attach, build_main, cylinder, empty, hinge_origin,
                         materials, panel, recess, reflect_x, rivets)

SPEC={
    'bounds_gltf':[[-.5,0,-.325],[.5,2.2,.325]],
    'bounds_exclude':['Hinges','HingeMount_0','HingeMount_1','HingeMount_2','Door','DoorLatchPocket','DoorLatch','DoorVent_0','DoorVent_1',
                      'DoorVent_2','DoorRivets','DoorReturn_L','DoorReturn_R',
                      'DoorReturn_T','DoorReturn_B'],
    'required_nodes':['Carcass','Door','Rail','SidePanel_L','SidePanel_R','BackPanel',
                      'TopPanel','BottomPanel','KickPlate','DoorLatch','Hinges'],
    'parents':{'Door':'Wardrobe','Rail':'Carcass','SidePanel_L':'Carcass',
               'SidePanel_R':'Carcass','BackPanel':'Carcass','TopPanel':'Carcass',
               'BottomPanel':'Carcass','KickPlate':'Carcass','Hinges':'Carcass',
               'DoorLatchPocket':'Door','DoorLatch':'Door','DoorRivets':'Door'},
    'pivots_gltf':{'Wardrobe':[0,0,0],'Door':[.500,.12,.340]},
    'materials':['PaintedSteel','BareSteel','DarkSteel'],
    'visible_details':['Rail','DoorLatch','Hinges'],
    'hero_camera_native':[-1.4,-5.0,2.8],
    'hero_camera_gltf':[-1.4,2.8,5.0],
    'capture_scale':1.25,
    'hero_target_native':[.1,-.25,1.1],
    'triangle_limit':15000,
    'parked_open_degrees':100,
    'guide_body_bounds_native':[[-.340,-.1717951745,-.9990821481],[.5261281133,.5815733075,.9930578470]],
    'room_facing':'-x',
    'room_origin':[7.675,0,3.6],
    'room_rotation_y_degrees':-90,
    'room_hinge_xz':[7.335,4.1],
    'layout_hinge_xz':[7.35,4.1],
    'hinge_handedness':'Right-hand in asset front view. Asset +X maps to room +Z, matching the layout hinge at z=4.1. Barrel axis is 15 mm forward of the closed carcass footprint.',
    'fit_notes':'The generated carcass and door planes are faired to the selected hero silhouette, with their exterior constrained to the 1.00 x .65 x 2.20 m layout envelope. The image rail and panel boundaries set the internal split; scan lumps are discarded. Door and hardware are separate closed cages. Interior stays clear for the pilot tunic.',
}


def assemble(guide):
    mats=materials(paint_color=(.075,.090,.085,1)); paint=mats['PaintedSteel']; bare=mats['BareSteel']; dark=mats['DarkSteel']
    paint.node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value=.05
    paint.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.75
    root=empty('Wardrobe'); body=empty('Carcass',parent=root)
    for name,dims,centre in [
        ('SidePanel_L',(.024,.65,2.2),(-.488,0,1.1)),
        ('SidePanel_R',(.024,.65,2.2),(.488,0,1.1)),
        ('BackPanel',(.952,.024,2.2),(0,.313,1.1)),
        ('FrontFoot_L',(.046,.036,.12),(-.477,-.307,.06)),
        ('FrontFoot_R',(.046,.036,.12),(.477,-.307,.06)),
        ('TopPanel',(.952,.626,.024),(0,-.012,2.188)),
        ('BottomPanel',(.952,.626,.024),(0,-.012,.132)),
        ('SurroundHead',(.952,.026,.060),(0,-.312,2.146)),
        ('SurroundStile_L',(.022,.026,1.96),(-.465,-.312,1.124)),
        ('SurroundStile_R',(.022,.026,1.96),(.465,-.312,1.124)),
    ]:
        panel(name,dims,centre,paint,.0025,parent=body)
    panel('KickPlate',(.908,.57,.12),(0,0,.06),dark,.003,parent=body)
    import numpy as np
    rail_samples=np.array([list(v.co) for obj in bpy.data.objects if obj.name.startswith('Guide_')
                           for v in obj.data.vertices if abs(v.co.x)<.4 and abs(v.co.y)<.2 and 1.65<v.co.z<2.05])
    rail_y,rail_z=np.median(rail_samples[:,1:],axis=0)
    rail_y,rail_z=float(rail_y),float(rail_z)
    guide_rail_z=rail_z;rail_z=1.82
    guide['rail_fitting']={'sample_count':len(rail_samples),'centre_native':[0,rail_y,rail_z],
                           'guide_median_height_m':guide_rail_z,
                           'method':'Generated rail section faired to a circular bar; lowered clear of the opening head so it reads as a hanging rail rather than perimeter trim.'}
    cylinder('Rail',.016,.90,(0,rail_y,rail_z),bare,axis=(1,0,0),sides=24,parent=body)
    for x in (-.46,.46):
        cylinder('RailSocket_L' if x<0 else 'RailSocket_R',.023,.035,(x,rail_y,rail_z),bare,axis=(1,0,0),parent=body)
    # Keep every leaf detail under the hinge-origin mesh, not under the carcass.
    door=panel('Door',(.95,.024,1.98),(-.006,-.344,1.12),paint,.0025)
    hinge_origin(door,(-.500,-.340,.12)); attach(door,root)
    door['parked_open_degrees']=100.0
    door['closed_front_axis']='Blender -Y / glTF +Z'
    for name,dims,centre in [
        ('DoorReturn_L',(.012,.012,1.95),(-.435,-.328,1.12)),
        ('DoorReturn_R',(.012,.012,1.95),(.423,-.328,1.12)),
        ('DoorReturn_T',(.87,.012,.012),(-.006,-.328,2.094)),
        ('DoorReturn_B',(.87,.012,.012),(-.006,-.328,.158)),
    ]:panel(name,dims,centre,paint,.001,parent=door)
    # Pockets stop short of the back skin so the folded door stays closed.
    recess(door,(.340,-.351,1.04),(.062,.018,.148))
    panel('DoorLatchPocket',(.060,.002,.146),(.340,-.343,1.04),dark,.0005,parent=door)
    for x in (.303,.377):
        panel('LatchRim_L' if x<.34 else 'LatchRim_R',(.008,.010,.164),(x,-.358,1.04),paint,.001,parent=door)
    panel('DoorLatchOuter',(.088,.012,.018),(.340,-.367,1.02),bare,.002,parent=door)
    recess(door,(.340,-.331,1.04),(.062,.010,.148))
    panel('InnerLatchPocket',(.060,.001,.146),(.340,-.3355,1.04),dark,.0004,parent=door)
    panel('DoorLatch',(.088,.012,.018),(.340,-.313,1.02),bare,.002,parent=door)
    for i,z in enumerate((1.775,1.82,1.865,1.91)):
        recess(door,(-.08,-.351,z),(.30,.018,.014))
        panel(f'VentBacking_{i}',(.298,.002,.013),(-.08,-.343,z),dark,.0003,parent=door)
        vent=panel(f'DoorVent_{i}',(.32,.016,.022),(-.08,-.363,z),paint,.001,parent=door)
        vent.rotation_euler.x=math.radians(-25)
        recess(door,(-.08,-.331,z),(.30,.010,.014))
        panel(f'InnerVentBacking_{i}',(.298,.001,.013),(-.08,-.3355,z),dark,.0003,parent=door)
        inner=panel(f'InnerDoorVent_{i}',(.32,.016,.022),(-.08,-.320,z),paint,.001,parent=door)
        inner.rotation_euler.x=math.radians(25)
    hinge_parts=[]
    for i,z in enumerate((.33,1.12,1.96)):
        obj=cylinder(f'Hinge_{i}',.012,.085,(-.500,-.340,z),bare,sides=24,parent=body)
        hinge_parts.append(obj)
        panel(f'HingeMount_{i}',(.018,.025,.065),(-.505,-.3295,z),bare,.001,parent=body)
        leaf=panel(f'DoorHingeLeaf_{i}',(.048,.008,.065),(-.4825,-.342,z),bare,.001,parent=door)
        leaf.rotation_euler.z=math.atan2(-.004,.035)
    # The group is named for the visibility gate; welded knuckles remain three shells.
    bpy.ops.object.select_all(action='DESELECT')
    for p in hinge_parts:p.select_set(True)
    bpy.context.view_layer.objects.active=hinge_parts[0]; bpy.ops.object.join()
    hinge_parts[0].name='Hinges'
    frame_points=[]
    for z in [.22+i*.15 for i in range(13)]:
        frame_points.extend([(-.465,-.3253,z),(.465,-.3253,z)])
    for x in [-.38+i*.15 for i in range(6)]:frame_points.append((x,-.3253,2.15))
    rivets('CarcassRivets',frame_points,bare,parent=body)
    door_points=[]
    for z in [.20+i*.16 for i in range(12)]:
        door_points.extend([(-.445,-.355,z),(.433,-.355,z)])
    for x in [-.36+i*.18 for i in range(5)]:
        door_points.extend([(x,-.355,.18),(x,-.355,2.06)])
    rivets('DoorRivetsOuter',door_points,bare,parent=door)
    rivets('DoorRivets',[(x,-.3317,z) for x,y,z in door_points],bare,
           axis=(0,1,0),parent=door)
    SPEC['visible_details'].append('DoorRivets')
    bpy.context.view_layer.update()
    door.rotation_euler.z=math.radians(-100)
    bpy.context.view_layer.update()
    # The parked door envelope is intentionally outside the closed carcass box.
    for obj in bpy.context.scene.objects:
        if obj.type=='MESH' and obj in door.children_recursive and obj.name not in SPEC['bounds_exclude']:
            SPEC['bounds_exclude'].append(obj.name)
    reflect_x([obj for obj in bpy.context.scene.objects if obj.type in {'MESH','EMPTY'}])
    guide['asset_x_reflected_to_match_layout_hinge']=True


if __name__=='__main__':
    build_main(__file__,'wardrobe',assemble,SPEC,(1.0,2.2,.65))
