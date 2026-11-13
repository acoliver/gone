"""Bake high-surface AO, signed curvature and topology-owned material IDs to frozen low UVs."""
import json
import shutil
import sys
from pathlib import Path
import bpy
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FIT, OUT, SIZE

bpy.ops.wm.open_mainfile(filepath=str(FIT / 'medal-fitted.blend'))
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 16
scene.render.threads_mode = 'FIXED'
scene.render.threads = 8
scene.render.bake.use_selected_to_active = True
scene.render.bake.margin = 8
scene.render.bake.use_clear = False
highs = {p: bpy.data.objects[p + '_High'] for p in ['Body','Loop','Bar']}
lows = {p: bpy.data.objects[p + '_Low'] for p in highs}
for obj in bpy.data.objects:
    obj.hide_render = obj not in list(highs.values()) + list(lows.values())
for obj in highs.values():
    obj.hide_render = False
    mesh = obj.data
    mesh.calc_loop_triangles()
    v = np.array([p.co[:] for p in mesh.vertices], dtype=float)
    tri = np.array([t.vertices[:] for t in mesh.loop_triangles])
    normals = np.zeros_like(v)
    cross = np.cross(v[tri[:,1]] - v[tri[:,0]], v[tri[:,2]] - v[tri[:,0]])
    for k in range(3):
        np.add.at(normals, tri[:,k], cross)
    normals /= np.maximum(np.linalg.norm(normals, axis=1)[:,None], 1e-20)
    edges = np.array([e.vertices[:] for e in mesh.edges])
    edges = np.vstack([edges, edges[:,::-1]])
    degree = np.bincount(edges[:,0], minlength=len(v))
    mean = np.zeros_like(v)
    np.add.at(mean, edges[:,0], v[edges[:,1]])
    mean /= degree[:,None]
    edge2 = np.zeros(len(v))
    np.add.at(edge2, edges[:,0], np.sum((v[edges[:,0]]-v[edges[:,1]])**2, axis=1))
    edge2 /= degree
    curvature = np.sum((v-mean)*normals,axis=1) / np.maximum(edge2,1e-20)
    # Smooth the geometry measurement, never generate colour or random variation.
    for _ in range(3):
        neighbor = np.zeros(len(v))
        np.add.at(neighbor, edges[:,0], curvature[edges[:,1]])
        curvature = .5*curvature + .5*neighbor/degree
    convex = np.clip(curvature / 350.,0,1)
    concave = np.clip(-curvature / 350.,0,1)
    colors = mesh.color_attributes.new(name='BakedGeometryMasks', type='FLOAT_COLOR', domain='CORNER')
    field = mesh.attributes.get('enamel_field7')
    for polygon in mesh.polygons:
        enamel = float(field.data[polygon.index].value > 0) if field else 0.
        for li in polygon.loop_indices:
            vi = mesh.loops[li].vertex_index
            colors.data[li].color = (enamel, convex[vi], concave[vi], 1.)
    material = bpy.data.materials.new(obj.name + '_GeometryBake')
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    output = nodes.new('ShaderNodeOutputMaterial')
    emit = nodes.new('ShaderNodeEmission')
    attr = nodes.new('ShaderNodeVertexColor')
    attr.layer_name = colors.name
    links.new(attr.outputs['Color'], emit.inputs['Color'])
    links.new(emit.outputs[0], output.inputs['Surface'])
    mesh.materials.clear()
    mesh.materials.append(material)

images = {}
for label in ['geometry-masks','ao','geometry-masks-rear','ao-rear']:
    image = bpy.data.images.new(label,width=SIZE,height=SIZE,alpha=False)
    image.generated_color = (0,0,0,1)
    image.colorspace_settings.name = 'Non-Color'
    image.filepath_raw = str(OUT / 'bakes' / (label + '.png'))
    image.file_format = 'PNG'
    images[label] = image

for low in lows.values():
    low.hide_render = True
    low.visible_diffuse = False
    low.visible_glossy = False
    low.visible_shadow = False
for label in ['geometry-masks','ao']:
    for part, low in lows.items():
        low.hide_render = False
        material = bpy.data.materials.new(part + '_' + label + '_Target')
        material.use_nodes = True
        target = material.node_tree.nodes.new('ShaderNodeTexImage')
        target.image = images[label]
        material.node_tree.nodes.active = target
        low.data.materials.clear()
        low.data.materials.append(material)
        highmat = highs[part].data.materials[0]
        nodes, links = highmat.node_tree.nodes, highmat.node_tree.links
        emit = next(n for n in nodes if n.type=='EMISSION')
        if label == 'ao':
            ao = nodes.new('ShaderNodeAmbientOcclusion')
            ao.samples = 16
            ao.inputs['Distance'].default_value = .002
            links.new(ao.outputs['AO'], emit.inputs['Color'])
        bpy.ops.object.select_all(action='DESELECT')
        highs[part].select_set(True)
        low.select_set(True)
        bpy.context.view_layer.objects.active = low
        scene.render.bake.cage_extrusion = .0001 if part=='Body' else .0005
        scene.render.bake.max_ray_distance = .00025 if part=='Body' else .001
        bpy.ops.object.bake(type='EMIT')
        if part == 'Body':
            target.image = images[label + '-rear']
            scene.render.bake.cage_extrusion = .0006
            scene.render.bake.max_ray_distance = .0012
            bpy.ops.object.bake(type='EMIT')
            images[label + '-rear'].save()
            target.image = images[label]
        low.hide_render = True
        print('BAKED',label,part,flush=True)
    images[label].save()
shutil.copyfile(FIT / 'medal-low-normal.png', OUT / 'bakes/normal.png')
normal = bpy.data.images.load(str(OUT / 'bakes/normal.png'))
assert tuple(normal.size)==(2048,2048)
report = {
    'source': str(FIT / 'medal-high.glb'), 'target': str(FIT / 'medal-low.glb'),
    'editable_source': str(FIT / 'medal-fitted.blend'), 'resolution': SIZE,
    'engine':'Cycles CPU', 'samples':16, 'ao_distance_m':.002, 'ao_node_samples':16,
    'method':'Selected-to-active emission transfer of high-surface AO and high vertex/face geometry attributes. Original low UVs. Rear-only reach composite performed by prepare_colours.py.',
    'mask_channels': {'R':'Topology-owned enamel_field7; brass=1-R','G':'convex signed uniform Laplacian curvature','B':'concave signed uniform Laplacian curvature'},
    'curvature':'dot(vertex - neighbor_mean, area-weighted normal) / mean edge squared; 3 half-neighbor smoothing steps; clamp signed curvature / 350 per metre.',
    'body_front': {'cage_m':.0001,'ray_m':.00025}, 'body_rear':{'cage_m':.0006,'ray_m':.0012},
    'hardware':{'cage_m':.0005,'ray_m':.001}, 'padding_px':8,
    'normal_reused':json.loads((FIT/'normal-bake.json').read_text()),
    'normal_existing_validation':json.loads((FIT/'bake-check.json').read_text()),
    'normal_validation':'2048 dimensions checked; existing exported Mikk-tangent normal/reach audit retained. No rebake or geometry edits.',
}
(OUT / 'bakes/settings.json').write_text(json.dumps(report,indent=2))
print('BAKES_COMPLETE',flush=True)
