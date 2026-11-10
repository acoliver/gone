"""Retain pass-10 review cameras and add a low target-angle studio capture."""
import argparse
import json
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render import aim, render
from sofa_decay_render import diagnostics
from sofa_pass9_render import hero_controls
from seat_render import diagnostic_material
from mathutils import Vector


def crease_labels(asset, out):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(asset.resolve()))
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.render.resolution_x, scene.render.resolution_y = 1280, 1164
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.dither_intensity = 0.
    scene.view_settings.view_transform = 'Raw'
    world = bpy.data.worlds.new('Crease diagnostics')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0, 0, 0, 1)
    scene.world = world
    for obj in scene.objects:
        if obj.type != 'MESH':
            continue
        for index, source in enumerate(list(obj.data.materials)):
            source = source.copy()
            category = 'other'
            if obj.name.startswith('Throw'):
                if source.name.startswith('OatmealWool'):
                    category = 'cover'
                elif 'Fringe' in source.name:
                    category = 'fringe'
            if obj.name in {'Frame', 'Feet', 'Rivets'}:
                category = 'rigid'
            obj.data.materials[index] = diagnostic_material(source, category, False)
    data = bpy.data.cameras.new('Arm crease camera')
    camera = bpy.data.objects.new(data.name, data)
    scene.collection.objects.link(camera)
    target = Vector((1.085, .035, .747))
    camera.location = target+Vector((.48, -.32, .17)).normalized()*.6
    data.lens = 45
    scene.camera = camera
    aim(camera, target)
    scene.render.filepath = str(out/'diagnostics/Throw/crease-labels.png')
    bpy.ops.render.render(write_still=True)
    path = out/'diagnostics/cameras.json'
    record = json.loads(path.read_text())
    record['parts']['Throw']['crease-labels'] = dict(projection='PERSP', distance_m=.6, eye_blender_m=list(camera.location),
        target_blender_m=list(target), lens_mm=data.lens, resolution=[1280, 1164], nominal_target_pixel_m=.6*data.sensor_width/data.lens/1280)
    path.write_text(json.dumps(record, indent=2) + chr(10))


def target_shot(asset, out):
    scene = bpy.context.scene
    camera = scene.camera
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 2.80
    camera.location = (3.1, -3.5, 2.2)
    target = (0, 0, .43)
    aim(camera, target)
    scene.render.resolution_x = scene.render.resolution_y = 1024
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.85, .85, .85, 1)
    floor = bpy.data.materials['Studio floor']
    floor.diffuse_color = (.85, .85, .85, 1)
    scene.render.filepath = str(out/'sofa-target-angle.png')
    bpy.ops.render.render(write_still=True)
    record = dict(input=str(asset.resolve()), target='docs/art/quarters/sheets/sofa/aged-target.png',
                  eye_blender_m=list(camera.location), aim_blender_m=list(target), projection='ORTHO',
                  scale=camera.data.ortho_scale, resolution=[1024, 1024],
                  method='camera orientation from the fitted hero used to generate the target; square 2.80 m framing; generated target has no measured camera metadata')
    (out/'target-camera.json').write_text(json.dumps(record, indent=2)+'\n')


def capture(asset, out):
    render('sofa', out, asset, preserve_materials=True)
    target_shot(asset, out)
    # Restore the neutral studio before the unchanged hero disabled-effect tests.
    scene = bpy.context.scene
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.65, .65, .65, 1)
    bpy.data.materials['Studio floor'].diffuse_color = (.58, .58, .58, 1)
    hero_controls(out)
    diagnostics(asset, out/'diagnostics')
    crease_labels(asset, out)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    capture(args.input, args.out)
