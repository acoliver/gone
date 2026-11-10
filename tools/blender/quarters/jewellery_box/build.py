"""Personal rounded hard-plastic jewellery box with brass trim and clasp."""
from pathlib import Path
import math
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'photo_frame'))
import small_common as sc


def rounded_body(name,dims,z0,radius,edge,mat,dome=False):
    width,depth,height=dims
    vertices=[]
    levels=[(z0,edge),(z0+edge,0),(z0+height-edge,0),(z0+height,edge)] if edge else [(z0,0),(z0+height,0)]
    if dome:
        levels=[(z0,edge),(z0+edge,0),(z0+.007,0),(z0+.013,.007),(z0+height,.017)]
    for z,inset in levels:
        for cx,cy,start in [(1,1,0),(-1,1,90),(-1,-1,180),(1,-1,270)]:
            for i in range(6):
                angle=math.radians(start+i*90/5)
                vertices.append((cx*(width/2-radius)+(radius-inset)*math.cos(angle),
                                 cy*(depth/2-radius)+(radius-inset)*math.sin(angle),z))
    count=24
    faces=[tuple(reversed(range(count)))]
    for band in range(len(levels)-1):
        faces.extend((band*count+i,band*count+(i+1)%count,
                      (band+1)*count+(i+1)%count,(band+1)*count+i) for i in range(count))
    faces.append(tuple(range((len(levels)-1)*count,len(levels)*count)))
    obj=sc.bt.cage(name,vertices,faces,mat,0)
    for poly in obj.data.polygons:
        poly.use_smooth=len(poly.vertices)==4
    return obj


def assemble(m):
    for name in ['IvoryPlastic','BluePlastic']:
        m[name].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.20
    m['BluePlastic'].node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.028,.105,.165,1)
    rounded_body('Body',(.15,.10,.032),0,.023,.004,m['IvoryPlastic'])
    rounded_body('BrassRim',(.148,.098,.002),.032,.022,0,m['Brass'])
    lid=rounded_body('Lid',(.146,.096,.016),.034,.022,.003,m['BluePlastic'],dome=True)
    sc.bt.hinge_origin(lid,(0,.048,.034))
    for i,x in enumerate([-.039,.039]):
        sc.bt.cylinder(f'Hinge_{i}',.0025,.020,(x,.048,.033),m['Brass'],axis=(1,0,0),sides=12,edge=0)
    sc.box('Clasp',(.013,.003,.011),(0,-.050,.031),m['Brass'],.001,2)
    sc.box('ClaspLever',(.007,.002,.005),(0,-.052,.030),m['Brass'],.0006,2)


if __name__=='__main__':
    sc.main(__file__,'jewellery_box',assemble)
