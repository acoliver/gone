"""First-hit cover/residue IDs in the fixed hero and frontal cameras."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render import aim
from seat_render import diagnostic_material
from sofa_decay_policy import ORDER
from sofa_full_decay import ROOT


def capture(asset, out, label):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(asset.resolve()))
    out.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.render.resolution_x, scene.render.resolution_y = 1600, 1422
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.view_settings.view_transform = 'Raw'
    world = bpy.data.worlds.new('Black first-hit background')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0, 0, 0, 1)
    scene.world = world
    record = {'asset': str(asset), 'parts': {}, 'cameras': {}}
    identifier = 1
    for obj in scene.objects:
        if obj.type != 'MESH':
            continue
        obj.data.calc_loop_triangles()
        attribute = obj.data.color_attributes.new(name='GateFace', type='FLOAT_COLOR', domain='CORNER')
        materials = list(obj.data.materials)
        points = np.array([obj.matrix_world@v.co for v in obj.data.vertices])
        faces, identifiers, kinds = [], [], []
        for face in obj.data.polygons:
            if len(face.vertices) != 3:
                raise ValueError('First-hit mapping requires exported triangles')
            source = materials[face.material_index].name
            kind = 'residue' if source.startswith('Foam') else 'cover'
            selected = obj.name in ORDER
            color = (identifier & 255, (identifier >> 8) & 255, (identifier >> 16) & 255) if selected else (0, 0, 0)
            for index in face.loop_indices:
                attribute.data[index].color = tuple(c/255 for c in color)+(1,)
            if selected:
                faces.append(face.vertices[:])
                identifiers.append(identifier)
                kinds.append(kind)
                identifier += 1
        if faces:
            np.savez_compressed(out/(label+'-'+obj.name+'.npz'), vertices=points,
                                faces=np.array(faces), ids=np.array(identifiers), kinds=np.array(kinds))
            record['parts'][obj.name] = label+'-'+obj.name+'.npz'
        for index, source in enumerate(materials):
            obj.data.materials[index] = diagnostic_material(source, 'cover' if obj.name in ORDER else 'other', False, True)
    data = bpy.data.cameras.new('First hit camera')
    camera = bpy.data.objects.new(data.name, data)
    scene.collection.objects.link(camera)
    data.type = 'ORTHO'
    data.ortho_scale = 2.85
    scene.camera = camera
    for view, eye in [('hero', (1.720729309, -2.457456133, 1.8)), ('front', (0, -3, .80))]:
        camera.location = eye
        aim(camera, (0, 0, .40))
        scene.render.filepath = str(out/(label+'-'+view+'.png'))
        record['cameras'][view] = {'eye_blender_m': list(eye), 'target_blender_m': [0, 0, .4],
                                   'scale': 2.85, 'resolution': [1600, 1422]}
        bpy.ops.render.render(write_still=True)
    (out/(label+'.json')).write_text(json.dumps(record, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    capture(ROOT/'assets/props/quarters/sofa.glb', args.out, 'before')
    capture(args.input, args.out, 'after')
