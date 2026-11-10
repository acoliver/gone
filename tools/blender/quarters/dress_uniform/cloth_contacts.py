"""Require a contact-resolved rest mesh instead of masking small faces."""
import bpy
import numpy as np


def validate_rest_faces(obj, mod):
    if mod.collision_settings.vertex_group_self_collisions:
        raise ValueError('Rest faces must not be excluded from self collision')
    mesh = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    mesh.calc_loop_triangles()
    vertices = np.array([v.co[:] for v in mesh.vertices])
    faces = np.array([t.vertices[:] for t in mesh.loop_triangles])
    triangles = vertices[faces]
    longest = np.linalg.norm(triangles-np.roll(triangles, 1, axis=1), axis=2).max(1)
    altitude = np.linalg.norm(np.cross(triangles[:, 1]-triangles[:, 0],
                                       triangles[:, 2]-triangles[:, 0]), axis=1)/longest
    diameter = 2*mod.collision_settings.self_distance_min
    unresolved = int(np.sum(altitude < diameter))
    if not np.isfinite(altitude).all() or unresolved:
        raise ValueError(f'{obj.name}: {unresolved} unresolved rest faces; minimum altitude {altitude.min():.9f} m, diameter {diameter:.9f} m')
    return dict(exclusion_vertices=0, policy='all dense faces collide',
                contact_diameter_m=diameter, minimum_rest_altitude_m=float(altitude.min()),
                sub_diameter_faces=unresolved, evaluated_triangles=len(faces))
