"""Retain pass-10 review cameras and add a low target-angle studio capture."""
import argparse
import json
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render import aim, render
from sofa_decay_render import diagnostics
from sofa_pass9_render import hero_controls


def target_shot(asset, out):
    scene = bpy.context.scene
    camera = scene.camera
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 2.75
    camera.location = (1.10, -3., 1.35)
    target = (0, 0, .61)
    aim(camera, target)
    scene.render.resolution_x = scene.render.resolution_y = 1024
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.85, .85, .85, 1)
    floor = bpy.data.materials['Studio floor']
    floor.diffuse_color = (.85, .85, .85, 1)
    scene.render.filepath = str(out/'sofa-target-angle.png')
    bpy.ops.render.render(write_still=True)
    record = dict(input=str(asset.resolve()), target='docs/art/quarters/sheets/sofa/aged-target.png',
                  eye_blender_m=list(camera.location), aim_blender_m=list(target), projection='ORTHO',
                  scale=camera.data.ortho_scale, resolution=[1024, 1024],
                  method='low near-front three-quarter camera inferred from fixed target; target has no measured camera metadata')
    (out/'target-camera.json').write_text(json.dumps(record, indent=2)+'\n')


def capture(asset, out):
    render('sofa', out, asset)
    target_shot(asset, out)
    # Restore the neutral studio before the unchanged hero disabled-effect tests.
    scene = bpy.context.scene
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.65, .65, .65, 1)
    bpy.data.materials['Studio floor'].diffuse_color = (.58, .58, .58, 1)
    hero_controls(out)
    diagnostics(asset, out/'diagnostics')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    capture(args.input, args.out)
