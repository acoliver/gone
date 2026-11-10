"""Issue 110 supported end-wall source, compact loom and shared pipe entries.

Source alignment and support ownership live here, independently of the fault
proof and the accepted retained-seat components.
"""
import json
import math

import numpy as np
import trimesh
from stasis_wiring_clearance import segment_distance

from stasis_wiring_assemblies import (Assembly, OUT, SOURCE, SIDES,
                                     annulus, box, nearest_surface, shaped_path)

ROTATION = np.array([[0., 0., 1.], [0., 1., 0.], [-1., 0., 0.]])


def socket_world(port):
    return SOURCE + ROTATION @ np.array(port['center_local_m'])


def stations(path):
    return np.r_[0., np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]


def blend(t):
    return t*t*t*(10+t*(-15+6*t))


def center_path(start, y, z, x_end, wall_z):
    # Tangent and curvature both vanish at each end of the height/side blend.
    straight = start + np.column_stack([np.linspace(0, .065, 9), np.zeros(9), np.zeros(9)])
    t = np.linspace(0, 1, 101)
    s = blend(t)
    curved = np.column_stack([straight[-1, 0]+.8*t,
                             start[1]+(y-start[1])*s,
                             start[2]+(z-start[2])*s])
    tail = shaped_path([curved[-1], [x_end, y, z], [x_end, y, wall_z],
                        [x_end, -.1, wall_z]], radius=.26, step=.012)
    path = np.concatenate([straight, curved[1:], tail[1:]])
    # Only the flat under-panel span receives slack; it ends before the
    # purposeful quarter-turn. All spans are tied to the same support stations.
    distance = stations(path)
    flat = np.flatnonzero((abs(path[:, 1]-y)<1e-10) & (abs(path[:, 2]-z)<1e-10))
    a, b = int(flat[0]), int(flat[-1])
    anchors = np.unique(np.linspace(a, b, max(2, math.ceil((distance[b]-distance[a])/.4)+1)).round().astype(int))
    maximum_sag = 0.0
    for lo, hi in zip(anchors, anchors[1:]):
        t = np.linspace(0, 1, hi-lo+1)
        # Gravity slack scales with span squared. A 45 mm straight between
        # two bends must not inherit the deflection of a 350 mm free span.
        sag = .0025*min(1., ((distance[hi]-distance[lo])/.35)**2)
        displacement = sag*16*t*t*(1-t)*(1-t)
        maximum_sag = max(maximum_sag, float(displacement.max()))
        path[lo:hi+1, 1] -= displacement
    return path, anchors, maximum_sag


def reduce_straights(path, fixed):
    """Keep bend samples and contact neighbourhoods, discard redundant straights."""
    keep = {0, len(path)-1}
    for index in fixed:
        keep.update(range(max(0, index-3), min(len(path), index+4)))
    delta = np.diff(path, axis=0)
    unit = delta/np.linalg.norm(delta, axis=1)[:, None]
    bends = np.flatnonzero(np.linalg.norm(np.diff(unit, axis=0), axis=1)>1e-7)+1
    keep.update(bends)
    keep.update(np.maximum(0, bends-1)); keep.update(np.minimum(len(path)-1, bends+1))
    # Long straight spans need no interior rings. The endpoint rings suffice.
    return np.array(sorted(keep))


def support_indices(distance, end, anchors):
    targets = list(np.arange(.16, distance[end], .36)) + [distance[end]-.035]
    indices = [int(np.argmin(abs(distance-s))) for s in targets if s>0]
    return sorted(set(indices).union(int(i) for i in anchors))


def add_tie(assembly, name, path, n, b, index, centers, meshes):
    lo, hi = max(0, index-1), min(len(path), index+2)
    tie, _ = annulus(path[lo:hi], .0094, .0104, n[lo:hi], b[lo:hi])
    assembly.add('bands', tie)
    for number, (strand, mesh) in enumerate(zip(centers, meshes)):
        radial = strand[index]-path[index]
        radial /= np.linalg.norm(radial)
        ring = mesh.vertices[index*SIDES:(index+1)*SIDES]
        crown = ring[np.argmax((ring-strand[index]) @ radial)]
        gap = nearest_surface([crown], tie)
        if gap>1e-7:
            raise ValueError(f'{name}: actual data jacket misses tie by {gap}')
        assembly.contacts.append({'id':f'{name}-strand-{number+1}',
                                  'support_id':name,
                                  'actual_jacket_crown_to_tie_gap_m':gap})
    saddle, inner = annulus(path[lo:hi], .0104, .0124, n[lo:hi], b[lo:hi])
    assembly.add('steel_clamps', saddle)
    record = {'id':name+'-frame', 'support_id':'carrier-seam-'+str(round(path[index, 2], 2)),
              'actual_tie_outer_surface_to_saddle_gap_m':nearest_surface(inner.reshape(-1, 3), tie)}
    assembly.bracket(saddle, path[index], record)
    assembly.contacts.append(record)


def entry_hardware(assembly, kind, path, n, b, begin, pipe_inner, pipe_outer):
    # One common bushing per conduit, not one unsupported sleeve per strand.
    # The metal union is behind a black entry lip on the same bore axis.
    d = stations(path)
    end = int(np.argmin(abs(d-(d[begin]+.072))))
    lip_end = int(np.argmin(abs(d-(d[begin]+.024))))
    body, _ = annulus(path[lip_end:end+1], pipe_outer, pipe_outer+.008,
                      n[lip_end:end+1], b[lip_end:end+1])
    # Polygonal hex outside, with an unchanged round through bore.
    count = (end-lip_end+1)*SIDES
    for index in range(count):
        station, side = divmod(index, SIDES)
        angle = side*2*math.pi/SIDES
        radius = (pipe_outer+.008)*math.cos(math.pi/6)/math.cos(angle % (math.pi/3)-math.pi/6)
        body.vertices[index] = path[lip_end+station]+radius*(n[lip_end+station]*math.cos(angle)+b[lip_end+station]*math.sin(angle))
    body.fix_normals()
    assembly.add('metal_entry_unions', body)
    bushing, _ = annulus(path[begin:lip_end+1], pipe_inner-.0004, pipe_outer+.003,
                         n[begin:lip_end+1], b[begin:lip_end+1])
    assembly.add('jacket', bushing)
    # This support explicitly clamps the union, then reaches the same carrier
    # seam as the other under-panel supports.
    clamp_end = min(end, lip_end+2)
    support, inner = annulus(path[lip_end:clamp_end+1], pipe_outer+.008, pipe_outer+.010,
                             n[lip_end:clamp_end+1], b[lip_end:clamp_end+1])
    # A round clamp around the hex would have gaps. Use the same hex exterior
    # for both mating surfaces, retaining a 2 mm metal strap thickness.
    for ring in range(clamp_end-lip_end+1):
        for side in range(SIDES):
            angle = side*2*math.pi/SIDES
            factor = math.cos(math.pi/6)/math.cos(angle % (math.pi/3)-math.pi/6)
            direction = n[lip_end+ring]*math.cos(angle)+b[lip_end+ring]*math.sin(angle)
            for offset, radius in [(0, pipe_outer+.010), ((clamp_end-lip_end+1)*SIDES, pipe_outer+.008)]:
                support.vertices[offset+ring*SIDES+side] = path[lip_end+ring]+radius*factor*direction
    support.fix_normals()
    assembly.add('steel_clamps', support)
    inner_points = support.vertices[(clamp_end-lip_end+1)*SIDES:]
    gap = nearest_surface(inner_points, body)
    record = {'id':kind+'-entry-union-support', 'support_id':'carrier-seam-entry-'+kind,
              'supported_center_m':path[lip_end].tolist(),
              'actual_hex_union_to_support_gap_m':gap}
    assembly.bracket(support, path[lip_end], record)
    assembly.contacts.append(record)
    seal_contact = path[lip_end]+n[lip_end]*(pipe_outer+.001)
    assembly.contacts.append({'id':kind+'-bushing-to-union', 'support_id':kind+'-entry-union',
                              'actual_bushing_to_union_face_gap_m':nearest_surface([seal_contact], body),
                              'actual_union_face_to_bushing_gap_m':nearest_surface([seal_contact], bushing)})
    return lip_end


def transition(sockets, drop_x=(-4.35, -4.70)):
    assembly = Assembly('supported-transition-aligned')
    for z in [-3.6, -3.]:
        assembly.rail_meshes[round(z, 3)] = assembly.block('steel_frame', [-4.8, 3.12, z], [2.4, .055, .055])
        assembly.block('steel_frame', [-4.8, 3.04025, z], [2.4, .1045, .016])
        assembly.block('steel_frame', [-4.8, 2.9865, z], [2.4, .003, .036])
    for x in [-6., -4.8, -3.6]:
        assembly.block('steel_frame', [x, 3.12, -3.3], [.055, .055, .655])
        edge = x!=-4.8
        inward = 1 if x==-6 else -1
        assembly.block('steel_frame', [x+inward*.004 if edge else x, 3.04025, -3.3], [.008 if edge else .016, .1045, .6])
        assembly.block('steel_frame', [x+inward*.009 if edge else x, 2.9865, -3.3], [.018 if edge else .036, .003, .6])
    ports = {p['id']:p for p in sockets['sockets']}
    all_centers = {}
    for kind, y, z, x_end, wall_z, radius, minimum in [
        ('power', 2.82, -3.10, drop_x[0], -3.93, .012, .144),
        ('data', 2.79, -3.24, drop_x[1], -3.955, .003, .048)]:
        port = ports['power-1' if kind=='power' else 'control-data']
        start = socket_world(port)-[.025, 0, 0]
        if kind=='power': start[2] = SOURCE[2]
        path, anchors, measured_sag = center_path(start, y, z, x_end, wall_z)
        assembly.metrics[kind+'_measured_sag_m'] = measured_sag
        d = stations(path)
        # The pipe begins on the straight -Z approach, before its rigid elbow.
        entry_z = -3.48 if kind=='power' else -3.57
        begin = int(np.argmin(np.linalg.norm(path-[x_end, y, entry_z], axis=1)))
        supports = support_indices(d, begin, anchors)
        wall_indices = [int(np.argmin(abs(path[:, 1]-height))) for height in [.3, .85, 1.4, 1.95, 2.45]]
        fixed = supports+wall_indices+[begin]
        fixed += [int(np.argmin(abs(d-(d[begin]+offset)))) for offset in [.024, .048, .072]]
        keep = reduce_straights(path, fixed)
        old_to_new = {old:new for new,old in enumerate(keep)}
        begin = old_to_new[begin]
        supports = [old_to_new[i] for i in supports]
        wall_indices = [old_to_new[i] for i in wall_indices]
        path = path[keep]
        d = stations(path)
        n, b = np.empty_like(path), np.empty_like(path)
        tangents = np.gradient(path, axis=0)
        tangents /= np.linalg.norm(tangents, axis=1)[:, None]
        # The two separated planar bends have exact untwisted frames. This
        # also prevents numerical frame drift from walking strands sideways
        # down a mechanically straight conduit.
        for index, tangent in enumerate(tangents):
            if abs(path[index, 0]-x_end)<1e-9:
                b[index] = [1., 0., 0.]
                n[index] = np.cross(b[index], tangent)
                n[index] /= np.linalg.norm(n[index])
            else:
                up = np.array([0., 1., 0.])
                n[index] = up-tangent*np.dot(up, tangent)
                n[index] /= np.linalg.norm(n[index])
                b[index] = np.cross(tangent, n[index])
        if kind=='power':
            s = blend(np.clip((path[:, 0]-start[0]-.065)/.8, 0, 1))
            offsets = .043-.030*s
            centers = [path+b*offsets[:, None], path-b*offsets[:, None]]
        else:
            centers = [path+.0064*(n*math.cos(i*math.pi/3)+b*math.sin(i*math.pi/3)) for i in range(6)]
        meshes = []
        for i, strand in enumerate(centers):
            # Shared transported frames on the constant-offset data loom make
            # its real jacket crowns coincide with the manufactured tie bore.
            mesh, rings = assembly.route(f'{kind}-{i+1}', strand, radius, minimum,
                                         n if kind=='data' else None, b if kind=='data' else None)
            meshes.append(mesh)
            socket = ports[f'power-{i+1}' if kind=='power' else 'control-data']
            target = socket_world(socket)
            axis = ROTATION @ np.array(socket['axis_local'])
            relative = strand[0]-target
            radial_error = np.linalg.norm(relative-axis*np.dot(relative, axis))
            bore = socket['bore_diameter_m']/2
            bore_clearance = bore-radial_error-radius
            inner = .027 if kind=='power' else .0105
            envelope = float(np.max(np.linalg.norm(rings[begin:]-path[begin:, None, :], axis=2)))
            clearance = inner*math.cos(math.pi/SIDES)-envelope
            entry_clearance = (inner-.0004)*math.cos(math.pi/SIDES)-envelope
            if min(bore_clearance, clearance, entry_clearance)<=0:
                raise ValueError(f'{kind}: jacket does not fit source, entry or conduit')
            route = assembly.routes[-1]
            route.update({'source_socket':socket['id'], 'source_socket_world_m':target.tolist(),
                          'source_axis_world':axis.tolist(), 'conduit_entry_index':begin,
                          'socket_axis_radial_error_m':float(radial_error),
                          'socket_radial_clearance_m':float(bore_clearance),
                          'minimum_conduit_inscribed_bore_clearance_m':clearance,
                          'entry_axis_tangent_dot':float(np.dot((strand[begin+1]-strand[begin])/np.linalg.norm(strand[begin+1]-strand[begin]), (path[begin+1]-path[begin])/np.linalg.norm(path[begin+1]-path[begin]))),
                          'exit_axis_dot_world_plus_x':float(np.dot((strand[1]-strand[0])/np.linalg.norm(strand[1]-strand[0]), axis))})
            if route['entry_axis_tangent_dot']<.999: raise ValueError('strand not aligned with shared pipe entry bore')
            if kind=='power':
                for number, index in enumerate(supports):
                    assembly.clamp(f'{kind}-{i+1}-saddle-{number}', strand, radius, index, mesh)
                    assembly.contacts[-1]['support_id']='carrier-seam-'+str(round(strand[index, 2], 2))
        if kind=='data':
            for number, index in enumerate(supports):
                add_tie(assembly, f'data-loom-support-{number}', path, n, b, index, centers, meshes)
        separation = min(segment_distance(a, c)-radius*2 for i,a in enumerate(centers) for c in centers[i+1:])
        if separation<(.001 if kind=='power' else .00035):
            raise ValueError(f'{kind}: strand jackets touch: {separation}')
        assembly.metrics['minimum_power_strand_surface_separation_m' if kind=='power' else 'data_minimum_strand_surface_separation_m'] = separation
        if kind=='data': assembly.metrics['data_envelope_at_bore_m'] = .0188
        all_centers[kind] = centers
        pipe_inner, pipe_outer = (.027, .030) if kind=='power' else (.0105, .0125)
        pipe_begin = entry_hardware(assembly, kind, path, n, b, begin, pipe_inner, pipe_outer)
        conduit_path = path[pipe_begin:]
        pipe, _ = annulus(conduit_path, pipe_inner, pipe_outer, n[pipe_begin:], b[pipe_begin:])
        assembly.add('steel_pipe', pipe)
        contact = path[pipe_begin+1]+n[pipe_begin+1]*pipe_outer
        union = assembly.parts['metal_entry_unions'][-1]
        assembly.contacts.append({'id':kind+'-pipe-to-union', 'support_id':kind+'-entry-union',
                                  'actual_pipe_to_union_bore_gap_m':nearest_surface([contact], union)})
        assembly.metrics[kind+'_entry_bushing_clearance_m'] = float(entry_clearance)
        # The real pipe passes vertically through y=0 and ends below the floor.
        floor_center = np.array([x_end, 0., wall_z])
        collar, collar_inner = annulus(np.array([floor_center, floor_center+[0, .018, 0]]), pipe_outer, pipe_outer+.017)
        assembly.add('steel_pipe', collar)
        pipe_gap = nearest_surface(collar_inner.reshape(-1, 3), pipe)
        floor = box([x_end, -.12, wall_z], [.2, .24, .2])
        bottom = collar.vertices[abs(collar.vertices[:, 1])<1e-10]
        floor_gap = nearest_surface(bottom, floor)
        assembly.contacts.append({'id':kind+'-floor-collar', 'support_id':'floor-y0',
                                  'actual_mesh_floor_gap_m':floor_gap,
                                  'actual_collar_inner_to_pipe_gap_m':pipe_gap,
                                  'pipe_crossing_center_m':floor_center.tolist()})
        wall_stations = []
        for number, index in enumerate(wall_indices):
            lo, hi = index-1, index+2
            clip, inner_points = annulus(path[lo:hi], pipe_outer, pipe_outer+.003, n[lo:hi], b[lo:hi])
            assembly.add('steel_clamps', clip)
            pipe_gap = nearest_surface(inner_points.reshape(-1, 3), pipe)
            p = path[index]
            mount = assembly.block('steel_clamps', [p[0], p[1], (-4+p[2]-pipe_outer-.003)/2],
                                   [pipe_outer*2, .024, p[2]-pipe_outer-.003+4])
            wall = box([p[0], p[1], -4.04], [.3, .3, .08])
            wall_contact = mount.vertices[abs(mount.vertices[:, 2]+4)<1e-10]
            clip_back = clip.vertices[np.argmin(clip.vertices[:, 2])]
            assembly.contacts.append({'id':kind+'-wall-clip-'+str(number), 'support_id':'south-wall-z-4',
                                      'supported_center_m':p.tolist(),
                                      'actual_clamp_inner_surface_to_pipe_gap_m':pipe_gap,
                                      'actual_wall_mount_mesh_gap_m':nearest_surface(wall_contact, wall),
                                      'actual_mount_to_clamp_back_surface_gap_m':nearest_surface([clip_back], mount)})
            wall_stations.append(p[1])
        pitches = np.diff([0.]+[d[i] for i in supports]+[d[begin]])
        assembly.metrics[kind+'_maximum_exposed_support_pitch_m'] = float(max(pitches))
        assembly.metrics[kind+'_maximum_wall_clip_pitch_m'] = float(max(np.diff([0.]+sorted(wall_stations)+[2.71])))
        assembly.metrics[kind+'_visible_flexible_length_m'] = float(d[begin])
        assembly.metrics[kind+'_conduit_floor_intersection_y_range_m'] = pipe.bounds[:, 1].tolist()
        assembly.metrics[kind+'_entry_center_m'] = path[begin].tolist()
        assembly.metrics[kind+'_entry_axis_world'] = ((path[begin+1]-path[begin])/np.linalg.norm(path[begin+1]-path[begin])).tolist()
    cross_clearance = min(segment_distance(a, c)-.015 for a in all_centers['power'] for c in all_centers['data'])
    if cross_clearance<.01: raise ValueError(f'power/data clearance below 10 mm: {cross_clearance}')
    assembly.metrics['minimum_power_data_surface_separation_m'] = cross_clearance
    assembly.metrics['maximum_authored_sag_m'] = .0025
    enclosure = trimesh.load(OUT/'stasis-wiring-enclosure.glb', force='scene')
    transformed = enclosure.copy()
    frame = np.eye(4); frame[:3, :3] = ROTATION; frame[:3, 3] = SOURCE
    transformed.apply_transform(frame)
    # The frozen source's four real bolt heads intersect the end-wall face.
    # Use their exported triangles, rather than treating the declared plane as
    # evidence that a smoothed casting or a fastener actually contacts it.
    wall = box([-6.04, 2.75, -3.1], [.08, .4, .5])
    for node in transformed.graph.nodes_geometry:
        transform, geometry = transformed.graph[node]
        if not node.startswith('Mount bolt head'): continue
        mesh = transformed.geometry[geometry].copy()
        mesh.apply_transform(transform)
        crossings = []
        for triangle in mesh.triangles:
            for a, c in zip(triangle, np.roll(triangle, -1, axis=0)):
                if (a[0]+6)*(c[0]+6)<0:
                    crossings.append(a+(c-a)*((-6-a[0])/(c[0]-a[0])))
        if not crossings: raise ValueError('exported source fastener does not intersect end wall')
        assembly.contacts.append({'id':node, 'support_id':'end-wall-x-6',
                                  'actual_bolt_triangle_wall_intersection_gap_m':nearest_surface(crossings, wall),
                                  'triangle_wall_intersection_count':len(crossings)})
    mount_plane = json.loads((OUT/'provenance.json').read_text())['rear_mounting_plane_local_z_m']
    assembly.metrics.update({'source_mount_back_plane_world_x_m':float(SOURCE[0]+mount_plane),
                             'source_rotation_y_degrees':90., 'source_position_m':SOURCE.tolist(),
                             'external_enclosure_actual_world_bounds_m':transformed.bounds.tolist(),
                             'source_socket_world_m':{p['id']:socket_world(p).tolist() for p in sockets['sockets']}})
    for contact in assembly.contacts:
        for key, value in contact.items():
            if key.endswith('gap_m') and value>1e-7:
                raise ValueError(f"{contact['id']}: {key}={value}")
    return assembly
