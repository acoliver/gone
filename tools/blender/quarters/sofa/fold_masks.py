"""Bake cloth-only fold occlusion without changing the retained sofa meshes."""
import argparse
from pathlib import Path
import sys

import bmesh
import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from material_roles import role


def bake_folds(objects, output, size, distance=.03):
    image = bpy.data.images.new('Sofa_cloth_folds', width=size, height=size, alpha=False)
    image.colorspace_settings.name = 'Non-Color'
    image.pixels.foreach_set(np.ones(size * size * 4, dtype=np.float32))
    bpy.ops.object.select_all(action='DESELECT')
    clones, materials = [], []
    for source in objects:
        source.hide_render = True
        for slot, original in enumerate(source.data.materials):
            if role(original.name) not in {'fabric', 'throw'}:
                continue
            clone = source.copy()
            clone.data = source.data.copy()
            bpy.context.collection.objects.link(clone)
            clone.hide_render = False
            clone.hide_set(False)
            clone.select_set(True)
            mesh = bmesh.new()
            mesh.from_mesh(clone.data)
            bmesh.ops.delete(mesh, geom=[face for face in mesh.faces if face.material_index != slot], context='FACES')
            mesh.to_mesh(clone.data)
            mesh.free()
            material = bpy.data.materials.new('Sofa_fold_bake')
            material.use_nodes = True
            nodes, links = material.node_tree.nodes, material.node_tree.links
            nodes.clear()
            output_node = nodes.new('ShaderNodeOutputMaterial')
            emit = nodes.new('ShaderNodeEmission')
            occlusion = nodes.new('ShaderNodeAmbientOcclusion')
            occlusion.only_local = True
            occlusion.inputs['Distance'].default_value = distance
            occlusion.samples = 8
            links.new(occlusion.outputs['Color'], emit.inputs['Color'])
            links.new(emit.outputs[0], output_node.inputs['Surface'])
            target = nodes.new('ShaderNodeTexImage')
            target.image = image
            nodes.active = target
            clone.data.materials.clear()
            clone.data.materials.append(material)
            for polygon in clone.data.polygons:
                polygon.material_index = 0
            clones.append(clone)
            materials.append(material)
    assert clones, 'fold bake requires cloth material slots'
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 8
    scene.render.bake.margin = 8
    scene.render.bake.use_clear = False
    scene.render.bake.use_selected_to_active = False
    bpy.context.view_layer.objects.active = clones[0]
    bpy.ops.object.bake(type='EMIT')
    image.filepath_raw = str(output)
    image.file_format = 'PNG'
    image.save()
    for clone in clones:
        mesh = clone.data
        bpy.data.objects.remove(clone, do_unlink=True)
        bpy.data.meshes.remove(mesh)
    for material in materials:
        bpy.data.materials.remove(material)
    for source in objects:
        source.hide_render = False
    print('CLOTH FOLDS', output, flush=True)


def bake_cloth_masks(objects, directory, size):
    bake_folds(objects, directory / 'fold.png', size)
    bake_folds(objects, directory / 'cloth_cavity.png', size, distance=.008)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', choices=['aged', 'as_built'], required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    directory = ROOT / 'tmp/mat/sofa' / args.state
    bpy.ops.wm.open_mainfile(filepath=str(directory / 'prepared.blend'))
    objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    bake_cloth_masks(objects, directory, 4096 if args.state == 'aged' else 2048)
