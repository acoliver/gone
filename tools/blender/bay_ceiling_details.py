"""Mounting-head solids and local return-wall UV projections for fitted panels."""
import math

import bpy
import numpy as np

from bay_ceiling_geometry import LENGTH, WIDTH, THICKNESS


def panel_uv(mesh, top_count, top_triangle_count, boundary):
    uv = mesh.uv_layers.new(name='UV0_planar_with_projected_returns')
    for loop in mesh.loops:
        x, y, _ = mesh.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = (x / LENGTH + .5, y / WIDTH + .5)
    for index, (a, b) in enumerate(boundary):
        edge = np.array(mesh.vertices[b].co[:2]) - np.array(mesh.vertices[a].co[:2])
        inward = np.array([-edge[1], edge[0]]) / np.linalg.norm(edge)
        # Project the 2 mm return onto the metal-side edge bank of the planar bake.
        # Each edge is a separate UV strip, so bends do not collapse this dimension.
        for polygon in mesh.polygons[2*top_triangle_count + 2*index:2*top_triangle_count + 2*index + 2]:
            for loop_index in polygon.loop_indices:
                vertex = mesh.loops[loop_index].vertex_index
                if vertex >= top_count:
                    x, y, _ = mesh.vertices[vertex].co
                    x, y = np.array([x, y]) + inward * THICKNESS
                    uv.data[loop_index].uv = (x / LENGTH + .5, y / WIDTH + .5)
    return uv


def mount_heads(kind, anchors, material):
    objects = []
    # A single closed flanged head per mount, not a disconnected washer in one mesh.
    profile = ((.006, 0.), (.006, .0008), (.0045, .0012), (.0045, .0038), (.0038, .0044))
    segments = 24
    for index, anchor in enumerate(anchors):
        vertices = [(anchor[0] + radius * math.cos(2*math.pi*i/segments),
                     anchor[1] + radius * math.sin(2*math.pi*i/segments), height)
                    for radius, height in profile for i in range(segments)]
        faces = []
        for ring in range(len(profile) - 1):
            for i in range(segments):
                a, b = ring*segments + i, ring*segments + (i+1) % segments
                faces.extend(((a, b, b+segments), (a, b+segments, a+segments)))
        bottom, top = len(vertices), len(vertices) + 1
        vertices.extend(((anchor[0], anchor[1], 0.), (anchor[0], anchor[1], profile[-1][1])))
        last = (len(profile) - 1)*segments
        for i in range(segments):
            j = (i+1) % segments
            faces.extend(((bottom, j, i), (top, last+i, last+j)))
        name = f'{kind}_mount_head_{index+1}'
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        assert not mesh.validate(verbose=True)
        uv = mesh.uv_layers.new(name='UV0_local_face_projection')
        for polygon in mesh.polygons:
            axes = np.argsort(np.abs(polygon.normal))[:2]
            for loop_index in polygon.loop_indices:
                point = np.array(mesh.vertices[mesh.loops[loop_index].vertex_index].co) - [*anchor, 0.]
                uv.data[loop_index].uv = point[axes] / .016 + .5
            polygon.use_smooth = True
        mesh.set_sharp_from_angle(angle=.7)
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        mesh.materials.append(material)
        obj['role'] = 'separate_flanged_mount_head'
        obj['attachment_index'] = index
        obj['panel_variant'] = kind
        objects.append(obj)
    return objects
