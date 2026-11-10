"""Bake local fold/upward masks and exportable dry pigments into unique UVs."""
import json
from pathlib import Path
import sys

import bpy
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build import ASSETS
from common import activate, export, save
from fringe_cards import image_from_array
from refinement_fields import cloth_color
from refine import TEXTURES


def bake_masks(obj, size):
    activate(obj)
    targets = []
    for slot, original in enumerate(tuple(obj.data.materials)):
        if original.name not in {'Foam', 'CottonTicking', 'BrittleWool', 'BrittleCotton'} and not original.name.startswith('Pillow_'):
            continue
        mat = original
        if obj.name.startswith('Pillow_'):
            mat = original.copy()
            mat.name = obj.name + '_AgedCotton'
            obj.data.materials[slot] = mat
        role = 'foam' if original.name == 'Foam' else ('wool' if obj.name == 'Quilt' else 'cotton')
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        nodes.clear()
        output = nodes.new('ShaderNodeOutputMaterial')
        emit = nodes.new('ShaderNodeEmission')
        pack = nodes.new('ShaderNodeCombineColor')
        ao = nodes.new('ShaderNodeAmbientOcclusion')
        ao.only_local = True
        ao.samples = 16
        ao.inputs['Distance'].default_value = .045
        geometry = nodes.new('ShaderNodeNewGeometry')
        normal = nodes.new('ShaderNodeSeparateXYZ')
        noise = nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = 110 if role == 'foam' else 32
        noise.inputs['Detail'].default_value = 2
        links.new(geometry.outputs['Position'], noise.inputs['Vector'])
        links.new(geometry.outputs['Normal'], normal.inputs[0])
        links.new(ao.outputs['AO'], pack.inputs['Red'])
        links.new(normal.outputs['Z'], pack.inputs['Green'])
        links.new(noise.outputs['Fac'], pack.inputs['Blue'])
        links.new(pack.outputs[0], emit.inputs['Color'])
        links.new(emit.outputs[0], output.inputs['Surface'])
        image = bpy.data.images.new(obj.name + '_' + role + '_Masks', width=size, height=size, alpha=False)
        image.colorspace_settings.name = 'Non-Color'
        target = nodes.new('ShaderNodeTexImage')
        target.image = image
        nodes.active = target
        targets.append((mat, image, role))
    bpy.ops.object.bake(type='EMIT')
    return targets


def finish(mat, mask, role, obj_name):
    mask.filepath_raw = str(TEXTURES / (obj_name.lower() + '_' + role + '_masks.png'))
    mask.file_format = 'PNG'
    mask.save()
    mask.pack()
    size = mask.size[0]
    pixels = np.array(mask.pixels[:], dtype=np.float32).reshape(size, size, 4)
    ao, up, variation = [np.clip(pixels[:, :, i], 0, 1) for i in range(3)]
    if role == 'foam':
        pores = np.clip((.50 - variation) * 8, 0, 1)
        color = np.array([.105, .044, .012]) * (.55 + .90 * variation[:, :, None])
        color *= (.55 + .45 * ao[:, :, None]) * (1 - .55 * pores[:, :, None])
        dust = up * ao * .18
        color = color * (1 - dust[:, :, None]) + np.array([.21, .145, .075]) * dust[:, :, None]
    else:
        color = cloth_color(ao, up, variation, wool=role == 'wool')
    rgba = np.ones((size, size, 4), dtype=np.float32)
    rgba[:, :, :3] = color
    image = image_from_array(obj_name + '_' + role + '_Aged', rgba,
                             TEXTURES / (obj_name.lower() + '_' + role + '_albedo.png'))
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    shader = nodes.new('ShaderNodeBsdfPrincipled')
    output = nodes.new('ShaderNodeOutputMaterial')
    links.new(shader.outputs[0], output.inputs['Surface'])
    texture = nodes.new('ShaderNodeTexImage')
    texture.image = image
    links.new(texture.outputs['Color'], shader.inputs['Base Color'])
    shader.inputs['Roughness'].default_value = .98
    if role == 'wool':
        uv = nodes.new('ShaderNodeUVMap')
        uv.uv_map = 'WeaveUV'
        tex = nodes.new('ShaderNodeTexImage')
        tex.image = bpy.data.images.load(str(ASSETS / 'bed_soft_textures/wool_weave_normal.png'), check_existing=False)
        tex.image.colorspace_settings.name = 'Non-Color'
        tex.image.pack()
        normal = nodes.new('ShaderNodeNormalMap')
        normal.uv_map = 'WeaveUV'
        normal.inputs['Strength'].default_value = .5
        links.new(uv.outputs['UV'], tex.inputs['Vector'])
        links.new(tex.outputs['Color'], normal.inputs['Color'])
        links.new(normal.outputs['Normal'], shader.inputs['Normal'])
    elif role == 'foam':
        # Bake the porous relief to tangent normals; procedural nodes alone
        # would disappear when the glTF importer builds the game material.
        noise = nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = 185
        noise.inputs['Detail'].default_value = 3
        geometry = nodes.new('ShaderNodeNewGeometry')
        links.new(geometry.outputs['Position'], noise.inputs['Vector'])
        bump = nodes.new('ShaderNodeBump')
        bump.inputs['Distance'].default_value = .0022
        bump.inputs['Strength'].default_value = .8
        links.new(noise.outputs['Fac'], bump.inputs['Height'])
        links.new(bump.outputs['Normal'], shader.inputs['Normal'])
    valid = ao > .001
    return {'mask_channels': {'R': '45 mm local fold occlusion', 'G': 'world upward normal',
                             'B': '110/m porous variation' if role == 'foam' else '32/m pigment variation'},
            'linear_color_min': color[valid].min(axis=0).tolist(),
            'linear_color_max': color[valid].max(axis=0).tolist()}


def bake_foam_normal(obj):
    activate(obj)
    targets = []
    for mat in obj.data.materials:
        image = bpy.data.images.new(mat.name + '_NormalBake', width=1024, height=1024, alpha=False)
        image.colorspace_settings.name = 'Non-Color'
        node = mat.node_tree.nodes.new('ShaderNodeTexImage')
        node.image = image
        mat.node_tree.nodes.active = node
        targets.append((mat, image))
    bpy.ops.object.bake(type='NORMAL')
    for mat, image in targets:
        if mat.name != 'Foam':
            continue
        image.filepath_raw = str(TEXTURES / 'foam_crust_normal.png')
        image.file_format = 'PNG'
        image.save()
        image.pack()
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        shader = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
        texture = nodes.new('ShaderNodeTexImage')
        texture.image = image
        normal = nodes.new('ShaderNodeNormalMap')
        links.new(texture.outputs['Color'], normal.inputs['Color'])
        links.new(normal.outputs['Normal'], shader.inputs['Normal'])


def main():
    source = HERE / 'bed-soft-aged-finished.blend'
    bpy.ops.wm.open_mainfile(filepath=str(source))
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 8
    scene.render.bake.margin = 8
    scene.render.bake.use_clear = True
    scene.render.bake.use_selected_to_active = False
    record = json.loads((HERE / 'refinement.json').read_text())
    record['materials'] = {}
    fringe_shader = bpy.data.materials['WoolFringe'].node_tree.nodes.get('Principled BSDF')
    fringe = fringe_shader.inputs['Base Color'].links[0].from_node.image
    pixels = np.array(fringe.pixels[:], dtype=np.float32).reshape(fringe.size[1], fringe.size[0], 4)
    pixels[:, :, :3] = np.array([.145, .103, .052])
    fringe.pixels.foreach_set(pixels.ravel())
    fringe.save()
    fringe.pack()
    for name in ('Mattress', 'Quilt', 'Pillow_L', 'Pillow_R'):
        obj = bpy.data.objects[name]
        targets = bake_masks(obj, 2048 if name == 'Quilt' else 1024)
        for mat, mask, role in targets:
            record['materials'][name + '/' + role] = finish(mat, mask, role, name)
        if name == 'Mattress':
            bake_foam_normal(obj)
        print('FINISHED MATERIALS', name, flush=True)
    (HERE / 'refinement.json').write_text(json.dumps(record, indent=2) + '\n')
    save(source, record)
    export(ASSETS / 'bed_soft_aged.glb')


if __name__ == '__main__':
    main()
