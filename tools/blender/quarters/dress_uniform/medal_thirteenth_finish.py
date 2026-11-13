"""Bounded normal curvature inside the generated medal's retained die facets."""
import numpy as np


def pillow_slopes(points, radius, max_degrees):
    """Differentiate a smooth die pillow with zero height and slope at its edges."""
    if radius <= 0 or max_degrees < 0:
        raise ValueError('Positive facet radius and nonnegative tilt are required')
    points=np.asarray(points,dtype=float)
    r=np.linalg.norm(points,axis=-1)
    theta=np.mod(np.arctan2(points[...,0],points[...,1]),2*np.pi)
    q=np.mod(theta,np.pi/5)/(np.pi/5)
    u=np.clip(r/radius,0,1)
    radial=np.sin(np.pi*u)**2
    angular=np.sin(np.pi*q)**2
    dr=np.pi*np.sin(2*np.pi*u)*angular
    dt=radial*5*np.sin(2*np.pi*q)/np.maximum(u,1e-12)
    dr=np.where(r<radius,dr,0)
    dt=np.where(r<radius,dt,0)
    # The analytic gradient is bounded by 5*pi; this keeps the limit independent
    # of the sample positions, atlas resolution and material island coverage.
    scale=np.tan(np.radians(max_degrees))/(5*np.pi)
    return scale*np.stack([dr*np.sin(theta)+dt*np.cos(theta),dr*np.cos(theta)-dt*np.sin(theta)],axis=-1)
