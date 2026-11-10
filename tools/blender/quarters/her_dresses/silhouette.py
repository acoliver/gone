"""Fit simulated cloth to the sewn waist/hem measurements without discarding its folds."""
import bpy
import numpy as np

from cloth_tools import retain_pattern


def fit(obj,rail_y,aged=False):
    name=obj.name+('_RawSimulationAged' if aged else '_RawSimulationRemembered')
    source=bpy.data.objects.get(name)
    if source is None:
        source=retain_pattern(obj)
        source.name=name;source.data.name=name
    if len(source.data.vertices)!=len(obj.data.vertices):
        raise ValueError(f'{obj.name}: raw simulation topology differs from fitted cloth')
    positions=np.array([v.co[:] for v in source.data.vertices])
    uv=np.zeros((len(positions),2))
    counts=np.zeros(len(positions))
    for loop in obj.data.loops:
        uv[loop.vertex_index]+=obj.data.uv_layers.active.data[loop.index].uv[:]
        counts[loop.vertex_index]+=1
    if np.any(counts==0):raise ValueError('Unreferenced dress vertex in silhouette fit')
    uv/=counts[:,None]*8
    target_y=uv[:,0]+rail_y
    target_z=uv[:,1]
    group=obj.vertex_groups['SupportStitches'].index
    locked={v.index for v in obj.data.vertices if any(g.group==group and g.weight>.99 for g in v.groups)}
    weight=.65 if aged else .80
    length_weight=.25 if aged else weight
    maximum=0.
    for vertex,p in zip(obj.data.vertices,positions):
        vertex.co=p
        if vertex.index in locked:continue
        vertex.co.y=float((1-weight)*p[1]+weight*target_y[vertex.index])
        vertex.co.z=float((1-length_weight)*p[2]+length_weight*target_z[vertex.index])
        maximum=max(maximum,float(np.linalg.norm(np.array(vertex.co[:])-p)))
    obj.data.update()
    return {'reference_weight':weight,'length_reference_weight':length_weight,'locked_support_stitches':len(locked),
            'maximum_fit_m':maximum,'raw_simulation_object':name,
            'method':'Keep simulated depth and folds; blend width and length toward the sewn pattern measurements to preserve the A-line silhouette'}
