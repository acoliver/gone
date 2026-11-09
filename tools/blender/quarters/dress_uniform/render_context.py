"""Review the tunic against a dark open locker, without editing either asset."""
import argparse
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from render import aim


def steel():
    mat = bpy.data.materials.new('Context only grey-green painted steel')
    mat.use_nodes = True
    shader = mat.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = (.065, .080, .070, 1)
    shader.inputs['Metallic'].default_value = .15
    shader.inputs['Roughness'].default_value = .76
    return mat


def setup(asset):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(ROOT/'assets/props/quarters/storage_locker_module.glb'))
    paint = steel()
    hinge = Vector((-.26, -.258, 0))
    door_transform = Matrix.Translation(hinge) @ Matrix.Rotation(math.radians(112), 4, 'Z') @ Matrix.Translation(-hinge)
    for obj in list(bpy.context.scene.objects):
        if obj.type != 'MESH':
            continue
        obj.data.materials.clear()
        obj.data.materials.append(paint)
        if obj.name.startswith(('Door', 'Handle')):
            obj.matrix_world = door_transform @ obj.matrix_world
    locker = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(asset))
    rotation = Matrix.Rotation(math.radians(55), 4, 'Z')
    origin = Vector((-.015, -.17, 1.65))
    for obj in set(bpy.context.scene.objects)-locker:
        debris = obj.name.startswith(('FibreDust', 'HeapFibres', 'FallenHem'))
        shift = Vector((-.015, -.10, 1.055)) if debris else origin
        obj.matrix_world = Matrix.Translation(shift) @ rotation @ obj.matrix_world
    # A peg at the hanger crown makes the hanging support explicit.
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=.004, depth=.08,
                                       location=(origin.x, origin.y+.035, origin.z-.007),
                                       rotation=(math.pi/2, 0, 0))
    bpy.context.object.data.materials.append(paint)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 48
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 1400
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.world = bpy.data.worlds.new('Dim room')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.06, .06, .06, 1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = .12
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    light = bpy.data.lights.new('Ceiling strip above and in front', 'AREA')
    light.energy = 75
    light.color = (1., .97, .90)
    light.shape = 'RECTANGLE'
    light.size = 1.2
    light.size_y = .18
    lamp = bpy.data.objects.new(light.name, light)
    scene.collection.objects.link(lamp)
    lamp.location = (.1, -1., 2.65)
    aim(lamp, Vector((0, 0, 1.1)))
    camera = bpy.data.objects.new('Context camera', bpy.data.cameras.new('Context camera'))
    scene.collection.objects.link(camera)
    scene.camera = camera
    return scene, camera, origin, rotation


def render_context(asset, out, state):
    scene, camera, origin, rotation = setup(asset)
    record = {}
    for view in ['hero', 'closeup', 'heap']:
        if view == 'hero':
            target = Vector((0, -.02, 1.10))
            camera.location = (.82, -2.9, 1.7)
            camera.data.type = 'ORTHO'
            camera.data.ortho_scale = 2.62
        elif view == 'closeup':
            target = origin+rotation @ Vector((.235, -.01, -.285))
            # A face-normal approach to the diagonally hung garment crosses
            # the right locker wall. Approach through the open doorway.
            direction = Vector((.16, -.96, .22)).normalized()
            camera.location = target+direction*.5
            camera.data.type = 'PERSP'
            camera.data.lens = 40
        else:
            target = Vector((-.015, -.10, .125))
            camera.location = (.35, -.85, .43)
            camera.data.type = 'PERSP'
            camera.data.lens = 50
        aim(camera, target)
        scene.render.filepath = str(out/f'{state}-{view}.png')
        bpy.ops.render.render(write_still=True)
        record[view] = dict(position_blender_m=list(camera.location), target_blender_m=list(target),
                            distance_m=(camera.location-target).length, lens_mm=camera.data.lens,
                            projection=camera.data.type)
    record['setup'] = dict(locker='assets/props/quarters/storage_locker_module.glb',
                          interior_albedo_linear=[.065, .080, .070], door_open_degrees=112,
                          hook_height_m=1.65, inner_floor_height_m=.105,
                          garment_yaw_degrees=55, garment_origin_blender_m=list(origin),
                          debris_translation_blender_m=[-.015, -.10, 1.055],
                          placement='Garment raised to a plausible 1.65 m hook; debris separately placed on the 0.105 m locker floor. Scene floor drop 1.545 m; authored parameter 0.95 m unchanged. Full-size sleeves turn diagonally, with one sleeve extending through the open doorway.',
                          ceiling_strip=dict(power_w=75, color=[1., .97, .90], position=[.1, -1., 2.65]),
                          rim_light=False)
    (out/f'{state}-context.json').write_text(json.dumps(record, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--state', default='after')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    args.out.mkdir(parents=True, exist_ok=True)
    render_context(args.input.resolve(), args.out.resolve(), args.state)
