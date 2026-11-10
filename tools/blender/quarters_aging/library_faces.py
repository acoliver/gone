"""Read fitted face geometry and existing UVs without editing the source blend."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np


def extract(blend, output):
    bpy.ops.wm.open_mainfile(filepath=str(blend.resolve()))
    faces, materials, meshes = [], set(), []
    for obj in sorted(bpy.context.scene.objects, key=lambda o: o.name):
        if obj.type != 'MESH' or obj.hide_render or obj.name.startswith('Guide_'):
            continue
        if obj.modifiers:
            raise ValueError(f'apply modifiers before library mapping: {obj.name}')
        mesh = obj.data
        if not mesh.uv_layers:
            raise ValueError(f'missing fitted UVs: {obj.name}')
        mesh.calc_loop_triangles()
        meshes.append(obj.name)
        points = np.array([obj.matrix_world @ vertex.co for vertex in mesh.vertices])
        normals = [np.array((obj.matrix_world.to_3x3().inverted().transposed() @ p.normal).normalized()) for p in mesh.polygons]
        parent = list(range(len(mesh.polygons)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        # A concave manufactured face may have been split for export. Adjacent
        # coplanar polygons share one image instead of exposing triangulation.
        edges = {}
        for p in mesh.polygons:
            for edge in p.edge_keys:
                for other in edges.get(tuple(sorted(edge)), []):
                    q = mesh.polygons[other]
                    if p.material_index == q.material_index and np.dot(normals[p.index], normals[other]) > .999999:
                        distance = abs(np.dot(points[p.vertices[0]]-points[q.vertices[0]], normals[other]))
                        if distance < 1e-6:
                            parent[find(p.index)] = find(other)
                edges.setdefault(tuple(sorted(edge)), []).append(p.index)
        groups = {}
        uv = mesh.uv_layers.active.data
        for tri in mesh.loop_triangles:
            key = find(tri.polygon_index)
            groups.setdefault(key, []).append(tri)
        for group, triangles in sorted(groups.items()):
            polygon = mesh.polygons[group]
            material = mesh.materials[polygon.material_index].name
            materials.add(material)
            xyz = [points[list(t.vertices)].tolist() for t in triangles]
            tex = [[list(uv[i].uv) for i in t.loops] for t in triangles]
            faces.append(dict(id=f'{obj.name}/{group}', part=obj.name, material=material,
                              normal=normals[group].tolist(), triangles=xyz, uv=tex))
    if not faces:
        raise ValueError('no renderable fitted meshes')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(dict(blend=str(blend), faces=faces, materials=sorted(materials), parts=meshes)))
    print('EXTRACTED', blend.name, len(meshes), 'meshes', len(faces), 'faces', sorted(materials), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blend', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    extract(args.blend, args.output)
