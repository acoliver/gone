"""Fit manufactured chair parts to the approved generated seat and back surfaces."""
import math
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'wardrobe'))
from batch_tools import PAINT, beam, empty, material, materials, panel, rivets


def assemble_chair(guide,spec,height,depth):
    mats=materials(paint_color=spec.get('paint_color',PAINT)); paint=mats['PaintedSteel']; bare=mats['BareSteel']; dark=mats['DarkSteel']
    fabric=material('Fabric',(.020,.024,.022,1),0,.90)
    root=empty('Chair'); frame=empty('Frame',parent=root)
    cloud=np.array([list(v.co) for obj in bpy.data.objects if obj.name.startswith('Guide_')
                    for v in obj.data.vertices])
    samples=cloud[(np.abs(cloud[:,0])<.18)&(np.abs(cloud[:,1])<depth*.32)&
                  (cloud[:,2]>.30)&(cloud[:,2]<.58)]
    measured=float(np.median(samples[:,2])); seat=float(np.clip(measured,.42,.46))
    guide['seat_fit']={'sample_count':len(samples),'guide_height_m':measured,'fitted_seat_height_m':seat}
    top=cloud[(np.abs(cloud[:,0])<.12)&(cloud[:,1]>.06)&(cloud[:,2]>height-.18)&(cloud[:,2]<height-.05)]
    low=cloud[(np.abs(cloud[:,0])<.12)&(cloud[:,1]>.06)&(cloud[:,2]>seat+.03)&(cloud[:,2]<seat+.10)]
    measured_slope=float((np.median(top[:,1])-np.median(low[:,1]))/(np.median(top[:,2])-np.median(low[:,2])))
    slope=float(np.clip(measured_slope,.10,.18))
    guide['back_fit']={'upper_samples':len(top),'lower_samples':len(low),
        'guide_dy_dz':measured_slope,'fitted_dy_dz':slope,'continuous_plate_from_seat':True}
    yfront=-depth/2+.025; yback=depth/2-.025
    brace_z=.11; fraction=(brace_z-.014)/(seat-.014)
    brace_x=.225+(.175-.225)*fraction
    brace_front=yfront+(yfront*.78-yfront)*fraction
    brace_back=yback+(yback*.78-yback)*fraction
    for side,x in (('L',-.225),('R',.225)):
        top_x=-.175 if x<0 else .175
        for end,y in (('F',yfront),('B',yback)):
            beam(f'Leg_{side}{end}',(x,y,.014),(top_x,y*.78,seat),.035,paint,parent=frame)
            panel(f'DeckShoe_{side}{end}',(.035,.035,.016),(x,y,.008),bare,.002,parent=frame)
        bx=-brace_x if x<0 else brace_x
        beam(f'SideBrace_{side}',(bx,brace_front,brace_z),(bx,brace_back,brace_z),.024,paint,parent=frame)
        beam(f'BackUpright_{side}',(top_x,yback*.78,seat-.03),
             (-.205 if x<0 else .205,depth/2-.025,height-.02),.030,paint,parent=frame)
    for end,y in (('F',brace_front),('B',brace_back)):
        beam(f'CrossBrace_{end}',(-brace_x,y,brace_z),(brace_x,y,brace_z),.024,paint,parent=frame)
    panel('SeatPan',(.50,depth-.015,.026),(0,-.0075,seat-.013),paint,.006,parent=frame)
    panel('SeatMountingPlate',(.32,.25,.012),(0,0,seat-.032),dark,.002,parent=frame)
    panel('SeatPad',(.45,depth-.065,.020),(0,-.0125,seat+.010),fabric,.006,parent=root)
    angle=-math.atan(slope); back_height=height-seat
    centre_z=height-(back_height*math.cos(angle)+.035*abs(math.sin(angle)))/2
    centre_y=depth/2-.020-back_height*abs(math.sin(angle))/2
    back=panel('BackPlate',(.46,.035,back_height),(0,centre_y,centre_z),paint,.008,parent=frame)
    back.rotation_euler.x=angle
    corner_fraction=(seat-.055-.014)/(seat-.014)
    corner_x=.225+(.175-.225)*corner_fraction
    corner_y=yfront+(yfront*.78-yfront)*corner_fraction-.018
    points=[(x,corner_y,seat-.055) for x in (-corner_x,corner_x)]
    rivets('FrameRivets',points,bare,parent=frame)
    spec['pivots_gltf']={'Chair':[0,0,0]}
