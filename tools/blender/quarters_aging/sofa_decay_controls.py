"""Blender integration controls for albedo export and keyed-cloth freezing."""
import json
from pathlib import Path
import struct
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cloth_stage import configure
from common import export
from fabric_mesh import material, new_object
from fringe_cards import image_from_array
from sofa_decay_material import exportable_material
from sofa_decay_policy import UPHOLSTERY
from sofa_full_decay import freeze_simulation

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT/'tmp/age/pass6/controls'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
obj = new_object('Control', [(0, 0, .2), (.1, 0, .2), (.1, .1, .2), (0, .1, .2)], [(0, 1, 2, 3)], material('ControlMaterial', UPHOLSTERY))
for i, point in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]):
    obj.data.uv_layers.active.data[i].uv = point
obj.data.uv_layers.active.name = 'BakeUV'
mat = obj.data.materials[0]
for kind, pixel in [('AO', (1, 1, 1, 1)), ('NORMAL', (.5, .5, 1, 1))]:
    data = np.empty((16, 16, 4), np.float32)
    data[:] = pixel
    node = mat.node_tree.nodes.new('ShaderNodeTexImage')
    node.name = kind
    node.image = image_from_array(kind, data, OUT/(kind.lower()+'.png'), True)
alpha = image_from_array('Alpha', np.ones((16, 16, 4), np.float32), OUT/'alpha.png', True)
exportable_material(mat, UPHOLSTERY, OUT, alpha)
export(OUT/'material.glb')
raw = (OUT/'material.glb').read_bytes()
length = struct.unpack_from('<I', raw, 12)[0]
doc = json.loads(raw[20:20+length])
assert doc['materials'][0]['alphaMode'] == 'MASK'
assert 'baseColorTexture' in doc['materials'][0]['pbrMetallicRoughness']
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(OUT/'material.glb'))
obj = bpy.data.objects['Control']
shader = obj.data.materials[0].node_tree.nodes['Principled BSDF']
texture = shader.inputs['Base Color'].links[0].from_node
pixels = np.array(texture.image.pixels[:]).reshape(-1, 4)
# Compare shader output with a constant reference, so colour-space errors in
# encoded bytes cannot pass a check of raw image buffers alone.
nodes, links = obj.data.materials[0].node_tree.nodes, obj.data.materials[0].node_tree.links
emission = nodes.new('ShaderNodeEmission')
links.new(texture.outputs['Color'], emission.inputs['Color'])
links.new(emission.outputs[0], nodes['Material Output'].inputs['Surface'])
reference = obj.copy()
reference.data = obj.data.copy()
bpy.context.collection.objects.link(reference)
reference.location.x += .15
reference.data.materials.clear()
refmat = bpy.data.materials.new('Reference')
refmat.use_nodes = True
refemission = refmat.node_tree.nodes.new('ShaderNodeEmission')
refemission.inputs['Color'].default_value = (*UPHOLSTERY, 1)
refmat.node_tree.links.new(refemission.outputs[0], refmat.node_tree.nodes['Material Output'].inputs['Surface'])
reference.data.materials.append(refmat)
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x, scene.render.resolution_y = 128, 64
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = 'Raw'
camera_data = bpy.data.cameras.new('ControlCamera')
camera = bpy.data.objects.new('ControlCamera', camera_data)
scene.collection.objects.link(camera)
camera.location = (.125, .05, 1)
camera_data.type = 'ORTHO'
camera_data.ortho_scale = .32
scene.camera = camera
scene.render.filepath = str(OUT/'material-roundtrip.png')
bpy.ops.render.render(write_still=True)
rendered = bpy.data.images.load(str(OUT/'material-roundtrip.png'))
render_pixels = np.array(rendered.pixels[:]).reshape((64, 128, 4))
actual_color = render_pixels[24:40, 24:44, :3].mean((0, 1))
reference_color = render_pixels[24:40, 84:104, :3].mean((0, 1))
assert np.max(np.abs(actual_color-reference_color)) <= 1/255, (actual_color, reference_color)
bpy.data.objects.remove(reference, do_unlink=True)
obj.shape_key_add(name='Basis')
rest = obj.shape_key_add(name='Rest')
config = dict(quality=4, frames=8, stiffness=150, bending=.9, mass=.1)
mod = configure(obj, config, 4, rest_shape=rest)
result = freeze_simulation(obj, mod, 8)
assert not obj.modifiers and not obj.data.shape_keys
assert obj.data.vertices[0].co.z < .2
assert result['frames'] == 8
(OUT/'controls.json').write_text(json.dumps({'pass': True,
    'roundtrip_texture_srgb': pixels[:, :3].mean(0).tolist(),
    'rendered_texture_sample': actual_color.tolist(), 'rendered_reference_sample': reference_color.tolist(),
    'maximum_rendered_difference': float(np.max(np.abs(actual_color-reference_color))),
    'expected_albedo_linear': UPHOLSTERY, 'keyed_cloth_frozen': True}, indent=2)+'\n')
print('SOFA DECAY CONTROLS PASS', flush=True)
