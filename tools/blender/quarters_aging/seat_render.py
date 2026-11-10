"""Render the actual centre-seat export and alpha-aware diagnostic passes."""
import argparse
import json
from pathlib import Path
import shutil
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render import aim, render

PALETTE = {'cover': (1, 0, 0), 'fringe': (0, 1, 0), 'residue': (0, 0, 1),
           'rigid': (1, 1, 1), 'other': (1, 0, 1)}


def diagnostic_material(source, category, normals, face_ids=False):
    mat = source.copy()
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    shader = nodes.get('Principled BSDF')
    alpha = shader.inputs['Alpha'].links[0].from_socket if shader.inputs['Alpha'].is_linked else None
    emission = nodes.new('ShaderNodeEmission')
    if face_ids:
        emission.inputs['Color'].default_value = (0, 0, 0, 1)
        if category == 'cover':
            attribute = nodes.new('ShaderNodeVertexColor')
            attribute.layer_name = 'GateFace'
            links.new(attribute.outputs['Color'], emission.inputs['Color'])
    elif normals:
        normal = (shader.inputs['Normal'].links[0].from_socket if shader.inputs['Normal'].is_linked
                  else nodes.new('ShaderNodeNewGeometry').outputs['Normal'])
        scale = nodes.new('ShaderNodeVectorMath')
        scale.operation = 'MULTIPLY'
        scale.inputs[1].default_value = (.5, .5, .5)
        links.new(normal, scale.inputs[0])
        add = nodes.new('ShaderNodeVectorMath')
        add.operation = 'ADD'
        add.inputs[1].default_value = (.5, .5, .5)
        links.new(scale.outputs['Vector'], add.inputs[0])
        links.new(add.outputs['Vector'], emission.inputs['Color'])
    elif not face_ids:
        emission.inputs['Color'].default_value = (*PALETTE[category], 1)
    output = nodes.get('Material Output')
    if alpha is not None:
        transparent = nodes.new('ShaderNodeBsdfTransparent')
        mix = nodes.new('ShaderNodeMixShader')
        links.new(alpha, mix.inputs[0])
        links.new(transparent.outputs[0], mix.inputs[1])
        links.new(emission.outputs[0], mix.inputs[2])
        links.new(mix.outputs[0], output.inputs['Surface'])
    else:
        links.new(emission.outputs[0], output.inputs['Surface'])
    return mat


def diagnostics(asset, out):
    cameras = {}
    for mode in ['labels', 'normals', 'faces-close', 'faces-hero']:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(asset.resolve()))
        scene = bpy.context.scene
        scene.render.engine = 'BLENDER_EEVEE_NEXT'
        scene.render.resolution_x = 1100
        scene.render.resolution_y = 1000
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = 'PNG'
        scene.render.image_settings.color_mode = 'RGB'
        scene.view_settings.view_transform = 'Raw'
        world = bpy.data.worlds.new('Black diagnostics')
        world.use_nodes = True
        world.node_tree.nodes['Background'].inputs['Color'].default_value = (0, 0, 0, 1)
        scene.world = world
        for obj in scene.objects:
            if obj.type != 'MESH':
                continue
            if mode.startswith('faces') and obj.name == 'SeatCushion_C':
                attribute = obj.data.color_attributes.new(name='GateFace', type='FLOAT_COLOR', domain='CORNER')
                cover = [p for p in obj.data.polygons if obj.data.materials[p.material_index].name.startswith('CharcoalUpholstery')]
                for face in cover:
                    identifier = face.index+1
                    color = (identifier & 255, (identifier >> 8) & 255, (identifier >> 16) & 255)
                    for index in face.loop_indices:
                        attribute.data[index].color = tuple(c/255 for c in color)+(1,)
                np.savez_compressed(out/'seat-face-map.npz', vertices=np.array([obj.matrix_world@v.co for v in obj.data.vertices]),
                                    faces=np.array([p.vertices[:] for p in cover]), ids=np.array([p.index+1 for p in cover]))
            for i, source in enumerate(obj.data.materials):
                if obj.name == 'SeatCushion_C' and source.name.startswith('CharcoalUpholstery'):
                    category = 'cover'
                elif obj.name.startswith('SeatCushion_C') and 'Fringe' in source.name:
                    category = 'fringe'
                elif obj.name == 'SeatCushion_C' and source.name.startswith('Foam'):
                    category = 'residue'
                elif obj.name in ['Frame', 'Feet', 'Rivets']:
                    category = 'rigid'
                else:
                    category = 'other'
                obj.data.materials[i] = diagnostic_material(source, category, mode == 'normals', mode.startswith('faces'))
        data = bpy.data.cameras.new('Seat close camera')
        camera = bpy.data.objects.new(data.name, data)
        scene.collection.objects.link(camera)
        target = Vector((-.10, -.29, .46))
        camera.location = target+Vector((-.18, -.50, .28)).normalized()*.6
        data.lens = 45
        if mode == 'faces-hero':
            target = Vector((0, 0, .40))
            camera.location = (1.720729309, -2.457456133, 1.8)
            data.type = 'ORTHO'
            data.ortho_scale = 2.85
        scene.camera = camera
        aim(camera, target)
        scene.render.filepath = str(out/f'seat-{mode}.png')
        cameras[mode] = {'projection': data.type, 'distance_m': (camera.location-target).length,
                         'lens_mm': data.lens, 'resolution': [1100, 1000],
                         'target_blender_m': list(target), 'eye_blender_m': list(camera.location)}
        bpy.ops.render.render(write_still=True)
    (out/'seat-camera.json').write_text(json.dumps({'input': str(asset.resolve()), 'cameras': cameras, 'palette': PALETTE}, indent=2)+'\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--diagnostics-only', action='store_true')
    a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    a.out.mkdir(parents=True, exist_ok=True)
    if not a.diagnostics_only:
        render('sofa', a.out, a.input)
        shutil.copyfile(a.out/'sofa-after.png', a.out/'seat-hero.png')
        shutil.copyfile(a.out/'sofa-closeup.png', a.out/'seat-closeup.png')
    diagnostics(a.input, a.out)
