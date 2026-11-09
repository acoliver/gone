"""Collapsed cut-edge UVs cannot use the broad sheet's tangent-space normals."""
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import load_source
from aging_cards import rim_modifier

body = load_source()
source = body.data.materials[0]
shader = source.node_tree.nodes['Principled BSDF']
normal = source.node_tree.nodes.new('ShaderNodeNormalMap')
source.node_tree.links.new(normal.outputs['Normal'], shader.inputs['Normal'])
texture = source.node_tree.nodes.new('ShaderNodeTexImage')
texture.image = bpy.data.images.new('Alpha control', width=4, height=4, alpha=True)
source.node_tree.links.new(texture.outputs['Alpha'], shader.inputs['Alpha'])
rim_modifier(body, [])
rim = body.data.materials[-1]
assert not rim.node_tree.nodes['Principled BSDF'].inputs['Normal'].is_linked
assert rim.node_tree.nodes['Principled BSDF'].inputs['Alpha'].is_linked
assert shader.inputs['Normal'].is_linked
assert not rim.use_backface_culling
print('PASS: rim uses geometric normals and retains alpha; the wool sheet keeps its normal map')
