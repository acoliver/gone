"""Render an actual chest patch in neutral light without altering its material."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_context import setup
from render import aim


def render(asset, out):
    scene, camera, origin, rotation = setup(asset)
    for light in bpy.data.lights:
        light.color = (1, 1, 1)
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.06, .06, .06, 1)
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    scene.render.dither_intensity = 0
    scene.cycles.seed = 9514
    sheet = np.load(asset.parent/'game-sheet.npz')
    positions, patterns, normals, faces = [], [], [], []
    for ids, uv in zip(sheet['faces'], sheet['uv']):
        a, b = uv[1]-uv[0], uv[2]-uv[0]
        if abs(a[0]*b[1]-a[1]*b[0]) < 1e-12:
            continue
        points = [origin+rotation @ Vector(sheet['vertices'][i]) for i in ids]
        n = (points[1]-points[0]).cross(points[2]-points[0]).normalized()
        faces.append(tuple(range(len(positions), len(positions)+3)))
        positions += points
        normals += [n]*3
        patterns += [Vector((*p, 0)) for p in uv]
    tree = BVHTree.FromPolygons(patterns, faces, all_triangles=True)
    uv, _, index, _ = tree.find_nearest(Vector((.14, .65, 0)))
    ids = faces[index]
    target = barycentric_transform(uv, *[patterns[i] for i in ids], *[positions[i] for i in ids])
    normal = barycentric_transform(uv, *[patterns[i] for i in ids], *[normals[i] for i in ids]).normalized()
    camera.location = target+normal*.5
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = .049
    aim(camera, target)
    bpy.context.view_layer.update()
    for dx in [-.024, 0, .024]:
        for dy in [-.024, 0, .024]:
            start = camera.location+camera.matrix_world.to_3x3() @ Vector((dx, dy, 0))
            hit, _, _, _, obj, _ = scene.ray_cast(bpy.context.evaluated_depsgraph_get(), start, -normal)
            if not hit or obj.name != 'TunicBody':
                raise ValueError(f'Chest swatch contains a non-wool surface: {obj.name if hit else "miss"}')
    scene.render.resolution_x = scene.render.resolution_y = 49
    scene.render.filepath = str(out/'aged-chest-neutral.png')
    bpy.ops.render.render(write_still=True)
    (out/'neutral-light.json').write_text(json.dumps(dict(
        crop_flat_pattern_uv=[.14, .65], position_blender_m=list(target), normal=list(normal),
        crop_width_m=.049, resolution=[49, 49], assumed_reference_scale_mm_per_pixel=1.,
        scale_limitation='The generated target has no physical ruler; 1 mm/pixel is an approximate garment-scale convention, not a measured photographic scale.',
        exposure=0, gamma=1, view_transform=scene.view_settings.view_transform, look=scene.view_settings.look,
        light_colour=[1, 1, 1], power_w=75,
        material_override=False, albedo_changed=False), indent=2)+'\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    a.out.mkdir(parents=True, exist_ok=True)
    render(a.input.resolve(), a.out.resolve())
