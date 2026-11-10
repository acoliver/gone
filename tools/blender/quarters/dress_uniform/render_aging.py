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


def lift_grain_lips(sheet, opacity):
    positions, faces, uv = sheet['vertices'], sheet['faces'], sheet['uv']
    groups = {}
    scale = np.asarray(opacity['pattern_scale_m'])
    low, high = uv.min(1), uv.max(1)
    def lift(point):
        candidates = np.flatnonzero(np.all((low <= point+1e-8) & (high >= point-1e-8), axis=1))
        for i in candidates:
            a, b, c = uv[i]
            matrix = np.array([b-a, c-a]).T
            if abs(np.linalg.det(matrix)) < 1e-12:
                continue
            v, w = np.linalg.solve(matrix, point-a)
            if min(v, w, 1-v-w) >= -1e-6:
                return np.array([1-v-w, v, w]) @ positions[faces[i]]
        return None
    for index, path in enumerate(opacity['grain_paths_m']):
        path = np.asarray(path)
        groups[f'grain-crack-{index+1}'] = {}
        for sign, side in [(-1, 'left'), (1, 'right')]:
            segments = []
            for a, b in zip(path, path[1:]):
                tangent = (b-a)/np.linalg.norm(b-a)
                normal = np.array([-tangent[1], tangent[0]])
                samples = [lift((p+normal*sign*.00065)/scale)
                           for p in np.linspace(a, b, max(2, int(np.linalg.norm(b-a)/.001)+1))]
                segments += [[p, q] for p, q in zip(samples, samples[1:]) if p is not None and q is not None]
            groups[f'grain-crack-{index+1}'][side] = segments
    return groups


def lip_seeds(sheet, scene, camera, opacity):
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
        if (u.max() < 1. and np.max(np.abs(v-.94)) < .001 and
                np.all(sheet['released'][list(edge)] >= .5)):
            group = groups['shoulder']['front' if u.mean() < .48 else 'back']
        elif u.min() > 1.09 and u.max() < 1.56 and v.max() < .001:
            group = groups['armhole']['sleeve']
        elif (u.max() < 1. and v.min() > .66 and v.max() < .96 and
              min(np.max(np.abs(u-.46)), np.max(np.abs(u-.97))) < .003):
            group = groups['armhole']['body']
        if group is not None:
            pixels = [world_to_camera_view(scene, camera, Vector(p)) for p in points]
            group.append([[(1-p.y)*1422, p.x*1600] for p in pixels])
    grain = lift_grain_lips(sheet, opacity)
    for tear, sides in grain.items():
        groups[tear] = {}
        for side, segments in sides.items():
            groups[tear][side] = []
            for points in segments:
                pixels = [world_to_camera_view(scene, camera, Vector(p)) for p in points]
                groups[tear][side].append([[(1-p.y)*1422, p.x*1600] for p in pixels])
    result = {}
    for tear, sides in groups.items():
        result[tear] = {}
        for side, segments in sides.items():
            target = Vector((.23, 0., -.25))
            a = world_to_camera_view(scene, camera, target)
            band = .002 if tear.startswith('grain-crack') else .008
            b = world_to_camera_view(scene, camera, target+Vector((band, 0, 0)))
            radius = max(2., float(np.hypot((b.x-a.x)*1600, (b.y-a.y)*1422)))
            result[tear][side] = dict(segments_yx=segments, radius_px=radius)
    return result


def diagnostics(asset, out, modes=None, scale=1, control=None):
    record = {}
    sheet = np.load(asset.parent / 'game-sheet.npz')
    opacity = json.loads((asset.parent / 'finished.json').read_text())['opacity']
    for mode in modes or ['labels', 'normals', 'faces', 'faces-30', 'faces-120', 'faces-210',
                          'faces-300', 'hero-labels', 'hero-before']:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        path = ROOT / 'assets/props/quarters/dress_uniform.glb' if mode == 'hero-before' else asset
        bpy.ops.import_scene.gltf(filepath=str(path.resolve()))
        scene = bpy.context.scene
        scene.render.engine = 'BLENDER_EEVEE_NEXT'
        scene.render.resolution_x = 1600*scale
        scene.render.resolution_y = 1422*scale
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
                mat = diagnostic_material(source, category, mode == 'normals', mode.startswith('faces'))
                if control == 'opaque' and obj.name == 'TunicBody':
                    emission = next(n for n in mat.node_tree.nodes if n.type == 'EMISSION')
                    mat.node_tree.links.new(emission.outputs[0], mat.node_tree.nodes['Material Output'].inputs['Surface'])
                obj.data.materials[i] = mat
            if control == 'no-fringe' and any('Fringe' in m.name for m in obj.data.materials):
                obj.hide_render = True
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
                            projection=data.type, resolution=[1600*scale, 1422*scale])
        if mode in ['labels', 'hero-labels']:
            seeds = lip_seeds(sheet, scene, camera, opacity)
            for sides in seeds.values():
                for data in sides.values():
                    data['segments_yx'] = (np.asarray(data['segments_yx'])*scale).tolist()
                    data['radius_px'] *= scale
            record[mode]['tear_lips'] = seeds
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
