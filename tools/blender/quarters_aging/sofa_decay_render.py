"""Render the ordered sofa and per-part alpha-aware acceptance diagnostics."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render import aim, render
from seat_render import diagnostic_material
from sofa_decay_policy import ORDER


def diagnostics(asset, out, names=(*ORDER, 'Throw')):
    out.mkdir(parents=True, exist_ok=True)
    record = {'input': str(asset.resolve()), 'parts': {}}
    for name in names:
        part_dir = out/name
        part_dir.mkdir(parents=True, exist_ok=True)
        cameras = {}
        for mode in ['labels', 'normals', 'faces-close', 'faces-hero']:
            bpy.ops.wm.read_factory_settings(use_empty=True)
            bpy.ops.import_scene.gltf(filepath=str(asset.resolve()))
            scene = bpy.context.scene
            scene.render.engine = 'BLENDER_EEVEE_NEXT'
            scene.render.resolution_x = 1280
            scene.render.resolution_y = 1164
            scene.render.resolution_percentage = 100
            scene.render.image_settings.file_format = 'PNG'
            scene.render.image_settings.color_mode = 'RGB'
            scene.view_settings.view_transform = 'Raw'
            world = bpy.data.worlds.new('Black diagnostics')
            world.use_nodes = True
            world.node_tree.nodes['Background'].inputs['Color'].default_value = (0, 0, 0, 1)
            scene.world = world
            prefix = 'OatmealWool' if name == 'Throw' else 'CharcoalUpholstery'
            for obj in scene.objects:
                if obj.type != 'MESH':
                    continue
                # glTF import shares the cover-atlas material across cushions.
                # Make each object's slots local before assigning category colours.
                for index, material in enumerate(list(obj.data.materials)):
                    obj.data.materials[index] = material.copy()
                if mode.startswith('faces') and obj.name == name:
                    attribute = obj.data.color_attributes.new(name='GateFace', type='FLOAT_COLOR', domain='CORNER')
                    cover = [p for p in obj.data.polygons if obj.data.materials[p.material_index].name.startswith(prefix)]
                    for face in cover:
                        identifier = face.index+1
                        color = (identifier & 255, (identifier >> 8) & 255, (identifier >> 16) & 255)
                        for index in face.loop_indices:
                            attribute.data[index].color = tuple(c/255 for c in color)+(1,)
                    np.savez_compressed(part_dir/'faces.npz', vertices=np.array([obj.matrix_world@v.co for v in obj.data.vertices]),
                                        faces=np.array([p.vertices[:] for p in cover]), ids=np.array([p.index+1 for p in cover]))
                for index, source in enumerate(list(obj.data.materials)):
                    if obj.name == name and source.name.startswith(prefix):
                        category = 'cover'
                    elif obj.name == name+'_Fringe':
                        category = 'fringe'
                    elif obj.name == name and source.name.startswith('Foam'):
                        category = 'residue'
                    elif obj.name in {'Frame', 'Feet', 'Rivets'}:
                        category = 'rigid'
                    else:
                        category = 'other'
                    obj.data.materials[index] = diagnostic_material(source, category, mode == 'normals', mode.startswith('faces'))
            part = bpy.data.objects[name]
            if name.startswith('Seat'):
                target = Vector((part.matrix_world.translation.x-.10, -.29, .45))
            elif name.startswith('Back'):
                target = Vector((part.matrix_world.translation.x-.05, .18, .57))
            else:
                # A rejected drop can leave the fitted arm location entirely.
                # Keep the diagnostic distance while measuring the real mesh.
                target = sum((part.matrix_world@v.co for v in part.data.vertices), Vector())/len(part.data.vertices)
            data = bpy.data.cameras.new('Acceptance camera')
            camera = bpy.data.objects.new(data.name, data)
            scene.collection.objects.link(camera)
            camera.location = target+Vector((-.18, -.50, .28)).normalized()*.6
            data.lens = 45
            if mode == 'faces-hero':
                target = Vector((0, 0, .40))
                camera.location = (1.720729309, -2.457456133, 1.8)
                data.type = 'ORTHO'
                data.ortho_scale = 2.85
            scene.camera = camera
            aim(camera, target)
            scene.render.filepath = str(part_dir/(mode+'.png'))
            cameras[mode] = {'projection': data.type, 'distance_m': (camera.location-target).length,
                             'eye_blender_m': list(camera.location), 'target_blender_m': list(target),
                             'lens_mm': data.lens, 'resolution': [1280, 1164],
                             'nominal_target_pixel_m': .6*data.sensor_width/data.lens/1280 if data.type == 'PERSP' else None}
            bpy.ops.render.render(write_still=True)
        record['parts'][name] = cameras
        (out/'cameras.json').write_text(json.dumps(record, indent=2)+'\n')
    return record


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--diagnostics-only', action='store_true')
    a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    if not a.diagnostics_only:
        render('sofa', a.out, a.input)
    diagnostics(a.input, a.out/'diagnostics')
