"""Rasterise real surface positions into the shared small-prop UV atlas."""
import subprocess
from pathlib import Path

import numpy as np


def bake(root, item, objects, size=512):
    position=np.zeros((size,size,3),dtype=np.float32)
    normal=np.zeros_like(position)
    valid=np.zeros((size,size),dtype=bool)
    for obj in objects:
        mesh=obj.data
        mesh.calc_loop_triangles()
        uv=mesh.uv_layers.active.data
        for tri in mesh.loop_triangles:
            material=obj.material_slots[tri.material_index].material.name
            if material not in {'Ceramic','Glaze','Stain','DustCeramic'}:
                continue
            coords=np.array([mesh.vertices[i].co[:] for i in tri.vertices])
            points=np.array([uv[i].uv[:] for i in tri.loops])*size
            points[:,1]=size-points[:,1]
            lo=np.maximum(np.floor(points.min(axis=0)).astype(int),0)
            hi=np.minimum(np.ceil(points.max(axis=0)).astype(int),size-1)
            x,y=np.meshgrid(np.arange(lo[0],hi[0]+1)+.5,np.arange(lo[1],hi[1]+1)+.5)
            a,b,c=points
            denominator=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
            if abs(denominator)<1e-12:
                raise ValueError('Zero-area ceramic UV triangle')
            u=((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/denominator
            v=((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/denominator
            w=1-u-v
            inside=(u>=-1e-6)&(v>=-1e-6)&(w>=-1e-6)
            region=np.s_[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
            mapped=u[...,None]*coords[0]+v[...,None]*coords[1]+w[...,None]*coords[2]
            position[region][inside]=mapped[inside]
            normal[region][inside]=tri.normal[:]
            valid[region][inside]=True
    folder=root/'tmp/small'/item
    folder.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(folder/'surface.npz',position=position,normal=normal,valid=valid)
    subprocess.run(['/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python',
                    str(root/'tools/blender/quarters/photo_frame/texture_bake.py'),item,'--surface'],check=True)
