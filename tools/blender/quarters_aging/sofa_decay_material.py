"""Exportable sofa swatches: bake AO into RGBA instead of unsupported colour math."""
from pathlib import Path

import bpy
import numpy as np

from fringe_cards import fringe_material, image_from_array
from sofa_decay_policy import UPHOLSTERY


def linear_to_srgb(values):
    values = np.asarray(values)
    return np.where(values <= .0031308, values*12.92, 1.055*np.maximum(values, 0)**(1/2.4)-.055)


def albedo_pixels(ao, color, opacity=None):
    result = np.ones_like(ao)
    result[:, :, :3] = linear_to_srgb(ao[:, :, :3]*np.asarray(color))
    if opacity is not None:
        result[:, :, 3] = opacity[:, :, 0]
    return result


def exportable_material(mat, color, out, opacity=None):
    """Direct image inputs survive glTF export, including their actual albedo."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    shader = nodes['Principled BSDF']
    ao_image = nodes['AO'].image
    width, height = ao_image.size
    ao = np.array(ao_image.pixels[:], dtype=np.float32).reshape((height, width, 4))
    alpha = np.array(opacity.pixels[:], dtype=np.float32).reshape((height, width, 4)) if opacity else None
    pixels = albedo_pixels(ao, color, alpha)
    image = image_from_array(mat.name+'_Albedo', pixels, out/(mat.name.lower()+'_albedo.png'))
    uv = nodes.new('ShaderNodeUVMap')
    uv.uv_map = 'BakeUV'
    tex = nodes.new('ShaderNodeTexImage')
    tex.image = image
    links.new(uv.outputs['UV'], tex.inputs['Vector'])
    links.new(tex.outputs['Color'], shader.inputs['Base Color'])
    if opacity:
        cutoff = nodes.new('ShaderNodeMath')
        cutoff.operation = 'ROUND'
        links.new(tex.outputs['Alpha'], cutoff.inputs[0])
        links.new(cutoff.outputs[0], shader.inputs['Alpha'])
    normal_tex = nodes['NORMAL']
    links.new(uv.outputs['UV'], normal_tex.inputs['Vector'])
    normal = nodes.new('ShaderNodeNormalMap')
    normal.uv_map = 'BakeUV'
    links.new(normal_tex.outputs['Color'], normal.inputs['Color'])
    links.new(normal.outputs['Normal'], shader.inputs['Normal'])
    shader.inputs['Roughness'].default_value = .98
    shader.inputs['Metallic'].default_value = 0
    mat.use_backface_culling = False
    return {'albedo': str(image.filepath_raw), 'albedo_linear': list(color),
            'normal': str(normal_tex.image.filepath_raw), 'alpha_scissor': opacity is not None}


def fabric_fringe(out, seed, color, wool=False):
    mat = fringe_material(out, seed, wool=wool)
    shader = mat.node_tree.nodes['Principled BSDF']
    texture = shader.inputs['Base Color'].links[0].from_node
    image = texture.image
    pixels = np.array(image.pixels[:], dtype=np.float32).reshape((image.size[1], image.size[0], 4))
    reference = np.array([.42, .36, .26] if wool else [.15, .16, .14])
    pixels[:, :, :3] *= linear_to_srgb(color)/reference
    image.pixels.foreach_set(pixels.ravel())
    image.save()
    image.pack()
    return mat


def upholstery_fringe(out, seed):
    return fabric_fringe(out, seed, UPHOLSTERY)


def pack_covers(objects, out, size=4096):
    """Pack six RGBA/normal pairs into one 3 by 2 atlas without rotating UVs."""
    if len(objects) != 6:
        raise ValueError('The cover atlas requires exactly six cushions')
    out = Path(out)
    atlases = {'albedo': np.zeros((size, size, 4), dtype=np.float32),
               'normal': np.empty((size, size, 4), dtype=np.float32)}
    atlases['normal'][:] = (.5, .5, 1, 1)
    records = []
    for index, obj in enumerate(objects):
        mat = obj.data.materials[0]
        shader = mat.node_tree.nodes['Principled BSDF']
        images = {'albedo': shader.inputs['Base Color'].links[0].from_node.image,
                  'normal': mat.node_tree.nodes['NORMAL'].image}
        col, row = index % 3, index//3
        x0, x1 = col*size//3, (col+1)*size//3
        y0, y1 = row*size//2, (row+1)*size//2
        pad = 8
        for kind, image in images.items():
            w, h = image.size
            data = np.array(image.pixels[:], dtype=np.float32).reshape(h, w, 4)
            ix = np.minimum((np.arange(x1-x0-2*pad)*w/(x1-x0-2*pad)).astype(int), w-1)
            iy = np.minimum((np.arange(y1-y0-2*pad)*h/(y1-y0-2*pad)).astype(int), h-1)
            tile = data[iy[:, None], ix[None, :]]
            atlases[kind][y0:y1, x0:x1] = np.pad(tile, ((pad, pad), (pad, pad), (0, 0)), mode='edge')
        for loop in obj.data.uv_layers['BakeUV'].data:
            loop.uv = ((x0+pad+loop.uv.x*(x1-x0-2*pad))/size,
                       (y0+pad+loop.uv.y*(y1-y0-2*pad))/size)
        records.append({'part': obj.name, 'tile_px': [x0, y0, x1, y1], 'gutter_px': pad})
    mat = objects[0].data.materials[0].copy()
    mat.name = 'CharcoalUpholstery_DecayAtlas'
    shader = mat.node_tree.nodes['Principled BSDF']
    for kind, data in atlases.items():
        image = image_from_array('SofaCover_'+kind, data, out/('sofa_cover_'+kind+'.png'), kind == 'normal')
        node = (shader.inputs['Base Color'].links[0].from_node if kind == 'albedo'
                else mat.node_tree.nodes['NORMAL'])
        node.image = image
    for obj in objects:
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    return {'size': size, 'parts': records, 'albedo_linear': list(UPHOLSTERY)}
