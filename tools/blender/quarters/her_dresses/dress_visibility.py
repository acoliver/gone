"""Projected dress area left visible by the fixed doorway camera."""
import numpy as np
import trimesh

MINIMUM_VISIBLE_AREA=.90


def doorway_fractions(parts,wardrobe,tunic):
    eye=np.array([-3.45,1.65,3.675])
    forward=np.array([5.85,-.4,0.]);forward/=np.linalg.norm(forward)
    right=np.cross(forward,[0,1,0]);right/=np.linalg.norm(right)
    up=np.cross(right,forward)
    result={}
    for name,other in [('RoseDress','BlueDress'),('BlueDress','RoseDress')]:
        part=parts[name]
        delta=part.triangles_center-eye
        distance=np.linalg.norm(delta,axis=1)
        directions=delta/distance[:,None]
        weights=part.area_faces*np.maximum(0,-np.sum(part.face_normals*directions,axis=1))/distance**2
        depth=delta@forward
        half_width=depth*np.tan(np.radians(50))
        visible=(depth>0)&(np.abs(delta@right)<=half_width)&(np.abs(delta@up)<=half_width*864/1536)
        blockers=trimesh.util.concatenate([wardrobe,tunic,parts[other]])
        locations,rays,_=blockers.ray.intersects_location(np.tile(eye,(len(delta),1)),directions,multiple_hits=False)
        locations=np.asarray(locations).reshape(-1,3)
        visible[rays]&=np.linalg.norm(locations-eye,axis=1)>=distance[rays]-.0001
        if weights.sum()<=0:raise ValueError('Dress has no camera-facing projected area')
        result[name]=float(weights[visible].sum()/weights.sum())
    return result
