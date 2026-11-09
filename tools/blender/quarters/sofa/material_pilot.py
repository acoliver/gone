"""Prepare material atlases on the retained sofa geometry, bake masks, export."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
from atlas_layout import rectangles
from fold_masks import bake_folds

SCRATCH = ROOT / 'tmp/mat/sofa'
ASSETS = ROOT / 'assets/props/quarters/sofa'


def role(name):
    if name.startswith('PaintedSteel'): return 'paint'
    if name.startswith('BareSteel'): return 'steel'
    if name.startswith(('Foam', 'FloorDust')): return 'foam'
    if name.startswith(('Oatmeal', 'Wool')): return 'throw'
    if name.startswith(('Charcoal', 'Upholstery')): return 'fabric'
    raise ValueError('Unknown sofa material: ' + name)


def image_pixels(image):
    pixels = np.empty(image.size[0] * image.size[1] * 4, np.float32)
    image.pixels.foreach_get(pixels)
    return pixels.reshape(image.size[1], image.size[0], 4)


def prepare(state):
    directory = SCRATCH / state
    directory.mkdir(parents=True, exist_ok=True)
    source = ROOT / ('tmp/age/pass10/sofa-preview.blend' if state == 'aged' else 'tools/blender/quarters/sofa/sofa-working.blend')
    bpy.ops.wm.open_mainfile(filepath=str(source))
    objects = sorted((o for o in bpy.context.scene.objects if o.type == 'MESH'), key=lambda o: o.name)
    groups, sizes = [], []
    size = 4096 if state == 'aged' else 2048
    for obj in objects:
        for slot, material in enumerate(obj.data.materials):
            identity = obj.name + '__' + str(slot)
            kind = role(material.name)
            fringe = 'Fringe' in material.name
            powder = material.name.startswith('FloorDust')
            width, height = (256, 256) if powder else ((256, 512) if fringe else ((512, 512) if kind == 'foam' or obj.name in {'Feet', 'Rivets'} else (1024, 1024)))
            if state == 'as_built': width = height = 512
            sizes.append((identity, width, height))
            groups.append((identity, obj, slot, material, kind))
    layout = rectangles(sizes, size)
    records = []
    saved_images = {}
    for obj in objects:
        obj.data.calc_loop_triangles()
        old_name = 'BakeUV' if 'BakeUV' in obj.data.uv_layers else obj.data.uv_layers[0].name
        atlas = obj.data.uv_layers.new(name='MaterialAtlas')
        old = obj.data.uv_layers[old_name]
        atlas.active_render = True
        obj.data.uv_layers.active = atlas
        for identity, owner, slot, material, kind in groups:
            if owner != obj: continue
            triangles = [t for t in obj.data.loop_triangles if t.material_index == slot]
            loop_ids = np.array([t.loops[:] for t in triangles])
            source_uv = np.array([[old.data[i].uv[:] for i in t] for t in loop_ids])
            # glTF uses the normal texture UV where a material has baked detail.
            x, y, w, h = layout[identity]
            low, high = source_uv.reshape(-1, 2).min(0), source_uv.reshape(-1, 2).max(0)
            if np.any(high <= low): raise ValueError('Degenerate sofa UV bounds: ' + identity)
            uv = ((source_uv - low) / (high - low) * [w - 16, h - 16] + [x + 8, y + 8]) / size
            for indices, coords in zip(loop_ids, uv):
                for i, co in zip(indices, coords): atlas.data[i].uv = co
            points = np.array([[obj.matrix_world @ obj.data.vertices[i].co for i in t.vertices] for t in triangles])
            np.savez_compressed(directory / (identity + '.npz'), uv=uv, source_uv=source_uv, positions=points)
            albedo, normal = None, None
            if material.use_nodes:
                shader = material.node_tree.nodes.get('Principled BSDF')
                if shader and shader.inputs['Base Color'].is_linked:
                    albedo = shader.inputs['Base Color'].links[0].from_node
                    if albedo.type != 'TEX_IMAGE': raise ValueError('Expected direct source albedo: ' + identity)
                    albedo = albedo.image
                normals = [n.image for n in material.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image and ('NORMAL' in n.name.upper() or 'NORMAL' in n.image.name.upper())]
                if normals: normal = normals[0]
            sources = {}
            for label, image in [('albedo', albedo), ('normal', normal)]:
                if image:
                    if image.name not in saved_images:
                        path = directory / (identity + '-' + label + '.npy')
                        np.save(path, image_pixels(image))
                        saved_images[image.name] = path.name
                    sources[label] = saved_images[image.name]
            records.append(dict(identity=identity, part=obj.name, source_material=material.name, role=kind,
                                rectangle=layout[identity], sources=sources, fringe='Fringe' in material.name,
                                powder=material.name.startswith('FloorDust')))
        for name in [layer.name for layer in obj.data.uv_layers if layer.name != 'MaterialAtlas']:
            obj.data.uv_layers.remove(obj.data.uv_layers[name])
        obj['aged_export'] = True
    # Isolate every slot before inserting the shared mask bake target.
    for obj in objects:
        for index, material in enumerate(list(obj.data.materials)):
            obj.data.materials[index] = material.copy()
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 8
    scene.render.bake.margin = 8
    scene.render.bake.use_clear = True
    scene.render.bake.use_selected_to_active = False
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.hide_render = False
        obj.hide_set(False)
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    for channel in ['ao', 'cavity', 'up']:
        image = bpy.data.images.new('Sofa_' + channel, width=size, height=size, alpha=False)
        image.colorspace_settings.name = 'Non-Color'
        for obj in objects:
            for material in obj.data.materials:
                material.use_nodes = True
                nodes, links = material.node_tree.nodes, material.node_tree.links
                nodes.clear()
                output = nodes.new('ShaderNodeOutputMaterial')
                emit = nodes.new('ShaderNodeEmission')
                links.new(emit.outputs[0], output.inputs['Surface'])
                if channel == 'up':
                    geom = nodes.new('ShaderNodeNewGeometry')
                    separate = nodes.new('ShaderNodeSeparateXYZ')
                    links.new(geom.outputs['Normal'], separate.inputs[0])
                    links.new(separate.outputs['Z'], emit.inputs['Color'])
                else:
                    ao = nodes.new('ShaderNodeAmbientOcclusion')
                    ao.inputs['Distance'].default_value = .008 if channel == 'cavity' else .12
                    ao.only_local = channel == 'cavity'
                    ao.samples = 8
                    links.new(ao.outputs['Color'], emit.inputs['Color'])
                target = nodes.new('ShaderNodeTexImage')
                target.image = image
                nodes.active = target
        print('BAKE', state, channel, flush=True)
        bpy.ops.object.bake(type='EMIT')
        image.filepath_raw = str(directory / (channel + '.png'))
        image.file_format = 'PNG'
        image.save()
    bake_folds(objects, directory / 'fold.png', size)
    (directory / 'layout.json').write_text(json.dumps(dict(state=state, size=size, groups=records), indent=2) + '\n')
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(directory / 'prepared.blend'))


def export(state, output=None):
    source = HERE / ('sofa-material-aged.blend' if state == 'aged' else 'sofa-material-clean.blend')
    bpy.ops.wm.open_mainfile(filepath=str(source))
    sys.path.insert(0, str(ROOT / 'tools/blender/quarters_aging'))
    from common import export as export_glb
    export_glb(output or ROOT / 'assets/props/quarters' / ('sofa_aged.glb' if state == 'aged' else 'sofa.glb'))


def assemble(state):
    directory = SCRATCH / state
    bpy.ops.wm.open_mainfile(filepath=str(directory / 'prepared.blend'))
    images = {}
    for kind in ['albedo', 'normal', 'orm']:
        image = bpy.data.images.load(str(ASSETS / (state + '_' + kind + '.png')), check_existing=True)
        image.colorspace_settings.name = 'sRGB' if kind == 'albedo' else 'Non-Color'
        image.pack()
        images[kind] = image
    material = bpy.data.materials.new('SofaFinish_' + state)
    material.use_nodes = True
    material.use_backface_culling = False
    nodes, links = material.node_tree.nodes, material.node_tree.links
    shader = nodes['Principled BSDF']
    uv = nodes.new('ShaderNodeUVMap')
    uv.uv_map = 'MaterialAtlas'
    textures = {}
    for kind, image in images.items():
        tex = nodes.new('ShaderNodeTexImage')
        tex.image = image
        links.new(uv.outputs[0], tex.inputs['Vector'])
        textures[kind] = tex
    links.new(textures['albedo'].outputs['Color'], shader.inputs['Base Color'])
    cutoff = nodes.new('ShaderNodeMath')
    cutoff.operation = 'ROUND'
    links.new(textures['albedo'].outputs['Alpha'], cutoff.inputs[0])
    links.new(cutoff.outputs[0], shader.inputs['Alpha'])
    normal = nodes.new('ShaderNodeNormalMap')
    normal.uv_map = 'MaterialAtlas'
    links.new(textures['normal'].outputs['Color'], normal.inputs['Color'])
    links.new(normal.outputs[0], shader.inputs['Normal'])
    channels = nodes.new('ShaderNodeSeparateColor')
    links.new(textures['orm'].outputs['Color'], channels.inputs[0])
    links.new(channels.outputs['Green'], shader.inputs['Roughness'])
    links.new(channels.outputs['Blue'], shader.inputs['Metallic'])
    # The export recognizes an alpha cutoff without rewriting the alpha image.
    material.surface_render_method = 'DITHERED'
    material.alpha_threshold = .5
    gltf = nodes.new('ShaderNodeGroup')
    group = bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree')
    group.interface.new_socket(name='Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
    gltf.node_tree = group
    links.new(channels.outputs['Red'], gltf.inputs['Occlusion'])
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH': continue
        obj.data.materials.clear()
        obj.data.materials.append(material)
        for face in obj.data.polygons: face.material_index = 0
    for mat in list(bpy.data.materials):
        if mat != material: bpy.data.materials.remove(mat)
    for image in list(bpy.data.images):
        if image not in images.values() and image.users == 0: bpy.data.images.remove(image)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / ('sofa-material-aged.blend' if state == 'aged' else 'sofa-material-clean.blend')))
    export(state)
    export(state, directory / 'repeat.glb')
    actual = ROOT / 'assets/props/quarters' / ('sofa_aged.glb' if state == 'aged' else 'sofa.glb')
    assert actual.read_bytes() == (directory / 'repeat.glb').read_bytes(), 'byte-identical saved-source re-export'
    print('BYTE_IDENTICAL', state, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=['prepare', 'assemble', 'export'], required=True)
    parser.add_argument('--state', choices=['as_built', 'aged'], required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    if args.stage == 'prepare': prepare(args.state)
    elif args.stage == 'assemble': assemble(args.state)
    else: export(args.state, args.output)
