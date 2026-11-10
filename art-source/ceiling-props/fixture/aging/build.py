"""Bake world fields from the unchanged, packed round-6 fixture topology."""
from pathlib import Path
import json
import math
import bmesh
import bpy
import numpy as np

R = Path(__file__).resolve().parent
SOURCE = R.parent / 'round6'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE / 'fixture.blend'))
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 1
scene.render.threads_mode = 'FIXED'
scene.render.threads = 4
scene.render.bake.use_selected_to_active = False
scene.render.bake.margin = 12
source = bpy.data.objects['SOURCE_720_generated_painted']
source.hide_render = True
source.hide_set(True)
for prefix, name in [('body', 'Seed720_CleanedGeneratedBeam'), ('grille', 'GeneratedUnderside_ArmouredGrille'), ('hardware', 'RaisedRails_Rivets_GravityFasteners')]:
    obj = bpy.data.objects[name]
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    edges = []
    for edge in bm.edges:
        if len(edge.link_faces) != 2 or edge.calc_face_angle(0) > math.radians(30):
            a, b = [obj.matrix_world @ vertex.co for vertex in edge.verts]
            for t in np.linspace(0, 1, max(2, int((b - a).length / .0007) + 1)):
                edges.append(tuple(a.lerp(b, float(t))))
    bm.free()
    np.save(R / (prefix + '_sharp_edges.npy'), np.array(edges, dtype=np.float32))
    bpy.ops.object.select_all(action='DESELECT')
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    mat = bpy.data.materials.new(prefix + '_FieldBake')
    mat.use_nodes = True
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    for face in obj.data.polygons:
        face.material_index = 0
    nt = mat.node_tree
    nt.nodes.clear()
    output = nt.nodes.new('ShaderNodeOutputMaterial')
    emission = nt.nodes.new('ShaderNodeEmission')
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    vec = nt.nodes.new('ShaderNodeVectorMath')
    nt.links.new(emission.outputs[0], output.inputs['Surface'])
    nt.links.new(vec.outputs[0], emission.inputs['Color'])
    image = bpy.data.images.new(prefix + '_field', width=1024, height=1024, float_buffer=True, alpha=False)
    image.colorspace_settings.name = 'Non-Color'
    target = nt.nodes.new('ShaderNodeTexImage')
    target.image = image
    nt.nodes.active = target
    for kind in ['position', 'normals']:
        if kind == 'position':
            vec.operation = 'ADD'
            vec.inputs[1].default_value = (.55, .11, .1)
            nt.links.new(geo.outputs['Position'], vec.inputs[0])
        else:
            vec.operation = 'MULTIPLY_ADD'
            vec.inputs[1].default_value = (.5, .5, .5)
            vec.inputs[2].default_value = (.5, .5, .5)
            nt.links.new(geo.outputs['Normal'], vec.inputs[0])
        bpy.ops.object.bake(type='EMIT')
        values = np.empty(1024 * 1024 * 4, dtype=np.float32)
        image.pixels.foreach_get(values)
        np.save(R / (prefix + '_' + kind + '.npy'), values.reshape(1024, 1024, 4))
(R / 'build-stats.json').write_text((SOURCE / 'build-stats.json').read_text())
bpy.ops.wm.save_as_mainfile(filepath=str(R / 'working.blend'))
print('BUILD_COMPLETE unchanged round-6 geometry and UVs')
