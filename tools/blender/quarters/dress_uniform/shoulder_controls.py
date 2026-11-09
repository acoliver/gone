"""Isolate exported shoulder fringe and cut rims in the fixed locker camera."""
import argparse
import json
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_context


def control_setup(asset, mode, setup):
    scene, camera, origin, rotation = setup(asset)
    scene.render.dither_intensity = 0
    for obj in scene.objects:
        if obj.type != 'MESH':
            continue
        card = any('Fringe' in mat.name for mat in obj.data.materials)
        if mode == 'cards-off' and card:
            obj.hide_render = True
        for mat in obj.data.materials:
            shader = mat.node_tree.nodes.get('Principled BSDF') if mat.use_nodes else None
            if mode == 'rim-off' and mat.name.startswith('WoolCutEdge'):
                for link in list(shader.inputs['Alpha'].links):
                    mat.node_tree.links.remove(link)
                shader.inputs['Alpha'].default_value = 0
            if mode == 'hard-alpha' and mat.name.startswith(('WoolFringeShoulderSoft', 'WoolCutEdgeShoulderSoft')):
                alpha = shader.inputs['Alpha'].links[0].from_socket
                cutoff = mat.node_tree.nodes.new('ShaderNodeMath')
                cutoff.operation = 'ROUND'
                mat.node_tree.links.new(alpha, cutoff.inputs[0])
                mat.node_tree.links.new(cutoff.outputs[0], shader.inputs['Alpha'])
    return scene, camera, origin, rotation


def controls(asset, out, modes):
    setup = render_context.setup
    try:
        for mode in modes:
            render_context.setup = lambda asset, mode=mode: control_setup(asset, mode, setup)
            render_context.render_context(asset, out, mode, views=['closeup'])
    finally:
        render_context.setup = setup


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--modes', nargs='+', default=['full', 'cards-off', 'rim-off'],
                   choices=['full', 'cards-off', 'rim-off', 'hard-alpha'])
    a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    a.out.mkdir(parents=True, exist_ok=True)
    controls(a.input.resolve(), a.out.resolve(), a.modes)
