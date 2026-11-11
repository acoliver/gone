"""First-hit #130 runtime masks, including near clipping and material culling."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[4]


def trace(game, state, view):
    camera = (json.loads((game/f'{state}-oblique-camera.json').read_text()) if view == 'oblique-context'
              else json.loads((game/'numeric-cameras.json').read_text())[f'{state}-{view}'])
    transform = np.array(camera['matrix_columns'])
    basis, origin = transform[:3].T, transform[3]
    focal = 1536/(2*np.tan(np.radians(camera['fov'])/2))
    sources = json.loads((game/f'{state}-geometry.json').read_text())
    fit = json.loads((ROOT/'assets/props/quarters/dress_uniform/medal/contact-frames.json').read_text())['aged' if state=='present' else 'as_built']['source_frame']
    feature = np.load(ROOT/'tmp/issue130-photoreal/stage1c/low-geometry.npz')
    centres = feature['vertices'][feature['faces']].mean(1)
    triangles, roles, regions, culls, projections, parities, local_triangles, uv_triangles = [], [], [], [], [], [], [], []
    for item in sources:
        v=np.array(item['positions']); indices=np.array(item['indices']).reshape(-1,3)
        role = (1 if item['slot']==0 else (2 if item['slot']==1 else 3)) if item['part']=='Medal' else (4 if item['part']=='TunicBody' else 0)
        reg=np.full(len(indices),-1,int)
        local=np.array(item['local_positions'])[:,[0,2,1]]*np.array([1,-1,1])
        local=np.einsum('ij,kj->ik',local-np.array(fit['origin']),np.array(fit['frame']))
        local_triangles.append(local[indices])
        uv_triangles.append(np.array(item['uv'])[indices] if role in [1,2] else np.zeros((len(indices),3,2)))
        if role in [1,2]:
            query=local[indices].mean(1)
            for start in range(0,len(query),64):
                delta=query[start:start+64,None,:]-centres[None,:,:]
                nearest=np.einsum('ijk,ijk->ij',delta,delta).argmin(1)
                reg[start:start+64]=feature['regions'][nearest]
            cv=np.einsum('ij,jk->ik',v-origin,basis)
            projections.append(np.c_[768+focal*cv[:,0]/-cv[:,2],432-focal*cv[:,1]/-cv[:,2]])
        triangles.append(v[indices]);roles.extend([role]*len(indices));regions.extend(reg);culls.extend([item['cull_mode']]*len(indices));parities.extend([item['parity']]*len(indices))
    triangles=np.concatenate(triangles)
    faces=np.arange(triangles.size//3).reshape(-1,3)
    bvh=BVHTree.FromPolygons(((triangles-origin)*1000).reshape(-1,3).tolist(),faces.tolist(),all_triangles=True)
    normals=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])*np.array(parities)[:,None]
    bounds=np.concatenate(projections)
    lo=np.maximum(np.floor(bounds.min(0)-60).astype(int),0)
    hi=np.minimum(np.ceil(bounds.max(0)+60).astype(int),[1535,863])
    xx,yy=np.meshgrid(np.arange(lo[0],hi[0]+1),np.arange(lo[1],hi[1]+1))
    x,y=xx.ravel(),yy.ravel()
    directions=np.einsum('ij,kj->ik',np.c_[(x+.5-768)/focal,-(y+.5-432)/focal,-np.ones(len(x))],basis)
    directions/=np.linalg.norm(directions,axis=1)[:,None]
    hit_points=np.zeros((len(x),3))
    hit_ids=np.full(len(x),-1,int)
    for index,direction in enumerate(directions):
        start=direction*(camera['near']*1000)/np.dot(direction,-basis[:,2])
        for step in range(100):
            point,_,face,_=bvh.ray_cast(Vector(start),Vector(direction))
            if face is None: break
            front=np.dot(normals[face],direction)>0
            if culls[face]==2 or (front and culls[face]==0) or (not front and culls[face]==1):
                hit_ids[index]=face;hit_points[index]=point;break
            start=np.array(point)+direction*max(.0001,np.max(abs(np.array(point)))*np.finfo(np.float32).eps*4)
        else: raise ValueError('Ray did not exit runtime surfaces')
    valid=hit_ids>=0;ids=np.maximum(hit_ids,0)
    role=np.zeros((864,1536),np.uint8);region=np.full((864,1536),-1,np.int16)
    role[y[valid],x[valid]]=np.array(roles)[ids[valid]]
    region[y[valid],x[valid]]=np.array(regions)[ids[valid]]
    selected=hit_ids[valid]
    t=triangles[selected]
    delta=origin+hit_points[valid]/1000-t[:,0]
    e1,e2=t[:,1]-t[:,0],t[:,2]-t[:,0]
    dot=lambda a,b:np.einsum('ij,ij->i',a,b)
    aa,ab,bb=dot(e1,e1),dot(e1,e2),dot(e2,e2)
    denom=aa*bb-ab*ab
    u=(bb*dot(delta,e1)-ab*dot(delta,e2))/denom
    v=(aa*dot(delta,e2)-ab*dot(delta,e1))/denom
    bary=np.c_[1-u-v,u,v]
    hit_local=np.einsum('ij,ijk->ik',bary,np.concatenate(local_triangles)[selected])
    hit_uv=np.einsum('ij,ijk->ik',bary,np.concatenate(uv_triangles)[selected])
    uv_image=np.zeros((864,1536,2),np.float32)
    uv_image[y[valid],x[valid]]=hit_uv
    local_image=np.full((864,1536,3),np.nan,np.float32)
    local_image[y[valid],x[valid]]=hit_local
    np.savez_compressed(game/f'{state}-{view}-raw-masks.npz',local=local_image[40:],uv=uv_image[40:],role=role[40:],region=region[40:],names=feature['region_names'],width=np.ptp(bounds[:,0]))
    print(state,view,'first-hit counts',np.unique(role,return_counts=True),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--game',type=Path,required=True)
    game=p.parse_args(sys.argv[sys.argv.index('--')+1:]).game.resolve()
    for state in ['remembered','present']:
        for view in ['medal','buttons','wardrobe']: trace(game,state,view)
        if (game/f'{state}-oblique-camera.json').exists(): trace(game,state,'oblique-context')
