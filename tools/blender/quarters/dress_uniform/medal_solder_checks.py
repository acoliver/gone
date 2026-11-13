"""Geometric suspension checks for the #130 soldered generated ring."""
import json

import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from aging_support import components
from medal_interlink import reciprocal_interlink
from tunic_details import points


def suspension_measurements(medal):
    record = json.loads(medal['medal_frame'])
    origin, frame = np.array(record['origin']), np.array(record['frame'])
    local = np.einsum('ij,kj->ik', points(medal) - origin, frame)
    metal = {i for face in medal.data.polygons if face.material_index < 2 for i in face.vertices}
    groups = [ids for ids in components(medal) if set(ids) <= metal]
    assert len(groups) == 2, 'One soldered body/ring and one unioned bar/loop solid required'
    body, bar = sorted(groups, key=len, reverse=True)
    medal.data.calc_loop_triangles()
    faces_by_solid = []
    for indices in [body, bar]:
        selected = set(indices)
        faces = [t.vertices[:] for t in medal.data.loop_triangles if set(t.vertices) <= selected]
        faces_by_solid.append(faces)
        lookup = {i: k for k, i in enumerate(indices)}
        mesh = bmesh.new()
        verts = [mesh.verts.new(Vector(local[i])) for i in indices]
        for face in faces:
            mesh.faces.new([verts[lookup[i]] for i in face])
        assert all(edge.is_manifold for edge in mesh.edges), 'Suspension solids must be closed'
        assert all(edge.is_contiguous for edge in mesh.edges), 'Suspension winding must agree'
        assert mesh.calc_volume(signed=True) > 0, 'Suspension solids must face outward'
        mesh.free()
    eyelet = json.loads(medal['eyelet'])
    loop = eyelet['suspender_loop']
    proof = reciprocal_interlink(local, faces_by_solid[0], eyelet['ring_plane_x_m'], loop)
    bar_tree = BVHTree.FromPolygons(local.tolist(), faces_by_solid[1], all_triangles=True)
    theta = np.arange(loop['major_segments']) * 2 * np.pi / loop['major_segments']
    curve = np.asarray(loop['center_m']) + loop['radius_m'] * (np.cos(theta)[:, None] * [1, 0, 0] + np.sin(theta)[:, None] * loop['up'])
    direction = Vector((.163, .971, .171)).normalized()
    for a, b in zip(curve, np.roll(curve, -1, axis=0)):
        for fraction in [.125, .375, .625, .875]:
            start = Vector(a * (1 - fraction) + b * fraction)
            hits = 0
            while True:
                hit = bar_tree.ray_cast(start, direction)[0]
                if hit is None:
                    break
                hits += 1
                assert hits < 20, 'Measured loop ray must leave the closed solid'
                start = hit + direction * 1e-7
            assert hits % 2 == 1, 'The asserted loop centreline must lie inside the measured bar/loop solid'
    tree = BVHTree.FromPolygons(local.tolist(), faces_by_solid[0], all_triangles=True)
    samples = [tree.find_nearest(Vector(local[i]))[3] for i in bar]
    bearing = min(samples)
    assert 0 <= bearing <= .0001, ('Ring/loop bearing must remain within 0.1 mm', bearing)
    ribbon = sorted(set(range(len(local))) - metal)
    center = (local[ribbon, 0].min() + local[ribbon, 0].max()) / 2
    bar_offset = abs((local[bar, 0].min() + local[bar, 0].max()) / 2 - center)
    bounds = np.asarray(eyelet['bar_bounds_m'])
    exposed_loop = [i for i in bar if local[i, 2] < bounds[0, 2] - 1e-7]
    loop_center = (local[exposed_loop, 0].min() + local[exposed_loop, 0].max()) / 2
    assert abs(loop_center - loop['center_m'][0]) < 1e-7, 'Measured loop bounds must match the interlink proof'
    loop_offset = abs(loop_center - center)
    assert bar_offset <= .001 and loop_offset <= .001, 'Bar and loop bounds-centres must be within 1 mm of the ribbon'
    bearing_vertex = bar[int(np.argmin(samples))]
    assert local[bearing_vertex, 2] < bounds[0, 2], 'The measured bearing must be on the loop below the bar'
    tongue = local[np.array(ribbon)[-28:]]
    assert tongue[:, 1].min() >= bounds[1, 1] + .00008 - 1e-8, 'Return tongue must clear the rear of the bar'
    assert tongue[:, 2].min() > bounds[:, 2].mean(), 'Return tongue must end above the bar centre'
    return dict(proof, body_ring_connected_solid=True, body_ring_gap_m=0.,
                ring_bar_bearing_sample_upper_bound_m=float(bearing),
                bar_loop_connected_solid=True, loop_centerline_inside_measured_solid=True,
                solder_watertight=True, solder_winding_consistent=True,
                bar_bounds_center_offset_m=float(bar_offset), loop_bounds_center_offset_m=float(loop_offset),
                tongue_bounds_m=[tongue.min(0).tolist(), tongue.max(0).tolist()],
                bar_bounds_m=bounds.tolist(), wire_diameter_m=2 * loop['wire_radius_m'])


def sewn_ribbon_samples(obj):
    indices = sorted({i for face in obj.data.polygons
                      if obj.data.materials[face.material_index].name.startswith('RibbonFabric')
                      for i in face.vertices})[:64]
    assert len(indices) == 64
    selected = set(indices)
    rows = []
    positions = points(obj)
    for face in obj.data.polygons:
        if not obj.data.materials[face.material_index].name.startswith('RibbonFabric'):
            continue
        for loop in face.loop_indices:
            index = obj.data.loops[loop].vertex_index
            if index not in selected:
                continue
            rows.append(np.r_[positions[index],
                              *[obj.data.uv_layers[name].data[loop].uv[:] for name in ['DetailUV', 'BakeUV']],
                              obj.data.color_attributes['RibbonColours'].data[loop].color[:]])
    return np.unique(np.array(rows), axis=0)
