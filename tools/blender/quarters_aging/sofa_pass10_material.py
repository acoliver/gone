"""Provisional tan foam with short-range cavity shading, separate from upholstery."""
from pathlib import Path

import bpy
import numpy as np

from common import activate
from fringe_cards import image_from_array
from sofa_decay_material import linear_to_srgb

FOAM_TAN = (.32, .18, .075)


def foam_albedo(ao):
    result = np.ones_like(ao)
    # AO modulates the cavity contribution, rather than replacing the diffuse
    # material with a black silhouette beneath the surviving cover.
    result[:, :, :3] = linear_to_srgb(np.asarray(FOAM_TAN)*(.55+.45*ao[:, :, :3]))
    return result


def local_cavity(dense, low, out):
    """Bake only the residue's own 8 mm cavities, excluding surrounding covers."""
    source_materials = list(dense.data.materials)
    source_indices = [f.material_index for f in dense.data.polygons]
    mat = bpy.data.materials.new('Foam local cavity source')
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    ao = nodes.new('ShaderNodeAmbientOcclusion')
    ao.only_local = True
    ao.inputs['Distance'].default_value = .008
    ao.samples = 16
    emission = nodes.new('ShaderNodeEmission')
    links.new(ao.outputs['Color'], emission.inputs['Color'])
    links.new(emission.outputs[0], nodes['Material Output'].inputs['Surface'])
    dense.data.materials.clear()
    dense.data.materials.append(mat)
    for face in dense.data.polygons:
        face.material_index = 0
    target = low.data.materials[0]
    image = target.node_tree.nodes['AO'].image
    target.node_tree.nodes.active = target.node_tree.nodes['AO']
    scene = bpy.context.scene
    scene.render.bake.use_selected_to_active = True
    activate(low)
    dense.hide_render = False
    dense.hide_set(False)
    dense.select_set(True)
    bpy.context.view_layer.objects.active = low
    bpy.ops.object.bake(type='EMIT')
    image.filepath_raw = str(Path(out)/'local_cavity.png')
    image.save()
    image.pack()
    dense.data.materials.clear()
    for source in source_materials:
        dense.data.materials.append(source)
    for face, index in zip(dense.data.polygons, source_indices):
        face.material_index = index
    dense.hide_render = True
    return image


def tan_residue(dense, low, out):
    image = local_cavity(dense, low, out)
    mat = low.data.materials[0]
    shader = mat.node_tree.nodes['Principled BSDF']
    old = shader.inputs['Base Color'].links[0].from_node
    ao = np.array(image.pixels[:], dtype=np.float32).reshape(image.size[1], image.size[0], 4)
    albedo = image_from_array(mat.name+'_Tan', foam_albedo(ao), Path(out)/'foam_tan_albedo.png')
    old.image = albedo
    shader.inputs['Roughness'].default_value = 1.
    return {'albedo': str(albedo.filepath_raw), 'albedo_linear': list(FOAM_TAN),
            'normal': str(mat.node_tree.nodes['NORMAL'].image.filepath_raw),
            'cavity': str(image.filepath_raw), 'cavity_distance_m': .008,
            'cavity_only_local': True, 'ambient_fraction': .55, 'alpha_scissor': False}
