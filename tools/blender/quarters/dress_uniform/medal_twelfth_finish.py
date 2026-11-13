"""Photo-derived die variation and lower-contrast woven ribbon detail."""
import numpy as np


def normalized_photo(values):
    centered=np.asarray(values,dtype=float)-np.mean(values)
    deviation=centered.std()
    if deviation<=np.finfo(float).eps:
        raise ValueError('Photographic field has no measured variation')
    return centered/deviation


def tilt_planes(planes,detail,max_degrees):
    """Tilt each fitted plane within a circular angular bound, without moving vertices."""
    planes=np.asarray(planes,dtype=float)
    direction=np.c_[detail[:,0],np.zeros(len(detail)),detail[:,1]]
    direction-=planes*np.einsum('ij,ij->i',planes,direction)[:,None]
    length=np.linalg.norm(direction,axis=1)
    maximum=length.max()
    if maximum==0:return planes.copy()
    slope=direction/maximum*np.tan(np.radians(max_degrees))
    result=planes+slope
    return result/np.linalg.norm(result,axis=1)[:,None]


def ribbon_field(photo):
    """Retain fine photographed ribs while lowering row-uniform molded bands."""
    return photo-.85*photo.mean(axis=1,keepdims=True)
