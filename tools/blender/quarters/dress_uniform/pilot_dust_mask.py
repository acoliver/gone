"""Capture visible upward upper-cloth pixels for matched lit dust controls."""
import argparse
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_context import setup
from render import aim


def capture(asset, context, output):
    scene, camera, origin, rotation = setup(asset)
    record = json.loads(context.read_text())['closeup']
    camera.location = record['position_blender_m']
    camera.data.type = record['projection']
    camera.data.lens = record['lens_mm']
    aim(camera, Vector(record['target_blender_m']))
    scene.view_settings.view_transform = 'Raw'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    scene.render.dither_intensity = 0
    scene.cycles.use_denoising = False
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = 0
    for obj in scene.objects:
        if obj.type != 'MESH':
            continue
        cloth = obj.name in ['TunicBody', 'ShoulderBoard_L', 'ShoulderBoard_R', 'Collar']
        for i, source in enumerate(list(obj.data.materials)):
            mat = source.copy()
            nodes, links = mat.node_tree.nodes, mat.node_tree.links
            emission = nodes.new('ShaderNodeEmission')
            emission.inputs[0].default_value = (0, 0, 0, 1)
            if cloth:
                geometry = nodes.new('ShaderNodeNewGeometry')
                normal = nodes.new('ShaderNodeSeparateXYZ')
                links.new(geometry.outputs['Normal'], normal.inputs[0])
                up = nodes.new('ShaderNodeMath')
                up.operation = 'GREATER_THAN'
                up.inputs[1].default_value = .35
                links.new(normal.outputs['Z'], up.inputs[0])
                position = nodes.new('ShaderNodeSeparateXYZ')
                links.new(geometry.outputs['Position'], position.inputs[0])
                upper = nodes.new('ShaderNodeMath')
                upper.operation = 'GREATER_THAN'
                upper.inputs[1].default_value = origin.z-.34
                links.new(position.outputs['Z'], upper.inputs[0])
                mask = nodes.new('ShaderNodeMath')
                mask.operation = 'MULTIPLY'
                links.new(up.outputs[0], mask.inputs[0])
                links.new(upper.outputs[0], mask.inputs[1])
                colour = nodes.new('ShaderNodeCombineColor')
                links.new(mask.outputs[0], colour.inputs[0])
                links.new(upper.outputs[0], colour.inputs[1])
                links.new(colour.outputs[0], emission.inputs[0])
            alpha = nodes.get('Principled BSDF').inputs['Alpha']
            material_output = nodes.get('Material Output')
            if alpha.is_linked:
                transparent = nodes.new('ShaderNodeBsdfTransparent')
                mix = nodes.new('ShaderNodeMixShader')
                links.new(alpha.links[0].from_socket, mix.inputs[0])
                links.new(transparent.outputs[0], mix.inputs[1])
                links.new(emission.outputs[0], mix.inputs[2])
                links.new(mix.outputs[0], material_output.inputs['Surface'])
            else:
                links.new(emission.outputs[0], material_output.inputs['Surface'])
            obj.data.materials[i] = mat
    scene.render.filepath = str(output)
    return scene


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--context', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    scene = capture(a.input.resolve(), a.context.resolve(), a.output.resolve())
    scene.render.filepath = str(a.output.resolve())
    bpy.ops.render.render(write_still=True)
