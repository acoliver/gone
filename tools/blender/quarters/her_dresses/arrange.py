"""Face the dresses into the room while keeping their hooks on the fixed rail."""
import math

import numpy as np

POSITIONS={'RoseDress':(-.451,-.21),'BlueDress':(.438,.29)}
FRONT_OFFSET=.21
WIDTH_SCALE=.75
RAIL_Y=-.003038027


def positions(points,name,hanger=False):
    points=np.array(points,dtype=float,copy=True)
    old,new=POSITIONS[name]
    fraction=np.clip((1.758-points[:,2])/(1.758-1.69),0,1)
    angle=math.pi/2*fraction
    dx=points[:,0]-old
    dy=points[:,1]-RAIL_Y
    result=points.copy()
    result[:,0]=new+np.cos(angle)*dx-np.sin(angle)*dy*WIDTH_SCALE
    result[:,1]=RAIL_Y+np.sin(angle)*dx+np.cos(angle)*dy-FRONT_OFFSET*fraction
    if hanger and old<0:result[:,0]-=.026*(1-fraction)
    return result


def apply(obj,name):
    result=positions([v.co[:] for v in obj.data.vertices],name,obj.name.endswith('_Hanger'))
    for vertex,point in zip(obj.data.vertices,result):vertex.co=point
    obj.data.update()
    return {'rail_x_m':POSITIONS[name][1],'front_offset_m':FRONT_OFFSET,
            'width_scale':WIDTH_SCALE,'hanger_yaw_deg':90,
            'hook':'Original rail-wrapping hook retained; neck turns into the offset display shoulder below 1.758 m'}
