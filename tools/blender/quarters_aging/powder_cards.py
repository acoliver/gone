"""Irregular floor deposits with numpy alpha-scissor powder coverage."""
from pathlib import Path

import bpy
import numpy as np

from fabric_mesh import material, new_object
from fringe_cards import image_from_array


def powder_texture(seed, size=1024):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[-1:1:complex(size), -1:1:complex(size)]
    radius = np.sqrt(x*x+y*y)
    edge = .83+.05*np.sin(np.arctan2(y, x)*7)+.03*np.cos(x*31+y*19)
    density = np.clip((edge-radius)*10, 0, 1)
    alpha = (rng.random((size, size)) < density).astype(np.float32)
    rgba = np.empty((size, size, 4), dtype=np.float32)
    rgba[:, :, :3] = np.array([.28, .19, .10])*(.85+.15*rng.random((size, size, 1)))
    rgba[:, :, 3] = alpha
    return rgba


def powder_card(name, centre, extent, out, seed):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    image = image_from_array(name, powder_texture(seed), out/f'{name.lower()}.png')
    rng = np.random.default_rng(seed+1)
    height = rng.uniform(.0005, .002, (1024, 1024))
    gy, gx = np.gradient(height)
    texel = 2*min(extent)/1024
    normals = np.stack([-gx/texel, -gy/texel, np.ones_like(gx)], axis=2)
    normals /= np.linalg.norm(normals, axis=2, keepdims=True)
    normal_rgba = np.ones((1024, 1024, 4), dtype=np.float32)
    normal_rgba[:, :, :3] = normals*.5+.5
    normal_image = image_from_array(name+'Normal', normal_rgba, out/f'{name.lower()}_normal.png', True)
    mat = material('FloorDust_'+name, (.28, .19, .10))
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    tex = nodes.new('ShaderNodeTexImage')
    tex.image = image
    shader = nodes.get('Principled BSDF')
    links.new(tex.outputs['Color'], shader.inputs['Base Color'])
    normal_tex = nodes.new('ShaderNodeTexImage')
    normal_tex.image = normal_image
    nm = nodes.new('ShaderNodeNormalMap')
    links.new(normal_tex.outputs['Color'], nm.inputs['Color'])
    links.new(nm.outputs['Normal'], shader.inputs['Normal'])
    cutoff = nodes.new('ShaderNodeMath')
    cutoff.operation = 'ROUND'
    links.new(tex.outputs['Alpha'], cutoff.inputs[0])
    links.new(cutoff.outputs[0], shader.inputs['Alpha'])
    rng = np.random.default_rng(seed)
    angle = np.linspace(0, 2*np.pi, 49)[:-1]
    radius = rng.uniform(.90, 1., len(angle))
    uv = np.c_[np.cos(angle)*radius, np.sin(angle)*radius]
    vertices = [tuple(centre)]+[(centre[0]+u*extent[0], centre[1]+v*extent[1], centre[2]) for u, v in uv]
    faces = [(0, i+1, (i+1)%len(angle)+1) for i in range(len(angle))]
    obj = new_object(name, vertices, faces, mat)
    patterns = np.vstack([[.5, .5], (uv+1)/2])
    for loop in obj.data.loops:
        obj.data.uv_layers.active.data[loop.index].uv = patterns[loop.vertex_index]
    return obj
