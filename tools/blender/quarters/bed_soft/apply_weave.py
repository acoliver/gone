"""Apply fine generated yarn detail without changing the retained bedding geometry."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build import ASSETS, export, mesh_points, save


def apply(state):
    aged = state == 'aged'
    source = HERE / ('bed-soft-aged.blend' if aged else 'bed-soft-working.blend')
    bpy.ops.wm.open_mainfile(filepath=str(source))
    quilt = bpy.data.objects['Quilt']
    mesh = quilt.data
    mesh.calc_loop_triangles()
    uv = mesh.uv_layers.active.data
    points = mesh_points(quilt)
    densities = []
    for triangle in mesh.loop_triangles:
        p = points[list(triangle.vertices)]
        q = np.array([uv[index].uv[:] for index in triangle.loops])
        area = np.linalg.norm(np.cross(p[1] - p[0], p[2] - p[0])) / 2
        uv_area = abs(float(np.linalg.det(np.array([q[1] - q[0], q[2] - q[0]])))) / 2
        if area > 1e-10 and uv_area > 1e-12:
            densities.append(np.sqrt(uv_area / area))
    factor = (1 / .12) / float(np.median(densities))
    for loop in uv:
        loop.uv *= factor
    normal_image = bpy.data.images.load(str(ASSETS / 'bed_soft_textures/wool_weave_normal.png'), check_existing=False)
    normal_image.colorspace_settings.name = 'Non-Color'
    normal_image.pack()
    for mat in quilt.data.materials:
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        for node in list(nodes):
            if node.type in ('TEX_IMAGE', 'NORMAL_MAP'):
                nodes.remove(node)
        shader = nodes.get('Principled BSDF')
        color = nodes.new('ShaderNodeTexImage')
        color.image = bpy.data.images.load(str(ASSETS / 'bed_soft_textures' / f'{mat.name.lower()}_weave.png'), check_existing=False)
        color.image.pack()
        normal = nodes.new('ShaderNodeTexImage')
        normal.image = normal_image
        bump = nodes.new('ShaderNodeNormalMap')
        links.new(color.outputs['Color'], shader.inputs['Base Color'])
        links.new(normal.outputs['Color'], bump.inputs['Color'])
        links.new(bump.outputs['Normal'], shader.inputs['Normal'])
    record_path = HERE / ('aging.json' if aged else 'simulation.json')
    record = json.loads(record_path.read_text())
    record['fine_weave'] = {'source': 'assets/props/quarters/sofa/weave.png',
                            'median_tile_pitch_m': .12, 'normal_height_scale_m': .0004,
                            'geometry_unchanged': True}
    record_path.write_text(json.dumps(record, indent=2) + '\n')
    save(source, record)
    export(ASSETS / ('bed_soft_aged.glb' if aged else 'bed_soft.glb'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', choices=('remembered', 'aged'), required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    apply(args.state)
