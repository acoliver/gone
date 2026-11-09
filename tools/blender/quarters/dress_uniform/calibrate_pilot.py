"""Solve display-sampled target colours under the fixed locker/AgX setup."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_context import setup
from render import aim


def decode(value):
    value = np.asarray(value, dtype=float)
    return np.where(value <= .04045, value/12.92, ((value+.055)/1.055)**2.4)


def calibrate(source, out):
    out.mkdir(parents=True, exist_ok=True)
    palette = json.loads(source.read_text())
    scene, camera, origin, rotation = setup(Path('assets/props/quarters/dress_uniform.glb').resolve())
    for obj in scene.objects:
        if obj.type == 'MESH' and not obj.data.materials[0].name.startswith('Context only'):
            obj.hide_render = True
    scene.cycles.samples = 24
    scene.cycles.seed = 9513
    scene.render.resolution_x = scene.render.resolution_y = 128
    scene.render.dither_intensity = 0
    bpy.ops.mesh.primitive_plane_add(size=.08)
    plane = bpy.context.object
    plane.name = 'Calibration flat swatch'
    mat = bpy.data.materials.new('Calibration albedo')
    mat.use_nodes = True
    plane.data.materials.append(mat)
    shader = mat.node_tree.nodes['Principled BSDF']
    palette['calibration'] = dict(method='Rendered fixed-point inversion in linearised display RGB; all iterations saved',
                                  lighting='render_context.setup, unchanged 75 W strip and dim world',
                                  view_transform='AgX', look=scene.view_settings.look,
                                  sample='Central 32 by 32 pixels of a flat 80 mm swatch, 128-square render',
                                  units='albedo linear RGB; display and target sRGB bytes', roles={})
    for role, colour in palette['colours'].items():
        horizontal = role != 'brass_brown'
        local = Vector((.16, -.095, -.16 if horizontal else -.28))
        target = origin+rotation @ local
        if role == 'fibre_dust':
            target = Vector((.03, -.10, .14))
        plane.location = target
        normal = Vector((0, 0, 1)) if horizontal else rotation @ Vector((0, -1, 0))
        plane.rotation_euler = normal.to_track_quat('Z', 'Y').to_euler()
        camera.location = target+Vector((0, -.12, .18) if horizontal else (.025, -.18, .025))
        camera.data.type = 'ORTHO'
        camera.data.ortho_scale = .035
        aim(camera, target)
        shader.inputs['Metallic'].default_value = .55 if role == 'brass_brown' else 0
        shader.inputs['Roughness'].default_value = .82 if role == 'brass_brown' else .97
        shader.inputs['Specular IOR Level'].default_value = .5 if role == 'brass_brown' else .12
        albedo = np.array(colour['linear'])
        desired = np.array(colour['srgb_bytes'], dtype=float)
        steps = []
        for iteration in range(12):
            shader.inputs['Base Color'].default_value = (*albedo, 1)
            path = out/f'{role}-{iteration:02}.png'
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            image = bpy.data.images.load(str(path), check_existing=False)
            image.colorspace_settings.name = 'Non-Color'
            pixels = np.empty(128*128*4, np.float32)
            image.pixels.foreach_get(pixels)
            displayed = np.median(pixels.reshape(128, 128, 4)[48:80, 48:80, :3], axis=(0, 1))*255
            bpy.data.images.remove(image)
            steps.append(dict(iteration=iteration, albedo_linear=albedo.tolist(), displayed_srgb_bytes=displayed.tolist(),
                              target_srgb_bytes=desired.tolist(), maximum_error_bytes=float(abs(displayed-desired).max()), image=str(path)))
            if abs(displayed-desired).max() <= 1:
                break
            albedo = np.clip(albedo*(decode(desired/255)/decode(np.maximum(displayed, 1)/255))**.8, .00001, 1)
        if steps[-1]['maximum_error_bytes'] > 1:
            raise ValueError(f'{role} swatch failed to converge: {steps[-1]}')
        colour['sample_display_linear'] = colour['linear']
        colour['linear'] = steps[-1]['albedo_linear']
        palette['calibration']['roles'][role] = dict(position_blender_m=list(target), normal=list(normal), steps=steps)
        (out/'target-colours.json').write_text(json.dumps(palette, indent=2)+'\n')
        print('CALIBRATED', role, colour['linear'], displayed, flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    calibrate(a.source.resolve(), a.out.resolve())
