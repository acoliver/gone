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


def render(prop, out, aged_path=None):
    out.mkdir(parents=True, exist_ok=True)
    sofa = prop == 'sofa'
    target = (0, 0, .40 if sofa else -.44)
    scale = 2.85 if sofa else 1.30
    floor = 0 if sofa else -.95
    for state in ['before', 'after']:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        asset = ROOT / f'assets/props/quarters/{prop}{"_aged" if state == "after" else ""}.glb'
        if state == 'after' and aged_path is not None:
            asset = aged_path
        bpy.ops.import_scene.gltf(filepath=str(asset))
        scene = bpy.context.scene
        scene.render.engine = 'BLENDER_EEVEE_NEXT'
        scene.render.image_settings.file_format = 'PNG'
        scene.render.resolution_percentage = 100
        scene.render.resolution_x = 1600
        scene.render.resolution_y = 1422
        scene.view_settings.view_transform = 'AgX'
        for mat in bpy.data.materials:
            if not mat.use_nodes:
                continue
            shader = mat.node_tree.nodes.get('Principled BSDF')
            if shader is None:
                continue
            if any(node.type == 'TEX_IMAGE' for node in mat.node_tree.nodes):
                continue
            colors = {'Foam': (.16, .065, .022, 1), 'FibreDust': (.27, .24, .19, 1),
                      'CharcoalUpholstery': (.055, .060, .066, 1), 'CoverInside': (.04, .045, .05, 1),
                      'CoverSplitSection': (.07, .065, .06, 1),
                      'OatmealWool': (.56, .48, .35, 1), 'ThrowInside': (.45, .38, .27, 1),
                      'ThrowFraySection': (.50, .43, .32, 1),
                      'TunicInside': (.019, .032, .060, 1), 'TunicFraySection': (.04, .055, .085, 1),
                      'NaturalFabric': (.40, .36, .28, 1) if sofa else (.025, .043, .080, 1),
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
            if sofa:
                close_target = Vector((-.10, -.29, .46))
                direction = Vector((-.18, -.50, .28)).normalized()
                camera.location = close_target + direction * .6
                aim(camera, close_target)
                data.type = 'PERSP'
                data.lens = 45
                scene.render.resolution_x = 1100
                scene.render.resolution_y = 1000
                scene.render.filepath = str(out / 'sofa-closeup.png')
                bpy.ops.render.render(write_still=True)
            else:
                close_target = Vector((.235, -.01, -.285))
                camera.location = close_target + Vector((.3, -.9, .22)).normalized() * .5
                aim(camera, close_target)
                data.type = 'PERSP'
                data.lens = 40
                scene.render.filepath = str(out / 'tunic-closeup.png')
                bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prop', choices=['sofa', 'dress_uniform'], required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--aged-input', type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    render(args.prop, args.out, args.aged_input)
