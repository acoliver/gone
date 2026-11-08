"""Fixed-camera, neutral-light comparisons of the actual exported GLBs."""
import argparse
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def render(prop, out):
    out.mkdir(parents=True, exist_ok=True)
    sofa = prop == 'sofa'
    target = (0, 0, .40 if sofa else -.44)
    scale = 2.85 if sofa else 1.15
    floor = 0 if sofa else -.95
    for state in ['before', 'after']:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        asset = ROOT / f'assets/props/quarters/{prop}{"_aged" if state == "after" else ""}.glb'
        bpy.ops.import_scene.gltf(filepath=str(asset))
        scene = bpy.context.scene
        scene.render.engine = 'BLENDER_EEVEE_NEXT'
        scene.render.image_settings.file_format = 'PNG'
        scene.render.resolution_percentage = 100
        scene.render.resolution_x = 900
        scene.render.resolution_y = 800
        scene.view_settings.view_transform = 'AgX'
        for mat in bpy.data.materials:
            if not mat.use_nodes:
                continue
            shader = mat.node_tree.nodes.get('Principled BSDF')
            if shader is None:
                continue
            colors = {'Foam': (.23, .11, .045, 1), 'FibreDust': (.36, .30, .23, 1),
                      'NaturalFabric': (.40, .36, .28, 1) if sofa else (.15, .21, .29, 1),
                      'PaintedSteel': (.36, .38, .39, 1), 'BareSteel': (.5, .52, .54, 1),
                      'Brass': (.57, .41, .18, 1)}
            shader.inputs['Base Color'].default_value = colors.get(mat.name, (.4, .4, .4, 1))
            shader.inputs['Metallic'].default_value = 0
            shader.inputs['Roughness'].default_value = .85
        bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, floor - .0005))
        ground = bpy.context.object
        mat = bpy.data.materials.new('Studio floor')
        mat.diffuse_color = (.58, .58, .58, 1)
        ground.data.materials.append(mat)
        world = bpy.data.worlds.new('Neutral studio')
        scene.world = world
        world.use_nodes = True
        world.node_tree.nodes['Background'].inputs[0].default_value = (.65, .65, .65, 1)
        world.node_tree.nodes['Background'].inputs[1].default_value = .7
        for name, loc, power in [('Front', (-3, -4, 4), 650), ('Right', (3, -2, 2), 500), ('Rear', (1, 3, 3), 650), ('Left', (-3, 2, 1), 450)]:
            data = bpy.data.lights.new(name, 'AREA')
            data.energy = power
            data.shape = 'DISK'
            data.size = 3
            obj = bpy.data.objects.new(name, data)
            scene.collection.objects.link(obj)
            obj.location = loc
            aim(obj, target)
        data = bpy.data.cameras.new('FixedCamera')
        camera = bpy.data.objects.new('FixedCamera', data)
        scene.collection.objects.link(camera)
        data.type = 'ORTHO'
        data.ortho_scale = scale
        scene.camera = camera
        def shot(name, angle, height):
            a = math.radians(angle)
            camera.location = (3 * math.sin(a), -3 * math.cos(a), height)
            aim(camera, target)
            scene.render.filepath = str(out / name)
            bpy.ops.render.render(write_still=True)
        shot(f'{prop}-{state}.png', 35, 1.8 if sofa else .08)
        if state == 'after':
            for angle in [30, 120, 210, 300]:
                shot(f'{prop}-turn-{angle}.png', angle, 1.5 if sofa else .08)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prop', choices=['sofa', 'dress_uniform'], required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    render(args.prop, args.out)
