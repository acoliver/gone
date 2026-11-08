"""Boundary-weighted game meshes and selected-to-active Cycles surface bakes."""
import heapq
import math
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils.kdtree import KDTree

from common import activate, apply


def boundary_segments(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    result = np.array([[obj.matrix_world@v.co for v in e.verts] for e in bm.edges if e.is_boundary])
    bm.free()
    return result.reshape((-1, 2, 3))


def boundary_samples(segments, step=.00025):
    points = []
    for a, b in segments:
        n = max(1, math.ceil(np.linalg.norm(b-a)/step))
        points.extend(a+(b-a)*t for t in np.linspace(0, 1, n+1))
    return points


def boundary_hausdorff(a, b, step=.00025):
    sa, sb = boundary_samples(boundary_segments(a), step), boundary_samples(boundary_segments(b), step)
    if not sa and not sb:
        return 0.
    if not sa or not sb:
        raise ValueError('Decimation changed an open surface into a closed surface')
    def directed(source, target):
        tree = KDTree(len(target))
        for i, p in enumerate(target):
            tree.insert(p, i)
        tree.balance()
        return max(tree.find(p)[2] for p in source)
    # Sampling plus half a source sample spacing bounds the continuous curves.
    return max(directed(sa, sb), directed(sb, sa))+step/2


def decimate(dense, target, protect=.006):
    low = dense.copy()
    low.data = dense.data.copy()
    bpy.context.collection.objects.link(low)
    low.name = dense.name+'_Game'
    low.shape_key_clear()
    keep = low.vertex_groups.get('Keep') or low.vertex_groups.new(name='Keep')
    bm = bmesh.new()
    bm.from_mesh(low.data)
    bm.verts.ensure_lookup_table()
    distances = {v.index: 0. for e in bm.edges if e.is_boundary for v in e.verts}
    pending = [(0., i) for i in distances]
    heapq.heapify(pending)
    while pending:
        distance, index = heapq.heappop(pending)
        if distance != distances[index]:
            continue
        for edge in bm.verts[index].link_edges:
            other = edge.other_vert(bm.verts[index])
            length = (low.matrix_world.to_3x3()@(other.co-bm.verts[index].co)).length
            candidate = distance+length
            if candidate <= protect and candidate < distances.get(other.index, float('inf')):
                distances[other.index] = candidate
                heapq.heappush(pending, (candidate, other.index))
    bm.free()
    # Surface distance avoids freezing unrelated folds that happen to touch a lip.
    if distances:
        keep.add(list(distances), 1., 'REPLACE')
    low.data.calc_loop_triangles()
    initial = len(low.data.loop_triangles)
    working = low.data.copy()
    ratio = min(1., target/initial)
    for _ in range(8):
        low.data = working.copy()
        mod = low.modifiers.new('Keep tear lips', 'DECIMATE')
        mod.decimate_type = 'COLLAPSE'
        mod.ratio = ratio
        mod.use_collapse_triangulate = True
        mod.vertex_group = keep.name
        # Blender decimates the weighted region; Keep names the opposite region.
        mod.invert_vertex_group = True
        mod.vertex_group_factor = 15
        apply(low, mod)
        low.data.calc_loop_triangles()
        count = len(low.data.loop_triangles)
        print(dense.name, 'decimate ratio', ratio, 'triangles', count, 'target', target, flush=True)
        if count <= target:
            break
        ratio *= target/count*.98
    else:
        raise ValueError(f'{dense.name}: cannot meet {target} triangles with protected lips')
    report = {'source_triangles': initial, 'target_triangles': target,
              'triangles': len(low.data.loop_triangles),
              'boundary_hausdorff_upper_m': boundary_hausdorff(dense, low)}
    report['pass'] = report['triangles'] <= target and report['boundary_hausdorff_upper_m'] <= .0015
    return low, report


def bake_uv(obj):
    activate(obj)
    layer = obj.data.uv_layers.get('BakeUV') or obj.data.uv_layers.new(name='BakeUV')
    obj.data.uv_layers.active = layer
    layer.active_render = True
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=.003)
    bpy.ops.object.mode_set(mode='OBJECT')


def bake(dense, low, out, size=4096, samples=16):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    bake_uv(low)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = samples
    scene.render.bake.use_selected_to_active = True
    scene.render.bake.cage_extrusion = .004
    scene.render.bake.max_ray_distance = .012
    scene.render.bake.margin = 8
    mat = bpy.data.materials.new(low.name+'_Baked')
    mat.use_nodes = True
    mat.use_backface_culling = False
    low.data.materials.clear()
    low.data.materials.append(mat)
    for face in low.data.polygons:
        face.material_index = 0
        face.use_smooth = True
    paths = {}
    for kind in ['NORMAL', 'AO']:
        image = bpy.data.images.new(low.name+'_'+kind, width=size, height=size, alpha=False)
        image.colorspace_settings.name = 'Non-Color'
        node = mat.node_tree.nodes.new('ShaderNodeTexImage')
        node.image = image
        node.name = kind
        mat.node_tree.nodes.active = node
        activate(low)
        dense.hide_set(False)
        dense.hide_render = False
        dense.select_set(True)
        bpy.context.view_layer.objects.active = low
        bpy.ops.object.bake(type=kind, normal_space='TANGENT')
        path = out/f'{low.name.lower()}_{kind.lower()}.png'
        image.filepath_raw = str(path)
        image.file_format = 'PNG'
        image.save()
        image.pack()
        paths[kind.lower()] = str(path)
    return mat, paths


def material_maps(mat, color, normal=True, opacity_image=None):
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    shader = nodes.get('Principled BSDF')
    shader.inputs['Roughness'].default_value = .98
    uv = nodes.new('ShaderNodeUVMap')
    uv.uv_map = 'BakeUV'
    for name in ['NORMAL', 'AO']:
        if nodes.get(name):
            links.new(uv.outputs['UV'], nodes[name].inputs['Vector'])
    ao = nodes.get('AO')
    if ao:
        multiply = nodes.new('ShaderNodeMixRGB')
        multiply.blend_type = 'MULTIPLY'
        multiply.inputs[0].default_value = 1
        multiply.inputs[1].default_value = (*color, 1)
        links.new(ao.outputs['Color'], multiply.inputs[2])
        links.new(multiply.outputs['Color'], shader.inputs['Base Color'])
    else:
        shader.inputs['Base Color'].default_value = (*color, 1)
    if normal and nodes.get('NORMAL'):
        nm = nodes.new('ShaderNodeNormalMap')
        nm.uv_map = 'BakeUV'
        links.new(nodes['NORMAL'].outputs['Color'], nm.inputs['Color'])
        links.new(nm.outputs['Normal'], shader.inputs['Normal'])
    if opacity_image:
        image = nodes.new('ShaderNodeTexImage')
        image.image = opacity_image
        links.new(uv.outputs['UV'], image.inputs['Vector'])
        cutoff = nodes.new('ShaderNodeMath')
        cutoff.operation = 'ROUND'
        links.new(image.outputs['Color'], cutoff.inputs[0])
        links.new(cutoff.outputs[0], shader.inputs['Alpha'])
