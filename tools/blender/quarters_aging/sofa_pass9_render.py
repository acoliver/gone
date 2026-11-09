"""Pass-8 cameras plus lit disabled-effect controls and hero visibility IDs."""
import argparse
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render import aim, render
from seat_render import diagnostic_material
from sofa_decay_render import diagnostics


def hero_controls(out):
    scene = bpy.context.scene
    camera = scene.camera
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 2.85
    camera.location = (1.720729309, -2.457456133, 1.8)
    aim(camera, (0, 0, .4))
    scene.render.resolution_x, scene.render.resolution_y = 1600, 1422
    groups = {'fringe': [o for o in scene.objects if o.name.endswith('_Fringe')],
              'crumbs': [bpy.data.objects['FoamDebris']]}
    for label, objects in groups.items():
        for obj in objects:
            obj.hide_render = True
        scene.render.filepath = str(out/('hero-without-'+label+'.png'))
        bpy.ops.render.render(write_still=True)
        for obj in objects:
            obj.hide_render = False
    bpy.data.materials['Studio floor'].use_nodes = True
    for obj in scene.objects:
        if obj.type != 'MESH':
            continue
        category = 'fringe' if obj in groups['fringe'] else 'residue' if obj in groups['crumbs'] else 'other'
        sources = list(obj.data.materials)
        for index, source in enumerate(sources):
            obj.data.materials[index] = diagnostic_material(source, category, False, category == 'other')
        if obj in groups['crumbs']:
            floor_index = len(obj.data.materials)
            obj.data.materials.append(diagnostic_material(sources[0], 'other', False, True))
            front = diagnostic_material(sources[0], 'residue', False)
            front.node_tree.nodes['Emission'].inputs['Color'].default_value = (0, 1, 1, 1)
            front_index = len(obj.data.materials)
            obj.data.materials.append(front)
            for face in obj.data.polygons:
                centre = obj.matrix_world@face.center
                if centre.z < .25:
                    face.material_index = floor_index
                elif centre.y < -.24:
                    face.material_index = front_index
    scene.view_settings.view_transform = 'Raw'
    scene.render.filepath = str(out/'hero-visibility.png')
    bpy.ops.render.render(write_still=True)


def capture(asset, out):
    render('sofa', out, asset)
    hero_controls(out)
    diagnostics(asset, out/'diagnostics')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    capture(args.input, args.out)
