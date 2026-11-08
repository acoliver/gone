"""Tear baked cloth along seeded fold/stress fields, release stitches and re-settle."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FIBRE_THICKNESS_FACTOR, midsurface, recalc, settle, solidify, surface_tree


def attachment_distance(point, surfaces):
    return min((surface.find_nearest(point)[3] for surface in surfaces), default=float('inf'))


def decay(obj, config, seed, details=()):
    rng = np.random.default_rng(seed)
    midsurface(obj)
    protected = [surface_tree(detail) for detail in details]
    original_area = sum(p.area for p in obj.data.polygons)
    slits = np.array(config['stress_slits_xz_m'], dtype=float)
    slits[:, :2] += rng.uniform(-config['stress_jitter_m'], config['stress_jitter_m'], (len(slits), 2))
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    remove = []
    for face in bm.faces:
        center = face.calc_center_median()
        world = obj.matrix_world @ center
        if attachment_distance(world, protected) < config['detail_protection_m']:
            continue
        if any(x0 <= world.x <= x1 and z0 <= world.z <= z1 for x0, x1, z0, z1 in config.get('retained_seam_boxes_xz_m', [])):
            continue
        if any(x0 <= world.x <= x1 and y0 <= world.y <= y1 and z0 <= world.z <= z1 for x0, x1, y0, y1, z0, z1 in config.get('retained_seam_boxes_xyz_m', [])):
            continue
        cut = False
        for x, z, width, length, angle in slits:
            delta = np.array((world.x - x, world.z - z))
            c, s = np.cos(angle), np.sin(angle)
            across, along = c * delta[0] - s * delta[1], s * delta[0] + c * delta[1]
            # Corrugated edges make elongated fold splits rather than round holes.
            edge = 1 + .18 * np.sin(along * 250 + seed)
            if (across / (width * edge)) ** 2 + (along / length) ** 2 < 1:
                cut = True
        if world.z < config['hem_z_m'] + config['hem_loss_m'] * (.5 + .5 * np.sin(world.x * 173 + seed)):
            cut = True
        if cut:
            remove.append(face)
    removed_area = sum(f.calc_area() for f in remove)
    bmesh.ops.delete(bm, geom=remove, context='FACES')
    remaining = {v for v in bm.verts if v.link_faces}
    component_areas = []
    while remaining:
        frontier = {remaining.pop()}
        group = set(frontier)
        while frontier:
            following = {edge.other_vert(v) for v in frontier for edge in v.link_edges} & remaining
            remaining -= following
            group |= following
            frontier = following
        component_areas.append(sum(face.calc_area() for face in {f for v in group for f in v.link_faces}))
    print(obj.name, 'cut surface component areas', component_areas, flush=True)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    pins = {}
    for vertex in obj.data.vertices:
        world = obj.matrix_world @ vertex.co
        distance = attachment_distance(world, protected)
        if distance < config['detail_pin_radius_m']:
            pins[vertex.index] = 1
        elif config['kind'] == 'tunic':
            # Retain the inner shoulder stitches. The outer left armhole can fall.
            if world.z > -.19 and abs(world.x) < .12:
                pins[vertex.index] = 1
            else:
                lateral = max(0, min(1, (-world.z - .39) / .25))
                lateral *= min(1, max(0, (abs(world.x) - .035) / .11))
                vertex.co.x *= 1 - config['lateral_shrink'] * lateral
        elif world.z > config['retained_corner_z_m'] and world.y < config['retained_corner_y_m']:
            pins[vertex.index] = 1
    simulation = settle(obj, config['cloth'], pins)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    obstacles = [surface_tree(bpy.data.objects[n]) for n in config.get('fray_obstacles', [])]
    candidates = [e for e in bm.edges if e.is_boundary and e.calc_length() > .003]
    fibre_layer = bm.verts.layers.int.new('AgingFiber')
    frays = 0
    for edge in candidates:
        if rng.random() > config['fray_probability']:
            continue
        a, b = edge.verts
        if attachment_distance(obj.matrix_world @ a.co, protected) < config['detail_protection_m']:
            continue
        center = (a.co + b.co) / 2
        outward = (center - edge.link_faces[0].calc_center_median()).normalized()
        tip = center + outward * rng.uniform(.002, .005)
        world_tip = obj.matrix_world @ tip
        blocked = False
        for obstacle in obstacles:
            point, normal, _, distance = obstacle.find_nearest(world_tip)
            if distance < .010 and (world_tip - point).dot(normal) < .001:
                blocked = True
                break
        if blocked:
            continue
        # Split a narrow base into the original boundary before adding a fibre.
        # Solidifying the extended sheet then gives a closed, two-manifold edge.
        _, left = bmesh.utils.edge_split(edge, a, .47)
        narrow, right = bmesh.utils.edge_split(edge, left, .06)
        loop = narrow.link_loops[0]
        vertex = bm.verts.new(tip)
        for fibre in [left, right, vertex]:
            fibre[fibre_layer] = 1
        face = bm.faces.new((loop.link_loop_next.vert, loop.vert, vertex))
        face.material_index = 0
        frays += 1
    bm.to_mesh(obj.data)
    bm.free()
    # Fibres need a thinner section than the torn wool they emerge from.
    group = obj.vertex_groups.new(name='Aging thickness')
    fibre_flags = obj.data.attributes['AgingFiber'].data
    for vertex in obj.data.vertices:
        if fibre_flags[vertex.index].value:
            weight = 0
        elif protected:
            distance = attachment_distance(obj.matrix_world @ vertex.co, protected)
            reinforced = float(np.clip((config['detail_pin_radius_m'] - distance) / .006, 0, 1))
            target_fraction = .45 + .55 * reinforced
            weight = (target_fraction - FIBRE_THICKNESS_FACTOR) / (1 - FIBRE_THICKNESS_FACTOR)
        else:
            weight = 1
        group.add([vertex.index], weight, 'REPLACE')
    solidify(obj, config['thickness_m'])
    recalc(obj)
    simulation.update({'seed': seed, 'removed_reference_area_m2': removed_area,
                       'original_midsurface_area_m2': original_area,
                       'removed_reference_fraction': removed_area / original_area,
                       'fray_triangles': frays, 'thickness_m': config['thickness_m'],
                       'cut_surface_component_areas_m2': component_areas})
    return simulation


def main():
    from build import run
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--params', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    run(args.source, json.loads(args.params.read_text()), args.output, stages={'cloth', 'debris'})


if __name__ == '__main__':
    main()
