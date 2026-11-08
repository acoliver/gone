"""Seeded, closed Voronoi crust plates and zero-pressure cloth cushion covers."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import apply, collision, recalc, settle, solidify, surface_tree


def largest_shell(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    remaining = set(bm.verts)
    groups = []
    while remaining:
        frontier = {remaining.pop()}
        group = set(frontier)
        while frontier:
            following = {e.other_vert(v) for v in frontier for e in v.link_edges} & remaining
            remaining -= following
            group |= following
            frontier = following
        groups.append(group)
    main = max(groups, key=len)
    bmesh.ops.delete(bm, geom=[v for g in groups if g is not main for v in g], context='VERTS')
    bm.to_mesh(obj.data)
    bm.free()
    recalc(obj)


def plates(core, seed, count, gap):
    """Clip the fitted shell to Voronoi half-spaces and close every cut plane."""
    rng = np.random.default_rng(seed)
    points = np.array([v.co[:] for v in core.data.vertices])
    lo, hi = points.min(0), points.max(0)
    sites = rng.uniform(lo[:2], hi[:2], (count, 2))
    output = bmesh.new()
    accepted = 0
    for i, site in enumerate(sites):
        bm = bmesh.new()
        bm.from_mesh(core.data)
        for j, other in enumerate(sites):
            if i == j:
                continue
            normal = Vector((*(other - site), 0)).normalized()
            middle = (site + other) / 2
            origin = Vector((*middle, 0)) - normal * gap / 2
            result = bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
                                           dist=1e-7, plane_co=origin, plane_no=normal, clear_outer=True)
            boundary = [e for e in result['geom_cut'] if isinstance(e, bmesh.types.BMEdge) and e.is_boundary]
            if boundary:
                bmesh.ops.holes_fill(bm, edges=boundary, sides=0)
        if bm.faces:
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            mapping = {v: output.verts.new(v.co) for v in bm.verts}
            for face in bm.faces:
                output.faces.new([mapping[v] for v in face.verts])
            accepted += 1
        bm.free()
    output.to_mesh(core.data)
    output.free()
    recalc(core)
    return accepted


def collapse(obj, config, seed):
    name = obj.name
    largest_shell(obj)
    original = np.array([v.co[:] for v in obj.data.vertices])
    base = original[:, 2].min()
    bottom_world = config['support_z_m'] + config['support_gap_m']
    local_bottom = (obj.matrix_world.inverted() @ Vector((0, 0, bottom_world))).z
    back = name.startswith('Back')
    depth_ratio = config['back_depth_ratio'] if back else 1
    rear = original[:, 1].max()
    for vertex in obj.data.vertices:
        vertex.co.z = local_bottom + (vertex.co.z - base) * config['height_ratio'] / depth_ratio
        if back:
            vertex.co.y = rear + (vertex.co.y - rear) * depth_ratio + config['back_support_y_shift_m']
    recalc(obj)
    core = obj.copy()
    core.data = obj.data.copy()
    bpy.context.collection.objects.link(core)
    core.name = name + '_CrustWork'
    mod = core.modifiers.new('Crust simplification', 'DECIMATE')
    mod.ratio = config['core_reduction']
    apply(core, mod)
    support_fit = local_bottom - min(v.co.z for v in core.data.vertices)
    for mesh_obj in [core, obj]:
        for vertex in mesh_obj.data.vertices:
            vertex.co.z += support_fit
    envelope = core.copy()
    envelope.data = core.data.copy()
    envelope.name = name + '_ContactEnvelope'
    envelope.hide_render = True
    bpy.context.collection.objects.link(envelope)
    collision(envelope, .0005)
    count = plates(core, seed, config['voronoi_cells'], config['crack_width_m'])
    core.data.materials.clear()
    foam = bpy.data.materials.get('Foam') or bpy.data.materials.new('Foam')
    foam.diffuse_color = (.20, .09, .035, 1)
    foam.use_nodes = True
    shader = foam.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (.20, .09, .035, 1)
    shader.inputs['Roughness'].default_value = 1
    core.data.materials.append(foam)
    # A continuous contact envelope keeps the cover from tunnelling into narrow cracks.
    # The upholstery's lower half is no longer supported by elastic foam.
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    remove = [f for f in bm.faces if f.normal.z < .05]
    bmesh.ops.delete(bm, geom=remove, context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(obj.data)
    bm.free()
    for v in obj.data.vertices:
        v.co.z += config['cover_lift_m']
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    rim = {tuple(round(c, 6) for c in v.co) for e in bm.edges if e.is_boundary for v in e.verts}
    rng = np.random.default_rng(seed)
    contact_points = np.array([v.co[:] for v in envelope.data.vertices])
    sites = rng.uniform(contact_points.min(0)[:2], contact_points.max(0)[:2], (config['voronoi_cells'], 2))
    faces = list(bm.faces)
    distances = []
    for face in faces:
        center = np.array(face.calc_center_median())[:2]
        nearest = np.sort(np.linalg.norm(sites - center, axis=1))[:2]
        distances.append(nearest[1] - nearest[0])
    cutoff = np.quantile(distances, config['cover_loss_fraction'])
    selected = [f for f, distance in zip(faces, distances) if distance < cutoff and not any(tuple(round(c, 6) for c in v.co) in rim for v in f.verts)]
    bmesh.ops.delete(bm, geom=selected, context='FACES')
    bm.to_mesh(obj.data)
    bm.free()
    pins = {v.index: 1 for v in obj.data.vertices if tuple(round(c, 6) for c in v.co) in rim}
    result = settle(obj, config['cloth'], pins, pressure=0)
    mod = obj.modifiers.new('Upholstery reduction', 'DECIMATE')
    mod.ratio = config['cover_reduction']
    apply(obj, mod)
    contact = surface_tree(envelope)
    inverse = obj.matrix_world.inverted()
    correction_max = 0.0
    clearance = config['cover_thickness_m'] / 2 + config['contact_clearance_m']
    for vertex in obj.data.vertices:
        world = obj.matrix_world @ vertex.co
        point, normal, _, _ = contact.find_nearest(world)
        signed = (world - point).dot(normal)
        if signed < clearance:
            correction_max = max(correction_max, clearance - signed)
            vertex.co = inverse @ (point + normal * clearance)
    bpy.data.objects.remove(envelope, do_unlink=True)
    solidify(obj, config['cover_thickness_m'])
    core.modifiers.clear()
    result['post_reduction_clearance_fit_max_m'] = correction_max
    result['decimation_support_fit_z_m'] = support_fit
    # Keep the original node and pivot. Both closed crust and thin cover belong to it.
    from common import activate
    activate(obj)
    core.select_set(True)
    bpy.ops.object.join()
    obj.name = name
    obj.data.name = name
    recalc(obj)
    result.update({'seed': seed, 'voronoi_plates': count, 'height_ratio': config['height_ratio'],
                   'pressure': 0, 'crack_width_m': config['crack_width_m']})
    return result


def seat_on_support(obj, config):
    support = surface_tree(bpy.data.objects[config['support']])
    crust_vertices = {index for face in obj.data.polygons if obj.data.materials[face.material_index].name == 'Foam' for index in face.vertices}
    bottom = min((obj.matrix_world @ obj.data.vertices[index].co).z for index in crust_vertices)
    gaps = []
    for index in crust_vertices:
        point = obj.matrix_world @ obj.data.vertices[index].co
        if point.z > bottom + .002:
            continue
        hit, _, _, _ = support.ray_cast(point, Vector((0, 0, -1)))
        if hit is not None:
            gaps.append(point.z - hit.z)
    if not gaps:
        raise ValueError(f'{obj.name}: crust has no frame beneath its bottom surface')
    drop = min(gaps) - config['support_gap_m']
    inverse = obj.matrix_world.inverted()
    for vertex in obj.data.vertices:
        world = obj.matrix_world @ vertex.co
        world.z -= drop
        vertex.co = inverse @ world
    return {'vertical_translation_m': -drop, 'target_gap_m': config['support_gap_m']}


def main():
    from build import run
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--params', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    run(args.source, json.loads(args.params.read_text()), args.output, stages={'foam'})


if __name__ == '__main__':
    main()
