"""Fit lapel facings and buttons to the simulated garment's flat-pattern UVs."""
import bpy
import numpy as np
from mathutils import Vector

from cloth_tools import bake_transforms, mesh, plain


def front_count():
    return sum(p.center.y<0 for p in bpy.data.objects['Jacket_CutPattern'].data.polygons)


def sample(obj,x,z,front=True):
    obj.data.calc_loop_triangles()
    target=np.array([x,z])*8
    for tri in obj.data.loop_triangles:
        if (tri.polygon_index<front_count())!=front:continue
        uv=np.array([obj.data.uv_layers.active.data[i].uv[:] for i in tri.loops])
        matrix=np.c_[uv[1]-uv[0],uv[2]-uv[0]]
        if abs(np.linalg.det(matrix))<1e-10:continue
        u,v=np.linalg.solve(matrix,target-uv[0])
        if u>=-1e-5 and v>=-1e-5 and u+v<=1+1e-5:
            position=sum((obj.data.vertices[i].co*w for i,w in zip(tri.vertices,(1-u-v,u,v))),Vector())
            return position,Vector(tri.normal)
    raise ValueError(f'No cloth at pattern coordinate {x,z}, front={front}')


def clip(subject,outline):
    area=sum(np.cross(outline[(i+1)%len(outline)]-outline[i],outline[(i+2)%len(outline)]-outline[(i+1)%len(outline)]) for i in range(len(outline)))
    if area<0:outline=outline[::-1]
    for a,b in zip(outline,np.roll(outline,-1,axis=0)):
        output=[]
        for p,q in zip(subject,subject[1:]+subject[:1]):
            dp=float(np.cross(b-a,p[:2]-a));dq=float(np.cross(b-a,q[:2]-a))
            if dp>=-1e-9:output.append(p)
            if (dp>=0)!=(dq>=0):output.append(p+(q-p)*dp/(dp-dq))
        subject=output
        if not subject:break
    return subject


def lapel(obj,side,mat):
    outline=np.array([(side*.027,.837),(side*.102,.815),(side*.066,.744),(side*.027,.685)])*8
    vertices,faces=[],[]
    for tri in obj.data.loop_triangles:
        if tri.polygon_index>=front_count():continue
        uv=np.array([obj.data.uv_layers.active.data[i].uv[:] for i in tri.loops])
        if np.any(uv.max(0)<outline.min(0)) or np.any(uv.min(0)>outline.max(0)):continue
        points=np.array([obj.data.vertices[i].co[:] for i in tri.vertices])
        polygon=clip([np.r_[q,p] for q,p in zip(uv,points)],outline)
        polygon=[p for i,p in enumerate(polygon) if np.linalg.norm(p-polygon[i-1])>1e-8]
        if len(polygon)<3:continue
        center=uv.mean(0)/8
        back,_=sample(obj,*center,front=False)
        n=Vector(tri.normal)
        if n.dot(Vector(points.mean(0))-back)<0:n.negate()
        start=len(vertices)
        vertices.extend(tuple(Vector(p[2:])+n*.0002) for p in polygon)
        for i in range(1,len(polygon)-1):faces.append((start,start+i,start+i+1))
    result=mesh('Lapel_L' if side<0 else 'Lapel_R',vertices,faces)
    result.data.materials.append(mat)


def add_tailoring(obj,aged=False):
    mat=plain('FadedLapelFacing' if aged else 'LapelWoolFacing',(.17,.195,.20) if aged else (.035,.055,.075))
    for side in (-1,1):lapel(obj,side,mat)
    buttons=plain('FadedJacketButtons' if aged else 'JacketButtons',(.105,.10,.09) if aged else (.02,.025,.03),.05 if aged else .15)
    for index,z in enumerate((.55,.45,.35)):
        p,n=sample(obj,.034,z)
        back,_=sample(obj,.034,z,False)
        if n.dot(p-back)<0:n.negate()
        bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=6,radius=1,location=p+n*.0012)
        button=bpy.context.object;button.name=f'JacketButton_{index}'
        button.scale=(.004,.004,.001)
        button.rotation_euler=n.to_track_quat('Z','Y').to_euler()
        button.data.materials.append(buttons);bake_transforms(button)
