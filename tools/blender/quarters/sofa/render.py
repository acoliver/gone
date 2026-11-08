"""Neutral studio captures with fixed cameras and fill on every side."""
import math
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[4]


def aim(obj, point):
    obj.rotation_euler = (Vector(point) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def render(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(Path(__file__).with_name('sofa-working.blend')))
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.film_transparent = False
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get('Background')
    background.inputs['Color'].default_value = (.65, .65, .65, 1)
    background.inputs['Strength'].default_value = .6
    for name, loc, power, size in [
        ('Main', (-3, -4, 4), 700, 3.5),
        ('Front fill', (3, -2, 2), 500, 3),
        ('Rear fill', (1, 3, 3), 650, 3),
        ('Left fill', (-3, 2, 2), 450, 3),
    ]:
        light = bpy.data.lights.new(name, 'AREA')
        light.energy = power
        light.shape = 'DISK'
        light.size = size
        obj = bpy.data.objects.new(name, light)
        scene.collection.objects.link(obj)
        obj.location = loc
        aim(obj, (0, 0, .43))
    data = bpy.data.cameras.new('StudioCamera')
    camera = bpy.data.objects.new('StudioCamera', data)
    scene.collection.objects.link(camera)
    data.type = 'ORTHO'
    scene.camera = camera

    def shot(name, location, target, scale, resolution):
        camera.location = location
        aim(camera, target)
        data.ortho_scale = scale
        scene.render.resolution_x, scene.render.resolution_y = resolution
        scene.render.filepath = str(out / name)
        bpy.ops.render.render(write_still=True)

    shot('fit-hero.png', (3.1, -3.5, 2.2), (0, 0, .43), 3.15, (1000, 800))
    shot('cushion-close.png', (1.2, -2.4, 1.8), (0, -.10, .53), 1.65, (1100, 850))
    shot('fit-detail.png', (2.25, -2.5, 1.15), (.99, -.15, .52), 1.13, (800, 800))
    for angle in (30, 120, 210, 300):
        r = math.radians(angle)
        shot(f'turn-{angle}.png', (3.2*math.sin(r), -3.2*math.cos(r), 1.65),
             (0, 0, .42), 3.15, (700, 700))
