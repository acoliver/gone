"""Fit manufactured chair parts to the approved generated seat and back surfaces."""
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'wardrobe'))
from batch_tools import PAINT, beam, cage, cylinder, empty, material, materials, panel, rivets


def rounded_plate(width, height, thickness, radius, mat, parent):
    outline=[]
    for cx,cz,start in ((width/2-radius,height/2-radius,0),
                         (-width/2+radius,height/2-radius,math.pi/2),
                         (-width/2+radius,-height/2+radius,math.pi),
                         (width/2-radius,-height/2+radius,3*math.pi/2)):
        outline.extend((cx+radius*math.cos(start+i*math.pi/8),
                        cz+radius*math.sin(start+i*math.pi/8)) for i in range(5))
    n=len(outline)
    vertices=[(x,y,z) for y in (-thickness/2,thickness/2) for x,z in outline]
    faces=[tuple(range(n)),tuple(reversed(range(n,2*n)))]
    faces.extend((i,i+n,(i+1)%n+n,(i+1)%n) for i in range(n))
    return cage('BackPlate',vertices,faces,mat,.001,parent=parent)


def assemble_chair(guide,spec,height,depth):
    mats=materials(paint_color=spec.get('paint_color',PAINT)); paint=mats['PaintedSteel']; bare=mats['BareSteel']; dark=mats['DarkSteel']
    fabric=material('Fabric',(.020,.024,.022,1),0,.90)
    root=empty('Chair'); frame=empty('Frame',parent=root)
    round_frame=spec.get('round_frame',False)
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
    gap=spec.get('back_gap_m',0)
    guide['back_fit']={'upper_samples':len(top),'lower_samples':len(low),
        'guide_dy_dz':measured_slope,'fitted_dy_dz':slope,'continuous_plate_from_seat':gap==0}

    def frame_beam(name,start,end,thickness):
        if round_frame:
            start,end=Vector(start),Vector(end)
            return cylinder(name,thickness/2,(end-start).length,(start+end)/2,paint,
                            axis=end-start,sides=16,parent=frame)
        return beam(name,start,end,thickness,paint,parent=frame)

    yfront=-depth/2+.025; yback=depth/2-.025
    brace_z=.11; fraction=(brace_z-.014)/(seat-.014)
    brace_x=.225+(.175-.225)*fraction
    brace_front=yfront+(yfront*.78-yfront)*fraction
    brace_back=yback+(yback*.78-yback)*fraction
    for side,x in (('L',-.225),('R',.225)):
        top_x=-.175 if x<0 else .175
        for end,y in (('F',yfront),('B',yback)):
            frame_beam(f'Leg_{side}{end}',(x,y,.014),(top_x,y*.78,seat),.035)
            if round_frame:
                cylinder(f'DeckShoe_{side}{end}',.021,.018,(x,y,.009),dark,sides=16,parent=frame)
            else:
                panel(f'DeckShoe_{side}{end}',(.035,.035,.016),(x,y,.008),bare,.002,parent=frame)
        bx=-brace_x if x<0 else brace_x
        frame_beam(f'SideBrace_{side}',(bx,brace_front,brace_z),(bx,brace_back,brace_z),.024)
        frame_beam(f'BackUpright_{side}',(top_x,yback*.78,seat-.03),
                   (-.205 if x<0 else .205,depth/2-.025,height-.02),.030)
    for end,y in (('F',brace_front),('B',brace_back)):
        frame_beam(f'CrossBrace_{end}',(-brace_x,y,brace_z),(brace_x,y,brace_z),.024)
    panel('SeatPan',(.50,depth-.015,.026),(0,-.0075,seat-.013),paint,.006,parent=frame)
    panel('SeatMountingPlate',(.32,.25,.012),(0,0,seat-.032),dark,.002,parent=frame)
    pad_height=spec.get('pad_height_m',.020)
    panel('SeatPad',(.45,depth-.065,pad_height),(0,-.0125,seat+pad_height/2),fabric,.006,parent=root)
    angle=-math.atan(slope); back_height=height-seat-gap
    centre_z=height-(back_height*math.cos(angle)+.035*abs(math.sin(angle)))/2
    centre_y=depth/2-.020-back_height*abs(math.sin(angle))/2
    if round_frame:
        back=rounded_plate(.46,back_height,.035,.035,paint,frame)
        back.location=(0,centre_y,centre_z)
    else:
        back=panel('BackPlate',(.46,.035,back_height),(0,centre_y,centre_z),paint,.008,parent=frame)
    back.rotation_euler.x=angle
    corner_fraction=(seat-.055-.014)/(seat-.014)
    corner_x=.225+(.175-.225)*corner_fraction
    corner_y=yfront+(yfront*.78-yfront)*corner_fraction-.018
    points=[(x,corner_y,seat-.055) for x in (-corner_x,corner_x)]
    rivets('FrameRivets',points,bare,parent=frame)
    if round_frame:
        panel('SeatFrontLip',(.50,.012,.016),(0,-depth/2+.006,seat+.006),paint,.002,parent=frame)
        for side,x in (('L',-.244),('R',.244)):
            panel(f'SeatLip_{side}',(.012,depth-.015,.016),(x,-.0075,seat+.006),paint,.002,parent=frame)
        bpy.context.view_layer.update()
        points=[back.matrix_world@Vector((x,-.0178,z)) for x in (-.195,.195)
                for z in (-back_height/2+.035,back_height/2-.035)]
        axis=back.matrix_world.to_3x3()@Vector((0,-1,0))
        rivets('BackRivets',points,bare,axis=axis,radius=.006,parent=back)
    spec['pivots_gltf']={'Chair':[0,0,0]}
