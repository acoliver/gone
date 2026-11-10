"""Fixed-camera material controls for the tunic's exported fringe cards."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from render import aim


def setup(asset):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(asset))
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.render.resolution_x, scene.render.resolution_y = 1600, 1422
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    world = bpy.data.worlds.new('Neutral studio')
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.65, .65, .65, 1)
    world.node_tree.nodes['Background'].inputs[1].default_value = .7
    target = Vector((.235, -.01, -.285))
    for name, loc, power in [('Front', (-3, -4, 4), 650), ('Right', (3, -2, 2), 500),
                             ('Rear', (1, 3, 3), 650), ('Left', (-3, 2, 1), 450)]:
        data = bpy.data.lights.new(name, 'AREA')
        data.energy, data.size, data.shape = power, 3, 'DISK'
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = loc
        aim(obj, (0, 0, -.44))
    data = bpy.data.cameras.new('Tunic8 close camera')
    camera = bpy.data.objects.new(data.name, data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.location = target+Vector((.3, -.9, .22)).normalized()*.5
    data.type, data.lens = 'PERSP', 40
    aim(camera, target)
    return scene


def controls(asset, out):
    out.mkdir(parents=True, exist_ok=True)
    report = {}
    for mode in ['cards-original', 'cards-no-normal', 'cards-linear-color',
                 'full-no-cards', 'full-no-rim', 'full-original']:
        scene = setup(asset)
        for obj in scene.objects:
            if obj.type != 'MESH':
                continue
            card = any('Fringe' in mat.name for mat in obj.data.materials)
            obj.hide_render = not card if mode.startswith('cards-') else card if mode == 'full-no-cards' else False
            for mat in obj.data.materials:
                shader = mat.node_tree.nodes.get('Principled BSDF') if mat.use_nodes else None
                if card and shader:
                    report[mat.name] = dict(double_sided=not mat.use_backface_culling,
                                           alpha_linked=bool(shader.inputs['Alpha'].links),
                                           normal_linked=bool(shader.inputs['Normal'].links))
                    if mode in ['cards-no-normal', 'cards-linear-color']:
                        for link in list(shader.inputs['Normal'].links):
                            mat.node_tree.links.remove(link)
                    if mode == 'cards-linear-color':
                        for link in list(shader.inputs['Base Color'].links):
                            mat.node_tree.links.remove(link)
                        shader.inputs['Base Color'].default_value = (.033, .054, .095, 1)
                if mode == 'full-no-rim' and mat.name.startswith('WoolCutEdge'):
                    for link in list(shader.inputs['Alpha'].links):
                        mat.node_tree.links.remove(link)
                    shader.inputs['Alpha'].default_value = 0
        scene.render.filepath = str(out/f'{mode}.png')
        bpy.ops.render.render(write_still=True)
    (out/'materials.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    controls(a.input.resolve(), a.out.resolve())
