"""Bounded fairing of reduced cloth and local untangling at the throw hold."""
import bmesh
import numpy as np
from mathutils import Vector

from common import recalc
from sofa_pass9_finish import points



def roughen_residue(obj, seed, amplitude=.0015):
    from opacity_bake import value_noise
    original = points(obj)
    offset = np.column_stack([amplitude*value_noise(original, .030, seed+axis*31)
                              for axis in range(3)])
    inverse = obj.matrix_world.inverted()
    for vertex, position in zip(obj.data.vertices, original+offset):
        vertex.co = inverse@Vector(position)
    recalc(obj)
    return {'method': 'continuous three-axis crust detail before contact clearance',
            'wavelength_m': .030, 'amplitude_m': amplitude, 'seed': seed,
            'maximum_displacement_m': float(np.linalg.norm(offset, axis=1).max())}


def break_planar_patches(obj, lift=.0012, maximum_faces=64):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bm.normal_update()
    bm.faces.index_update()
    selected = set()
    for edge in bm.edges:
        if len(edge.link_faces) != 2 or edge.calc_face_angle() >= .01:
            continue
        if sum(f.calc_area() for f in edge.link_faces) <= .001:
            continue
        selected.update(f for f in edge.link_faces if f.normal.z > .1)
    selected = sorted(selected, key=lambda f: (-f.calc_area(), f.index))[:maximum_faces]
    for face in selected:
        vertices = list(face.verts)
        apex = bm.verts.new(face.calc_center_median()+face.normal*lift)
        for a, b in zip(vertices, vertices[1:]+vertices[:1]):
            bm.faces.new((a, b, apex))
        bm.faces.remove(face)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    recalc(obj)
    return {'method': 'explicit crust relief on broad near-planar top patches',
            'lift_m': lift, 'faces_refined': len(selected), 'triangles_added': len(selected)*2,
            'maximum_faces': maximum_faces}

def fair_interior(obj, maximum=.006, iterations=10, nonshrinking=False):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    original = {v: v.co.copy() for v in bm.verts}
    coordinates = np.array([tuple(v.co) for v in bm.verts])
    lower, upper = coordinates.min(0), coordinates.max(0)
    fixed = {v for v in bm.verts if v.is_boundary}
    layer = bm.verts.layers.deform.active
    hold = obj.vertex_groups.get('Retained stitches')
    if hold:
        fixed.update(v for v in bm.verts if v[layer].get(hold.index, 0.) > .5)
    factors = (.5, -.53) if nonshrinking else (.45,)
    for _ in range(iterations):
        for factor in factors:
            updates = {}
            for vertex in bm.verts:
                if vertex in fixed or not vertex.link_edges:
                    continue
                mean = sum((e.other_vert(vertex).co for e in vertex.link_edges), Vector())/len(vertex.link_edges)
                target = vertex.co+factor*(mean-vertex.co)-original[vertex]
                if target.length > maximum:
                    target *= maximum/target.length
                updates[vertex] = Vector(np.clip(np.asarray(original[vertex]+target), lower, upper))
            for vertex, position in updates.items():
                vertex.co = position
    moved = max(((v.co-original[v]).length for v in bm.verts), default=0.)
    bm.to_mesh(obj.data)
    bm.free()
    recalc(obj)
    return {'method': 'bounded one-ring fairing; open boundaries and retained stitches fixed',
            'nonshrinking': nonshrinking, 'factors': list(factors),
            'iterations': iterations, 'displacement_limit_m': maximum, 'maximum_displacement_m': moved}


def restore_hold_patch(obj, rest, centre=(1.113, .130, .755), inner=.022, outer=.055):
    original = points(obj)
    rest = np.asarray(rest)
    if rest.shape != original.shape:
        raise ValueError('Hold repair requires the matching prepared cloth topology')
    distance = np.linalg.norm(original-np.asarray(centre), axis=1)
    weight = np.clip((outer-distance)/(outer-inner), 0, 1)
    weight = weight*weight*(3-2*weight)
    hold = obj.vertex_groups['Retained stitches'].index
    for vertex in obj.data.vertices:
        if any(g.group == hold and g.weight > .5 for g in vertex.groups):
            weight[vertex.index] = 0.
    result = original+(rest-original)*weight[:, None]
    inverse = obj.matrix_world.inverted()
    for vertex, position in zip(obj.data.vertices, result):
        vertex.co = inverse@Vector(position)
    recalc(obj)
    return {'method': 'restore the prepared local fold around the retained stitches, smooth collar into solved hang',
            'inner_radius_m': inner, 'outer_radius_m': outer, 'centre_blender_m': list(centre),
            'moved_vertices': int(np.count_nonzero(weight)),
            'maximum_displacement_m': float(np.linalg.norm(result-original, axis=1).max())}
