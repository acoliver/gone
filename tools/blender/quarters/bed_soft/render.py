"""Render each exported state on the unchanged bed at two fixed viewing angles."""
from pathlib import Path
import sys

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = ROOT / 'docs/art/quarters/sheets/bed_soft'


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def render(state):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(ROOT / 'assets/props/quarters/bed.glb'))
    bpy.ops.import_scene.gltf(filepath=str(ROOT / f'assets/props/quarters/bed_soft{"_aged" if state == "aged" else ""}.glb'))
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    world = bpy.data.worlds.new('Neutral review room')
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.65, .65, .65, 1)
    world.node_tree.nodes['Background'].inputs[1].default_value = .5
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.0005))
    floor = bpy.context.object
    mat = bpy.data.materials.new('ReviewFloor')
    mat.diffuse_color = (.32, .32, .30, 1)
    floor.data.materials.append(mat)
    for name, position, power in (('Key', (-3, -4, 5), 500), ('Fill', (3, -1, 3), 350), ('Back', (0, 3, 4), 400)):
        data = bpy.data.lights.new(name, 'AREA')
        data.energy = power
        data.size = 4
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = position
        aim(obj, (0, 0, .5))
    data = bpy.data.cameras.new('ReviewCamera')
    camera = bpy.data.objects.new('ReviewCamera', data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    # Bed centre at room (4, 0, 4.9), facing the entrance. In the bed's native
    # frame the doorway camera (4, 1.65, .15) is (0, -4.75, 1.65).
    for angle, position in (('doorway', (0, -4.75, 1.65)), ('three_quarter', (-3.1, -3.7, 2.45))):
        camera.location = position
        aim(camera, (0, 0, .54))
        data.type = 'PERSP' if angle == 'doorway' else 'ORTHO'
        data.lens = 55
        data.ortho_scale = 3.15
        scene.render.filepath = str(OUT / f'{state}-{angle}.png')
        bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    states = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else ['remembered', 'aged']
    for state in states:
        render(state)
