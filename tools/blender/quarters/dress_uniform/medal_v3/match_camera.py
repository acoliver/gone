"""Estimate the input's oblique camera from the blue enamel's ellipse.

This is numerical image measurement only, not visual evaluation. The measured
ellipse is approximate because the star and rim occlude parts of the field.
"""
from pathlib import Path
import json
import math

import numpy as np
from PIL import Image
from scipy.optimize import least_squares
from scipy.spatial import ConvexHull

ROOT=Path(__file__).resolve().parents[5]
SOURCE=Path(__file__).resolve().parent
OUT=ROOT/'tmp/issue130-v3/fit1'
im=np.asarray(Image.open(SOURCE/'frozen-c01-seed1306201.png').convert('RGB'),dtype=float)
r,g,b=im.transpose(2,0,1)
y,x=np.nonzero((b>r*1.15)&(b>g*1.04)&(b>35))
points=np.c_[x,y]
hull=points[ConvexHull(points).vertices]


def residual(v):
    cx,cy,la,lb,t=v
    a,b=np.exp([la,lb])
    c,s=np.cos(t),np.sin(t)
    dx,dy=hull[:,0]-cx,hull[:,1]-cy
    return ((c*dx+s*dy)/a)**2+((-s*dx+c*dy)/b)**2-1


v=least_squares(residual,[*hull.mean(0),np.log(np.ptp(x)/2),np.log(np.ptp(y)/2),0]).x
a,b=np.exp(v[2:4])
c,s=np.cos(v[4]),np.sin(v[4])
rotation=np.array([[c,-s],[s,c]])
cov=rotation@np.diag([a*a,b*b])@rotation.T/max(a*a,b*b)
# Image +Y is down, whereas the studio camera's up is +Z.
cov[0,1]*=-1
cov[1,0]*=-1
theta=math.acos(math.sqrt(cov[0,0]))
phi=math.asin(cov[0,1]/(math.cos(theta)*math.sin(theta)))
distance=10.
target=[0.,0.,.5]
position=[-distance*math.sin(theta)*math.cos(phi),
          -distance*math.cos(theta)*math.cos(phi),.5+distance*math.sin(phi)]
report={'blue_mask_pixels':len(points),'ellipse_axes_px':[float(a),float(b)],
        'ellipse_rotation_degrees':float(np.degrees(v[4])),
        'ellipse_equation_residual_rms':float(np.sqrt(np.mean(residual(v)**2))),
        'azimuth_degrees':math.degrees(theta),'elevation_degrees':math.degrees(phi),
        'position':position,'target':target,
        'limitation':'Approximate orthographic fit to blue-field hull; no visual judgment or perspective-camera calibration.'}
(OUT/'camera-match.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
