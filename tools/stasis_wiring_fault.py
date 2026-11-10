"""Released power cores authored at the installed retained-jacket endpoints."""
import math

import numpy as np
import trimesh

from stasis_wiring_assemblies import ROOT, SIDES, minimum_radius, nearest_surface, sweep
from stasis_wiring_clearance import segment_distance

# (side, jacket, straight reach, insulated tip height). All turns are 160 mm.
LEADS = [('left', 1, .22, 2.49), ('left', 2, .16, 2.56), ('right', 1, .14, 2.53)]
CORE_RADIUS = .004
COPPER_RADIUS = .0016
EXPOSED = .004


def taper(start, end, radii):
    path = np.array([start, end])
    mesh, rings = sweep(path, 1.)
    mesh.vertices[:2*SIDES] = (path[:, None, :] + (rings-path[:, None, :])*np.array(radii)[:, None, None]).reshape(-1, 3)
    return mesh


def add_fault(assembly):
    if 'fault' in assembly.metrics:
        raise ValueError('production fault already installed')
    routes = {r['id']: r for r in assembly.routes}
    fault = {'leads': [], 'tips': [], 'sealed_connection': 'fault-right-power-2'}
    new_meshes = []
    for side, number, reach, height in LEADS:
        connection = f'fault-{side}-power-{number}'
        jacket = routes[connection]
        origin = np.array(jacket['end_m'])
        direction = np.array([1. if side == 'left' else -1., 0., 0.])
        np.testing.assert_allclose(np.diff(jacket['centerline_m'][-2:], axis=0)[0]/
                                   np.linalg.norm(np.diff(jacket['centerline_m'][-2:], axis=0)), direction, atol=1e-8)
        radius = .16
        bend_start = origin+direction*reach
        angles = np.linspace(0, math.pi/2, 81)
        arc = bend_start+np.outer(radius*np.sin(angles), direction)
        arc[:, 1] -= radius*(1-np.cos(angles))
        end = arc[-1].copy(); end[1] = height
        path = np.vstack([origin-direction*.004, origin, arc, end])
        mesh, rings = sweep(path, CORE_RADIUS)
        measured = minimum_radius(path)
        surface = min(minimum_radius(rings[:, i]) for i in range(SIDES))
        if measured < .048-1e-4 or surface < .044-4e-4:
            raise ValueError('released core violates 6D bend setting')
        assembly.add('fault_insulation', mesh)
        boot = assembly.add('jacket', taper(origin-direction*.004, origin+direction*.026, [.0125, CORE_RADIUS]))
        copper_end = end+np.array([0., -EXPOSED, 0.])
        copper = assembly.add('copper', sweep(np.array([end, copper_end]), COPPER_RADIUS)[0])
        new_meshes.extend([mesh, boot, copper])
        contacts = [c for c in assembly.contacts if c['id'].startswith(f'fault-{side}-{number}-support-')]
        retained = max(contacts, key=lambda c: c['station_m'])
        if np.linalg.norm(np.array(retained['jacket_center_m'])-origin) > .08:
            raise ValueError('released core has no retained end clamp')
        lead_id = f'released-{side}-{number}'
        fault['leads'].append({'id': lead_id, 'connection': connection, 'class': 'power',
            'centerline_m': path.tolist(), 'insulation_radius_m': CORE_RADIUS,
            'minimum_centerline_radius_m': measured, 'minimum_inner_surface_radius_m': surface,
            'retained_clamp': retained['id'],
            'retained_clamp_contact_gap_m': retained['actual_inner_surface_to_jacket_max_gap_m'],
            'retained_clamp_distance_to_release_m': float(np.linalg.norm(np.array(retained['jacket_center_m'])-origin)),
            'jacket_to_core_axis_gap_m': float(np.linalg.norm(path[1]-origin)),
            'actual_mesh_bounds_m': mesh.bounds.tolist()})
        fault['tips'].append({'id': f'power_tip_{len(fault["tips"])+1}', 'class': 'power',
                              'lead': lead_id, 'start_m': end.tolist(), 'end_m': copper_end.tolist(),
                              'radius_m': COPPER_RADIUS, 'exposed_length_m': EXPOSED})
    origin = np.array(routes[fault['sealed_connection']]['end_m'])
    direction = np.array([-1., 0., 0.])
    cap = assembly.add('jacket', taper(origin-direction*.006, origin+direction*.018, [.013, .010]))
    new_meshes.append(cap)
    fault['sealed_end_bounds_m'] = cap.bounds.tolist()
    fault['sealed_end_axis_m'] = [origin.tolist(), (origin+direction*.018).tolist()]
    assembly.metrics['fault'] = fault
    # Retain physical pieces for independent geometry audits, never export witnesses.
    assembly.fault_meshes = new_meshes
    audit_fault(assembly, fault)


def audit_fault(assembly, fault):
    from stasis_wiring_production import CONTEXT, triangle_box_intersects
    import json

    if len(fault['tips']) != 3 or [t['id'] for t in fault['tips']] != ['power_tip_1', 'power_tip_2', 'power_tip_3']:
        raise ValueError('fault requires the three specific power tips')
    for tip in fault['tips']:
        if tip['class'] != 'power' or abs(np.linalg.norm(np.subtract(tip['end_m'], tip['start_m']))-EXPOSED) > 1e-9:
            raise ValueError('power tips must expose exactly 4 mm copper')
    context = json.loads(CONTEXT.read_text())
    meshes = assembly.fault_meshes
    for mesh in meshes:
        if not mesh.is_watertight or not mesh.is_winding_consistent:
            raise ValueError('released fault mesh is not a closed solid')
        for service in context['services']:
            bounds = np.array(service)+np.array([[-.004]*3, [.004]*3])
            if triangle_box_intersects(mesh.triangles, bounds):
                raise ValueError('released lead intersects fixture/service reservation')
    fault['service_clearance_lower_bound_m'] = .004
    low = min(m.bounds[0, 1] for m in meshes)
    fault['standing_capsule_vertical_gap_m'] = float(low-context['player']['standing_capsule_top_m'])
    fault['get_up_camera_capsule_vertical_gap_m'] = float(low-context['player']['get_up_envelope_top_m'])
    if min(fault['standing_capsule_vertical_gap_m'], fault['get_up_camera_capsule_vertical_gap_m']) <= .003:
        raise ValueError('released leads enter camera/capsule/get-up envelope')
    for i, lead in enumerate(fault['leads']):
        for other in fault['leads'][i+1:]:
            if segment_distance(np.array(lead['centerline_m']), np.array(other['centerline_m'])) < 2*CORE_RADIUS+.002:
                raise ValueError('released insulated cores touch')
    # Rotated native lid vertices at interval endpoints, expanded by the
    # maximum arc/chord error, enclose every intermediate triangle position.
    scene = trimesh.load(ROOT/'assets/props/pod/pod-v4.glb', force='scene')
    lids = []
    for node in scene.graph.nodes_geometry:
        if not node.startswith(('PodLid', 'WindowPane')):
            continue
        transform, name = scene.graph[node]
        lids.append(trimesh.transform_points(scene.geometry[name].vertices, transform))
    vertices = np.concatenate(lids)
    pivot = np.array([0., .437, -1.17250931263])
    local = vertices-pivot
    angles = np.linspace(0, -math.radians(67.7295), 137)
    error = np.linalg.norm(local[:, 1:], axis=1).max()*(1-math.cos(abs(angles[1])/2))
    margin = .004
    checked = 0
    minimum_box_gap = math.inf
    for pod in context['pods']:
        yaw = pod['yaw']
        rotate = np.array([[math.cos(yaw), 0., math.sin(yaw)], [0., 1., 0.], [-math.sin(yaw), 0., math.cos(yaw)]])
        poses = []
        for angle in angles:
            around_x = trimesh.transformations.rotation_matrix(angle, [1, 0, 0])
            points = trimesh.transform_points(local, around_x)+pivot
            poses.append(points@rotate.T+pod['position'])
        for first, second in zip(poses, poses[1:]):
            bounds = np.array([np.minimum(first.min(axis=0), second.min(axis=0)),
                               np.maximum(first.max(axis=0), second.max(axis=0))])
            bounds += np.array([[-error-margin]*3, [error+margin]*3])
            for mesh in meshes:
                gap = np.maximum(np.maximum(bounds[0]-mesh.bounds[1], mesh.bounds[0]-bounds[1]), 0.)
                minimum_box_gap = min(minimum_box_gap, float(np.linalg.norm(gap)))
                if triangle_box_intersects(mesh.triangles, bounds):
                    raise ValueError('released fault intersects conservative complete lid arc')
            checked += 1
    fault.update({'lid_count': len(context['pods']), 'lid_arc_intervals_per_pod': len(angles)-1,
                  'lid_arc_intervals_checked': checked, 'lid_arc_chord_error_bound_m': float(error),
                  'full_lid_arc_clearance_lower_bound_m': margin,
                  'minimum_expanded_lid_box_separation_m': minimum_box_gap,
                  'clearance_method': 'actual fault triangles versus complete native lid interval boxes with chord-error bound; native service AABBs; continuous vertical camera/capsule envelope'})


def verify_exported_tips(scene, fault):
    copper = []
    for node in scene.graph.nodes_geometry:
        if not node.startswith('copper'):
            continue
        transform, name = scene.graph[node]
        mesh = scene.geometry[name].copy()
        mesh.apply_transform(transform)
        mesh.merge_vertices()
        copper.extend(part for part in mesh.split(only_watertight=False) if 0 < part.bounds[0, 1] and part.bounds[1, 1] < 2.7)
    if len(copper) != 3:
        raise ValueError('export must contain exactly three exposed copper solids')
    for tip in fault['tips']:
        expected = np.array([np.array(tip['end_m'])-[COPPER_RADIUS, 0., COPPER_RADIUS],
                             np.array(tip['start_m'])+[COPPER_RADIUS, 0., COPPER_RADIUS]])
        matching = [mesh for mesh in copper if np.allclose(mesh.bounds, expected, atol=1e-6, rtol=0)]
        if len(matching) != 1 or not matching[0].is_watertight:
            raise ValueError('exported 4 mm tip position/length mismatch: '+tip['id'])
    return {'exposed_copper_solids': 3, 'length_m': EXPOSED, 'export_tolerance_m': 1e-6}
