"""Medal-only selected-to-active bakes on the accepted, unmodified stage1c mesh."""
import argparse
import json
import math
from pathlib import Path
import sys
import time

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE.parents[1]))
from hatch_bake import new_image, save_image

SIZE = 2048
SEED = 130303


def pixels(image):
    data = np.empty(SIZE * SIZE * 4, np.float32)
    image.pixels.foreach_get(data)
    return data.reshape(SIZE, SIZE, 4)


def image_from(name, data, out, depth=16, color=False):
    image = bpy.data.images.new(name, SIZE, SIZE, alpha=True, float_buffer=True)
    image.colorspace_settings.name = 'sRGB' if color else 'Non-Color'
    values = np.ones((SIZE, SIZE, 4), np.float32)
    if data.ndim == 2:
        values[:, :, :3] = data[:, :, None]
    else:
        values[:, :, :data.shape[2]] = data
    image.pixels.foreach_set(values.ravel())
    scene = bpy.context.scene
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.color_depth = str(depth)
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    image.save_render(str(out / (name + '.png')), scene=scene)
    image.filepath_raw = str(out / (name + '.png'))
    return image


def mesh_arrays(obj):
    m = obj.data
    return dict(vertices=np.array([v.co[:] for v in m.vertices]),
                faces=np.array([p.vertices[:] for p in m.polygons]),
                smooth=np.array([p.use_smooth for p in m.polygons]),
                normals=np.array([x.vector[:] for x in m.corner_normals]),
                regions=np.array([x.value for x in m.attributes['FeatureRegion'].data]),
                materials=np.array([p.material_index for p in m.polygons]))


def tree(obj):
    return BVHTree.FromPolygons([v.co[:] for v in obj.data.vertices],
                               [p.vertices[:] for p in obj.data.polygons], all_triangles=True)


def curvature(obj, out):
    """Signed normal variation, followed by two metric-space Gaussian filters."""
    m = obj.data
    v = np.array([x.co[:] for x in m.vertices], np.float64)
    normals = np.array([x.normal[:] for x in m.vertices], np.float64)
    e = np.array([x.vertices[:] for x in m.edges])
    delta = v[e[:, 1]] - v[e[:, 0]]
    length = np.linalg.norm(delta, axis=1)
    signed = np.einsum('ij,ij->i', normals[e[:, 1]] - normals[e[:, 0]], delta) / np.maximum(length * length, 1e-20)
    total = np.zeros(len(v)); weight = np.zeros(len(v))
    for side in [0, 1]:
        np.add.at(total, e[:, side], signed * length)
        np.add.at(weight, e[:, side], length)
    signed = total / weight
    # Blender has no SciPy. The existing Hunyuan environment owns the spatial filter.
    np.savez_compressed(out / 'curvature-source.npz', vertices=v, signed=signed)
    import subprocess
    subprocess.run(['/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python',
                    str(HERE / 'medal_stage2_texture.py'), 'filter', str(out)], check=True)
    filtered = np.load(out / 'curvature-filtered.npz')
    for key in ['convex', 'concave']:
        attr = m.attributes.new('Medal_' + key, 'FLOAT_VECTOR', 'POINT')
        attr.data.foreach_set('vector', np.repeat(filtered[key][:, None], 3, axis=1).astype(np.float32).ravel())
    return filtered


def create_material(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree; nt.nodes.clear()
    output = nt.nodes.new('ShaderNodeOutputMaterial')
    emit = nt.nodes.new('ShaderNodeEmission')
    nt.links.new(emit.outputs[0], output.inputs['Surface'])
    return mat, emit


def bake(out):
    out.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(HERE / 'medal-low.blend'))
    high, low = bpy.data.objects['MedalHigh'], bpy.data.objects['MedalLow']
    originals = {o.name: mesh_arrays(o) for o in [high, low]}
    for obj in bpy.context.scene.objects:
        obj.hide_render = obj not in [high, low]
        obj.hide_set(obj not in [high, low])
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'; scene.cycles.device = 'CPU'
    scene.cycles.seed = SEED; scene.cycles.use_animated_seed = False
    scene.cycles.samples = 64
    scene.render.threads_mode = 'FIXED'; scene.render.threads = 10
    scene.render.bake.margin = 16; scene.render.bake.margin_type = 'EXTEND'
    scene.render.bake.normal_space = 'TANGENT'
    scene.render.bake.normal_r = 'POS_X'; scene.render.bake.normal_g = 'POS_Y'; scene.render.bake.normal_b = 'POS_Z'
    scene.render.bake.cage_extrusion = .00015
    scene.render.bake.max_ray_distance = .00030
    scene.render.bake.use_selected_to_active = True
    scene.render.bake.use_clear = True
    high.data.materials.clear()
    source, emit = create_material('MedalBakeSource')
    high.data.materials.append(source)
    for p in high.data.polygons: p.material_index = 0
    target, _ = create_material('MedalBakeTarget')
    low.data.materials.clear(); low.data.materials.append(target)
    for p in low.data.polygons: p.material_index = 0
    tex = target.node_tree.nodes.new('ShaderNodeTexImage')
    target.node_tree.nodes.active = tex
    # Emission IDs expose crossed-region rays before any material work.
    attr = high.data.attributes.new('MedalRegionID', 'FLOAT_VECTOR', 'FACE')
    region = originals[high.name]['regions']
    attr.data.foreach_set('vector', np.repeat(((region + 1) / 16)[:, None], 3, axis=1).astype(np.float32).ravel())
    nt = source.node_tree
    def attribute(name):
        node = nt.nodes.new('ShaderNodeAttribute'); node.attribute_name = name
        return node.outputs['Vector']
    def execute(name, kind='EMIT', socket=None, samples=64):
        image = bpy.data.images.new(name, SIZE, SIZE, alpha=True, float_buffer=True)
        image.colorspace_settings.name = 'Non-Color'
        tex.image = image
        if socket is not None:
            nt.links.new(socket, emit.inputs['Color'])
        scene.cycles.samples = samples
        bpy.ops.object.select_all(action='DESELECT')
        high.select_set(True); low.select_set(True); bpy.context.view_layer.objects.active = low
        start = time.time()
        print('BAKE START', name, flush=True)
        bpy.ops.object.bake(type=kind, uv_layer='MedalUV')
        data = pixels(image)
        np.save(out / (name + '.npy'), data)
        image_from(name, data, out)
        print('BAKE DONE', name, round(time.time() - start, 2), flush=True)
        return data
    ids = execute('projected_regions', socket=attribute('MedalRegionID'))
    normal = execute('geometry_normal', 'NORMAL')
    curvature(high, out)
    for key in ['convex', 'concave']:
        execute('curvature_' + key, socket=attribute('Medal_' + key))
    ao = nt.nodes.new('ShaderNodeAmbientOcclusion')
    ao.samples = 1; ao.only_local = False
    for radius, label in [(.0003, 'near'), (.002, 'local')]:
        ao.inputs['Distance'].default_value = radius
        execute('ao_' + label, socket=ao.outputs['AO'], samples=128)
    geom = nt.nodes.new('ShaderNodeNewGeometry')
    # Position is encoded into positive channels without a color transform.
    scale = nt.nodes.new('ShaderNodeVectorMath'); scale.operation = 'MULTIPLY_ADD'
    nt.links.new(geom.outputs['Position'], scale.inputs[0])
    scale.inputs[1].default_value = (20, 20, 20); scale.inputs[2].default_value = (.5, .5, .5)
    execute('surface_position', socket=scale.outputs[0])
    scale2 = nt.nodes.new('ShaderNodeVectorMath'); scale2.operation = 'MULTIPLY_ADD'
    nt.links.new(geom.outputs['Normal'], scale2.inputs[0])
    scale2.inputs[1].default_value = (.5, .5, .5); scale2.inputs[2].default_value = (.5, .5, .5)
    execute('high_shading_normal', socket=scale2.outputs[0])
    # Restore the immutable region/material assignment, then save standalone candidate sources.
    for obj in [high, low]:
        for p, i in zip(obj.data.polygons, originals[obj.name]['materials']): p.material_index = int(i)
    low.data.calc_tangents(uvmap='MedalUV')
    np.savez_compressed(out / 'low-bake-context.npz', **originals[low.name],
        uv=np.array([x.uv[:] for x in low.data.uv_layers.active.data]).reshape(-1, 3, 2),
        tangent=np.array([x.tangent[:] for x in low.data.loops]).reshape(-1, 3, 3),
        sign=np.array([x.bitangent_sign for x in low.data.loops]).reshape(-1, 3),
        region_names=np.array(json.loads(low['feature_names'])))
    for obj in [high, low]:
        now = mesh_arrays(obj)
        for field in ['vertices', 'faces', 'smooth', 'normals', 'regions']:
            assert np.array_equal(now[field], originals[obj.name][field]), (obj.name, field, 'geometry changed')
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'medal-bake.blend'))
    (out / 'bake-settings.json').write_text(json.dumps(dict(renderer='Cycles CPU', seed=SEED,
        normal_samples=64, ao_samples=128, resolution=SIZE, gutter_dilation_texels=16,
        selected_to_active=True, cage_extrusion_mm=.15, max_ray_distance_mm=.30,
        normal_convention='OpenGL +Y', ao_radii_mm=[.3, 2], geometry_unchanged=True), indent=2))
    print('BAKES COMPLETE', flush=True)


if __name__ == '__main__':
    bake(Path(sys.argv[sys.argv.index('--') + 1]))
