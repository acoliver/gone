"""Render scratch tunic candidates, including alpha-aware acceptance diagnostics."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from render import aim, render
from seat_render import diagnostic_material


def lip_seeds(sheet, scene, camera):
    vertices, faces, uv = sheet['vertices'], sheet['faces'], sheet['uv']
    edges = {}
    for face, pattern in zip(faces, uv):
        for i, j in [(0, 1), (1, 2), (2, 0)]:
            edges.setdefault(tuple(sorted((int(face[i]), int(face[j])))), []).append(pattern[[i, j]])
    groups = {'shoulder': {'front': [], 'back': []}, 'armhole': {'body': [], 'sleeve': []}}
    for edge, patterns in edges.items():
        if len(patterns) != 1:
            continue
        pattern = patterns[0]
        points = vertices[list(edge)]
        if points[:, 0].min() <= .075:
            continue
        u, v = pattern[:, 0], pattern[:, 1]
        group = None
        if u.max() < 1. and np.max(np.abs(v-.94)) < .001:
            group = groups['shoulder']['front' if u.mean() < .48 else 'back']
        elif u.min() > 1.09 and u.max() < 1.56 and v.max() < .001:
            group = groups['armhole']['sleeve']
        elif (u.max() < 1. and v.min() > .66 and v.max() < .96 and
              min(np.max(np.abs(u-.46)), np.max(np.abs(u-.97))) < .003):
            group = groups['armhole']['body']
        if group is not None:
            pixels = [world_to_camera_view(scene, camera, Vector(p)) for p in points]
            group.append([[(1-p.y)*1422, p.x*1600] for p in pixels])
    result = {}
    for tear, sides in groups.items():
        result[tear] = {}
        for side, segments in sides.items():
            target = Vector((.23, 0., -.25))
            a = world_to_camera_view(scene, camera, target)
            b = world_to_camera_view(scene, camera, target+Vector((.008, 0, 0)))
            radius = max(3., float(np.hypot((b.x-a.x)*1600, (b.y-a.y)*1422)))
            result[tear][side] = dict(segments_yx=segments, radius_px=radius)
    return result


def diagnostics(asset, out):
    record = {}
    sheet = np.load(asset.parent / 'game-sheet.npz')
    for mode in ['labels', 'normals', 'faces', 'faces-30', 'faces-120', 'faces-210',
                 'faces-300', 'hero-labels', 'hero-before']:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        path = ROOT / 'assets/props/quarters/dress_uniform.glb' if mode == 'hero-before' else asset
        bpy.ops.import_scene.gltf(filepath=str(path.resolve()))
        scene = bpy.context.scene
        scene.render.engine = 'BLENDER_EEVEE_NEXT'
        scene.render.resolution_x = 1600
        scene.render.resolution_y = 1422
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = 'PNG'
        scene.render.image_settings.color_mode = 'RGB'
        scene.view_settings.view_transform = 'Raw'
        scene.render.dither_intensity = 0.
        world = bpy.data.worlds.new('Black diagnostics')
        world.use_nodes = True
        world.node_tree.nodes['Background'].inputs[0].default_value = (0, 0, 0, 1)
        world.node_tree.nodes['Background'].inputs[1].default_value = 0
        scene.world = world
        for obj in scene.objects:
            if obj.type != 'MESH':
                continue
            if mode.startswith('faces') and obj.name == 'TunicBody':
                attribute = obj.data.color_attributes.new(name='GateFace', type='FLOAT_COLOR', domain='CORNER')
                for face in obj.data.polygons:
                    if obj.data.materials[face.material_index].name.startswith('WoolCutEdge'):
                        continue
                    identifier = face.index+1
                    color = (identifier & 255, (identifier >> 8) & 255, (identifier >> 16) & 255)
                    for i in face.loop_indices:
                        attribute.data[i].color = tuple(c/255 for c in color)+(1,)
                cover = [p for p in obj.data.polygons if not obj.data.materials[p.material_index].name.startswith('WoolCutEdge')]
                np.savez_compressed(out / 'visible-faces.npz',
                                    vertices=np.array([obj.matrix_world @ v.co for v in obj.data.vertices]),
                                    faces=np.array([p.vertices[:] for p in cover]), ids=np.array([p.index+1 for p in cover]))
            for i, source in enumerate(obj.data.materials):
                category = ('cover' if obj.name == 'TunicBody' else
                            'fringe' if 'Fringe' in source.name else
                            'residue' if obj.name == 'Hanger' else 'other')
                obj.data.materials[i] = diagnostic_material(source, category, mode == 'normals', mode.startswith('faces'))
        data = bpy.data.cameras.new('Tunic acceptance camera')
        camera = bpy.data.objects.new(data.name, data)
        scene.collection.objects.link(camera)
        scene.camera = camera
        if mode.startswith('hero') or mode.startswith('faces-'):
            angle = np.radians(float(mode.split('-')[1])) if mode.startswith('faces-') else np.radians(35.)
            camera.location = (3*np.sin(angle), -3*np.cos(angle), .08)
            target = Vector((0, 0, -.44))
            data.type = 'ORTHO'
            data.ortho_scale = 1.30
        else:
            target = Vector((.235, -.01, -.285))
            camera.location = target+Vector((.3, -.9, .22)).normalized()*.5
            data.type = 'PERSP'
            data.lens = 40
        aim(camera, target)
        bpy.context.view_layer.update()
        scene.render.filepath = str(out / f'tunic-{mode}.png')
        if mode == 'hero-labels':
            body = bpy.data.objects['TunicBody']
            bm = __import__('bmesh').new()
            bm.from_mesh(body.data)
            vertices = {v for e in bm.edges if e.is_boundary for v in e.verts
                        if v.co.x > .075 and v.co.z > -.35}
            # Rim-only solidify may close boundary loops; its rim material
            # identifies the same authored lip positions on the baked export.
            if not vertices:
                mats = body.data.materials
                vertices = {v for f in bm.faces if mats[f.material_index].name.startswith('WoolCutEdge')
                            for v in f.verts if v.co.x > .075 and v.co.z > -.35}
            points = [world_to_camera_view(scene, camera, body.matrix_world @ v.co) for v in vertices]
            record['split_hull_pixels'] = [[p.x*1600, (1-p.y)*1422] for p in points]
            bm.free()
        record[mode] = dict(distance_m=float((camera.location-target).length), lens_mm=data.lens,
                            position_blender_m=list(camera.location), look_at_blender_m=list(target),
                            projection=data.type, resolution=[1600, 1422])
        if mode in ['labels', 'hero-labels']:
            record[mode]['tear_lips'] = lip_seeds(sheet, scene, camera)
        bpy.ops.render.render(write_still=True)
    (out / 'tunic-cameras.json').write_text(json.dumps(record, indent=2)+'\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--out', type=Path, default=ROOT / 'tmp/age/tunic8')
    a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    a.out.mkdir(parents=True, exist_ok=True)
    render('dress_uniform', a.out.resolve(), a.input.resolve())
    diagnostics(a.input.resolve(), a.out.resolve())
