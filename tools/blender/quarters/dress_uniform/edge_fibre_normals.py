"""Shade thin wool edges with their parent cloth's fibre envelope, not card planes."""
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform


def repair(body, sheet):
    points, faces = sheet['vertices'], sheet['faces']
    mesh = bpy.data.meshes.new('Wool fibre normal envelope')
    mesh.from_pydata(points, [], faces)
    mesh.update()
    normals = [v.normal.copy() for v in mesh.vertices]
    tree = BVHTree.FromPolygons(points.tolist(), faces.tolist(), all_triangles=True)
    def normal(point):
        p, _, index, _ = tree.find_nearest(point)
        ids = faces[index]
        n = barycentric_transform(p, *[Vector(points[i]) for i in ids], *[normals[i] for i in ids])
        return n.normalized()
    report = {}
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH' or obj.name not in ['TunicBody', 'Longwoolfringe', 'Seamallowance']:
            continue
        original = [n.vector.copy() for n in obj.data.corner_normals]
        changed = 0
        to_local = obj.matrix_world.to_3x3().inverted()
        for face in obj.data.polygons:
            rim = obj == body and obj.data.materials[face.material_index].name.startswith('WoolCutEdge')
            card = obj != body
            if not rim and not card:
                continue
            centre = obj.matrix_world @ face.center
            if centre.z < -.35 or centre.x < .14:
                continue
            for index in face.loop_indices:
                vertex = obj.data.vertices[obj.data.loops[index].vertex_index]
                n = (to_local @ normal(obj.matrix_world @ vertex.co)).normalized()
                if n.dot(face.normal) < 0:
                    n = -n
                original[index] = n
                changed += 1
        if changed:
            obj.data.normals_split_custom_set(original)
            report[obj.name] = changed
    bpy.data.meshes.remove(mesh)
    return dict(corner_normals=report,
                method='Parent wool surface normals on shoulder rim/fibre cards; base colour, AO and alpha bytes unchanged')
