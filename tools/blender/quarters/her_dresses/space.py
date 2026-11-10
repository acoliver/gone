"""Reserve the real tunic's height-dependent width, leaving room for cloth volume."""
import json
from functools import cache
from pathlib import Path

import numpy as np

HERE=Path(__file__).resolve().parent


@cache
def profile():
    return np.asarray(json.loads((HERE/'tunic-envelope.json').read_text())['height_left_right_m'])


def bounds_at(z,left):
    data=profile()
    edge=float(np.interp(z,data[:,0],data[:,1 if left else 2]))
    return (-.473,edge) if left else (edge,.473)


def reserve():
    from cloth_tools import collision,mesh
    data=profile()
    vertices=[]
    for z,left,right in data:
        vertices.extend(((left,-.31,z),(right,-.31,z),(right,.31,z),(left,.31,z)))
    faces=[(3,2,1,0)]
    for j in range(len(data)-1):
        for i in range(4):faces.append((j*4+i,j*4+(i+1)%4,(j+1)*4+(i+1)%4,(j+1)*4+i))
    faces.append(tuple((len(data)-1)*4+i for i in range(4)))
    obj=mesh('ReservedTunicEnvelope',vertices,faces)
    obj['aged_export']=False;obj['placement_only']=True;obj.hide_render=True
    collision(obj,.0005)


def fit(obj,left):
    moved=0
    maximum=0.
    for vertex in obj.data.vertices:
        low,high=bounds_at(float(vertex.co.z),left)
        before=vertex.co.copy()
        vertex.co.x=float(np.clip(vertex.co.x,low+.001,high-.001))
        vertex.co.y=float(np.clip(vertex.co.y,-.292,.292))
        distance=(vertex.co-before).length
        moved+=distance>1e-7
        maximum=max(maximum,distance)
    obj.data.update()
    return {'projected_vertices':moved,'maximum_projection_m':maximum,
            'constraint':'measured tunic envelope and wardrobe side/front/back interior faces'}

def generate():
    import sys
    sys.path.insert(0,str(HERE.parent/'her_jacket'))
    from verify import tunic
    triangles=np.concatenate([tunic(s).triangles for s in ('remembered','aged')])
    heights=np.arange(.825,1.851,.025)
    rows=[[.14,-.20,.20],[.75,-.20,.20],[.80,-.428,.397]]
    for height in heights:
        selected=triangles[(triangles[:,:,1].min(1)<height+.025)&(triangles[:,:,1].max(1)>height-.025)]
        left=float(selected[:,:,0].min())-.008 if len(selected) else -.08
        right=float(selected[:,:,0].max())+.008 if len(selected) else .08
        rows.append([round(float(height),6),left,right])
    (HERE/'tunic-envelope.json').write_text(json.dumps({
        'source':'Both exported dress_uniform GLBs in the reflected wardrobe-local demo frame, hanging geometry only above shelf',
        'method':'Triangle bounds over +/-25 mm height slabs, 8 mm lateral clearance; below 0.80 m reserve a central 0.40 m width',
        'height_left_right_m':rows},indent=2)+'\n')


if __name__=='__main__':generate()
