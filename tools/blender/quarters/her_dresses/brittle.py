"""Dry woven surfaces and a compact fibre volume beneath the loose yarns."""
import math

import bpy
import numpy as np

from cloth_tools import ASSETS,image_from_array,mesh


def surface(mat,color):
    shader=mat.node_tree.nodes['Principled BSDF']
    shader.inputs['Specular IOR Level'].default_value=.08
    shader.inputs['Sheen Weight'].default_value=0
    shader.inputs['Roughness'].default_value=.98
    normal=next(n for n in mat.node_tree.nodes if n.type=='NORMAL_MAP')
    normal.inputs['Strength'].default_value=.65
    texture=shader.inputs['Base Color'].links[0].from_node
    source=bpy.data.images.load(str(ASSETS/'sofa/weave.png'),check_existing=True)
    pixels=np.array(source.pixels[:],dtype=np.float32).reshape(source.size[1],source.size[0],4)
    grain=pixels[:,:,:3].mean(2)
    grain=np.clip(grain/np.median(grain),.65,1.35)
    rgba=np.ones_like(pixels)
    rgba[:,:,:3]=np.asarray(color)*(.62+.38*grain[:,:,None])
    texture.image=image_from_array(mat.name+'_dry_weave',rgba,
        ASSETS/'her_dresses_textures'/(mat.name.lower()+'.png'))


def heap(name,x,rail_y,mat):
    old=bpy.data.objects.get(name)
    if old is not None:bpy.data.objects.remove(old,do_unlink=True)
    vertices=[(x,rail_y,.1588)]
    faces=[]
    count=24
    for ring in range(1,5):
        r=ring/4
        for j in range(count):
            a=2*math.pi*j/count
            edge=1+.07*math.sin(a*5)+.035*math.sin(a*9+.6)
            vertices.append((x+.053*r*edge*math.cos(a),rail_y+.19*r*edge*math.sin(a),
                             .1448+.014*(1-r*r)**2))
        if ring==1:
            faces.extend((0,1+j,1+(j+1)%count) for j in range(count))
        else:
            lower=1+(ring-2)*count;upper=lower+count
            faces.extend((lower+j,lower+(j+1)%count,upper+(j+1)%count,upper+j) for j in range(count))
    obj=mesh(name,vertices,faces)
    obj.data.materials.append(mat)
    return obj
