"""Explicit PBR base texture for glTF, including AO, navy albedo and opacity."""
from pathlib import Path

import numpy as np

from fringe_cards import image_from_array


def wool_material(obj, out, opacity=None, color=(.025, .043, .08)):
    mat = obj.data.materials[0]
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    ao = nodes['AO'].image
    ao_width, ao_height = ao.size
    values = np.empty(ao_width*ao_height*4, np.float32)
    ao.pixels.foreach_get(values)
    values = values.reshape(ao_height, ao_width, 4)
    width, height = opacity.size if opacity is not None else ao.size
    if (width, height) != (ao_width, ao_height):
        rows = np.minimum((np.arange(height)*ao_height/height).astype(int), ao_height-1)
        columns = np.minimum((np.arange(width)*ao_width/width).astype(int), ao_width-1)
        values = values[rows[:, None], columns[None, :]]
    linear = np.clip(values[:, :, :3]*np.array(color), 0, 1)
    rgba = np.ones_like(values)
    rgba[:, :, :3] = np.where(linear <= .0031308, linear*12.92,
                              1.055*linear**(1/2.4)-.055)
    if opacity is not None:
        alpha = np.empty(width*height*4, np.float32)
        opacity.pixels.foreach_get(alpha)
        rgba[:, :, 3] = alpha.reshape(height, width, 4)[:, :, 0]
    image = image_from_array(obj.name+'_WoolBase', rgba, Path(out)/(obj.name.lower()+'_base.png'))
    texture = nodes.new('ShaderNodeTexImage')
    texture.name = 'Wool base with AO and opacity'
    texture.image = image
    uv = nodes.new('ShaderNodeUVMap')
    uv.uv_map = 'BakeUV'
    links.new(uv.outputs['UV'], texture.inputs['Vector'])
    shader = nodes['Principled BSDF']
    links.new(texture.outputs['Color'], shader.inputs['Base Color'])
    if opacity is not None:
        cutoff = nodes.new('ShaderNodeMath')
        cutoff.operation = 'ROUND'
        links.new(texture.outputs['Alpha'], cutoff.inputs[0])
        links.new(cutoff.outputs[0], shader.inputs['Alpha'])
    return {'path': image.filepath_raw, 'albedo_linear': list(color),
            'ao_multiplied': True, 'opacity_packed': opacity is not None}
