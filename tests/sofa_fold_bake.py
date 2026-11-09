"""Blender integration regression: filling must not become cloth-fold grime."""
from pathlib import Path
import sys

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/blender/quarters/sofa'))
from fold_masks import bake_folds

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
mesh = bpy.data.meshes.new('JoinedClothAndFoam')
mesh.from_pydata([(-.5, -.5, z) for z in [0, .002]] +
                 [(.5, -.5, z) for z in [0, .002]] +
                 [(.5, .5, z) for z in [0, .002]] +
                 [(-.5, .5, z) for z in [0, .002]], [], [(0, 2, 4, 6), (1, 3, 5, 7)])
obj = bpy.data.objects.new('Cushion', mesh)
bpy.context.collection.objects.link(obj)
uv = mesh.uv_layers.new(name='MaterialAtlas')
for face in mesh.polygons:
    low, high = (.1, .4) if face.index == 0 else (.6, .9)
    for index, coord in zip(face.loop_indices, [(low, .1), (high, .1), (high, .9), (low, .9)]):
        uv.data[index].uv = coord
    face.material_index = face.index
control = bpy.data.images.new('JoinedControl', width=64, height=64, alpha=False)
control.colorspace_settings.name = 'Non-Color'
for name in ['CharcoalUpholstery_Test', 'Foam_Test']:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    output = nodes.new('ShaderNodeOutputMaterial')
    emit = nodes.new('ShaderNodeEmission')
    ao = nodes.new('ShaderNodeAmbientOcclusion')
    ao.only_local = True
    ao.inputs['Distance'].default_value = .12
    ao.samples = 8
    links.new(ao.outputs[0], emit.inputs[0])
    links.new(emit.outputs[0], output.inputs[0])
    target = nodes.new('ShaderNodeTexImage')
    target.image = control
    nodes.active = target
    mesh.materials.append(material)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 8
scene.render.bake.margin = 2
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
bpy.ops.object.bake(type='EMIT')
joined = np.array(control.pixels[:]).reshape(64, 64, 4)[14:48, 10:23, 0].mean()
vertices = [v.co[:] for v in mesh.vertices]
faces = [p.vertices[:] for p in mesh.polygons]
output = ROOT / 'tmp/mat/sofa/fold-test.png'
bake_folds([obj], output, 64)
separated = np.array(bpy.data.images['Sofa_cloth_folds'].pixels[:]).reshape(64, 64, 4)[14:48, 10:23, 0].mean()
assert joined < .6, ('control must see filling occlusion', joined)
assert separated > .99, ('flat cloth must have no fold grime', separated)
assert [v.co[:] for v in mesh.vertices] == vertices
assert [p.vertices[:] for p in mesh.polygons] == faces
assert len(bpy.context.scene.objects) == 1
print('FOLD REGRESSION PASS', dict(joined_ao=float(joined), cloth_only_ao=float(separated), geometry_unchanged=True))
