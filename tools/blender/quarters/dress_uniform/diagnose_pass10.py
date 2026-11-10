"""Neutral-camera controls for transmitted background and visible fibre deposition."""
import argparse
import json
import math
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from render import aim


def diagnose(out):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(out/'candidate.glb'))
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.render.resolution_x, scene.render.resolution_y = 1600, 1422
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    world = bpy.data.worlds.new('Neutral studio')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.65, .65, .65, 1)
    world.node_tree.nodes['Background'].inputs[1].default_value = .7
    scene.world = world
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.9505))
    ground = bpy.context.object
    ground.name = 'Studio floor'
    mat = bpy.data.materials.new('Studio floor')
    mat.diffuse_color = (.58, .58, .58, 1)
    ground.data.materials.append(mat)
    target = Vector((0, 0, -.44))
    for name, loc, power in [('Front', (-3, -4, 4), 650), ('Right', (3, -2, 2), 500),
                              ('Rear', (1, 3, 3), 650), ('Left', (-3, 2, 1), 450)]:
        data = bpy.data.lights.new(name, 'AREA')
        data.energy, data.size, data.shape = power, 3, 'DISK'
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = loc
        aim(obj, target)
    data = bpy.data.cameras.new('Pass-ten controls')
    camera = bpy.data.objects.new(data.name, data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    data.type, data.ortho_scale = 'ORTHO', 1.30
    camera.location = (3*math.sin(math.radians(35)), -3*math.cos(math.radians(35)), .08)
    aim(camera, target)
    bpy.context.view_layer.update()
    controls = out.parent/'controls'
    controls.mkdir(exist_ok=True)
    def shot(name):
        scene.render.filepath = str(controls/name)
        bpy.ops.render.render(write_still=True)
    shot('hero.png')
    for obj in scene.objects:
        if obj.name.startswith(('FibreDust', 'HeapFibres')):
            obj.hide_render = True
    shot('hero-no-dust.png')
    for obj in scene.objects:
        if obj.name.startswith(('FibreDust', 'HeapFibres')):
            obj.hide_render = False
    close_target = Vector((.235, -.01, -.285))
    camera.location = close_target+Vector((.3, -.9, .22)).normalized()*.5
    data.type, data.lens = 'PERSP', 40
    aim(camera, close_target)
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    record = json.loads((out/'finished.json').read_text())
    hits = []
    for a, b in record['pass10']['bridge_roots']:
        point = (Vector(a)+Vector(b))/2
        ray = (point-camera.location).normalized()
        hit, location, normal, index, obj, matrix = scene.ray_cast(deps, camera.location, ray)
        uv = world_to_camera_view(scene, camera, point)
        hits.append(dict(pixel_xy=[uv.x*1600, (1-uv.y)*1422], first_hit=obj.name if hit else 'world',
                         distance_past_gap_m=float((location-point).length) if hit else None))
    shot('close.png')
    bpy.data.objects['Rear'].hide_render = True
    shot('close-no-rear.png')
    (controls/'lighting.json').write_text(json.dumps(dict(gap_rays=hits,
        protocol='same neutral lights and tunic9 hero/close cameras; no material overrides'), indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    diagnose(args.out.resolve())
