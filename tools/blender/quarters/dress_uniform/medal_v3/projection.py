"""Frozen studio and registered game-camera projections in pixel units."""
from pathlib import Path
import json,re
import numpy as np
SOURCE=Path(__file__).resolve().parent;ROOT=SOURCE.parents[4];OUT=ROOT/'tmp/issue130-v3/fit1'
match=json.loads((OUT/'camera-match.json').read_text())
reg=json.loads((SOURCE/'game-registration.json').read_text())['frame']
game=json.loads((SOURCE/'game-close-camera.json').read_text())['camera']
transform=np.array([float(n) for n in re.findall(r'-?\d+(?:\.\d+)?',game['transform'])]).reshape(4,3)

def project(v,camera):
 if camera=='studio':
  pos=np.array(match['position']);target=np.array(match['target']);direction=target-pos;direction/=np.linalg.norm(direction)
  right=np.cross(direction,[0,0,1.]);right/=np.linalg.norm(right);up=np.cross(right,direction)
  result=np.c_[(v*100-pos)@right,-(v*100-pos)@up]/5.05*900+450
  assert np.isfinite(result).all()
  return result
 authored=v@np.array(reg['frame'])+np.array(reg['origin'])
 world=np.c_[-authored[:,1],authored[:,2],-authored[:,0]]+[41.32804,-9.18,5.3]
 delta=world-transform[3];depth=-(delta@transform[2]);assert np.all(depth>0)
 focal=game['size'][0]/(2*np.tan(np.deg2rad(game['fov'])/2))
 result=np.c_[delta@transform[0],-delta@transform[1]]/depth[:,None]*focal+np.array(game['size'])/2
 assert np.isfinite(result).all()
 return result
