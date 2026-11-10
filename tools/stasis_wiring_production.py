"""Baked issue-110 installation, measured against the native bay and pod export.

No carrier, panel, floor or pod is copied into this asset. Support witness meshes
are read from the production ceiling and discarded after the contact audit.
"""
import json
import math

import numpy as np
import trimesh

from stasis_wiring_assemblies import (ROOT, OUT, SIDES, annulus, box,
                                     nearest_surface, shaped_path)
from stasis_wiring_geometry import _frames
from stasis_wiring_transition import transition, stations, reduce_straights

CONTEXT = ROOT/'tmp/verify-stasis-wiring/production-install/context.json'
DROP_X = (-4.02, -4.18)


def measure_pods():
    scene = trimesh.load(ROOT/'assets/props/pod/pod-v4.glb', force='scene')
    base, lids = [], []
    for node in scene.graph.nodes_geometry:
        transform, name = scene.graph[node]
        mesh = scene.geometry[name].copy()
        mesh.apply_transform(transform)
        (base if node.startswith('PodBase') else lids if node.startswith(('PodLid', 'WindowPane')) else []).append(mesh)
    base = trimesh.util.concatenate(base)
    vertices = np.concatenate([m.vertices for m in lids])
    pivot = np.array([0., .437, -1.17250931263])
    p = vertices-pivot
    angle = math.radians(67.7295)
    candidates = [vertices[:, 1], pivot[1]+p[:, 1]*math.cos(angle)+p[:, 2]*math.sin(angle)]
    critical = np.arctan2(-p[:, 2], p[:, 1])
    in_sweep = (critical>=-angle)&(critical<=0)
    candidates.append(np.where(in_sweep, pivot[1]+np.hypot(p[:, 1], p[:, 2]), -np.inf))
    return {'base':base, 'base_bounds_m':base.bounds.tolist(),
            'interpod_gap_m':float(1.4-base.extents[0]),
            'gap_interval_m':[-4.8+float(base.bounds[1, 0]), -3.4+float(base.bounds[0, 0])],
            'full_lid_sweep_max_y_m':float(np.max(candidates))}


def compact_path(raw, radius=.26, pitch=.48):
    path = shaped_path(raw, radius=radius, step=.012)
    d = stations(path)
    fixed = [int(np.argmin(abs(d-s))) for s in np.linspace(.025, d[-1]-.025, max(2, math.ceil(d[-1]/pitch)+1))]
    keep = reduce_straights(path, fixed)
    lookup = {old:new for new,old in enumerate(keep)}
    return path[keep], [lookup[i] for i in sorted(set(fixed))]


def rail_witnesses(assembly, context):
    for z in np.arange(-3.6, 3.61, .6):
        pieces = []
        for row in context['supports']:
            bounds = np.array(row['bounds'])
            if row['path'].endswith('SupportedCrossRails') and abs(bounds.mean(axis=0)[2]-z)<1e-5:
                pieces.append(box(bounds.mean(axis=0), np.ptp(bounds, axis=0)))
        assembly.rail_meshes[round(float(z), 3)] = trimesh.util.concatenate(pieces)


def junction(assembly, name, center, size=(.15, .10, .16)):
    # Folded boxes have bounded ports, including separate trunk/takeoff exits.
    # Cables enter openings rather than disappearing through sheet metal.
    p = np.array(center)
    size = np.array(size)
    panels, ports = [], []
    for side in [-1, 1]:
        panels.append(assembly.block('junction_metal', p+[0,side*(size[1]-.003)/2,0], [size[0],.003,size[2]]))
        for normal, along in [(0,2),(2,0)]:
            openings = [(-.042,.042)]
            if name=='source-power-branch' and normal==0:
                openings = [(-.032,.032)]+([(.042,.114)] if side==1 else [])
            cursor = -size[along]/2
            for lo, hi in openings+[(size[along]/2,size[along]/2)]:
                extent = size.copy(); extent[normal] = .003
                extent[along] = lo-cursor
                shift = np.zeros(3); shift[normal] = side*(size[normal]-.003)/2
                shift[along] = (cursor+lo)/2
                panels.append(assembly.block('junction_metal', p+shift, extent))
                if hi>lo:
                    ports.append({'normal_axis':normal,'side':side,'along_axis':along,'interval_m':[lo,hi]})
                cursor = hi
    # Select the actual horizontal top sheet, regardless of face ordering.
    top = max((part for part in panels if part.extents[1]<.004), key=lambda part:part.bounds[1,1])
    record = {'id':name+'-mount','support_id':'production-cross-carrier' if p[1]>0 else 'production-floor-slab-underside'}
    if p[1]>0:
        assembly.bracket(top, p, record)
    else:
        y = top.bounds[1,1]
        stem = assembly.block('steel_clamps', [p[0],(y-.2)/2,p[2]], [.024,-.2-y,.024])
        record['actual_box_top_to_stem_gap_m'] = nearest_surface([[p[0],y,p[2]]], stem)
        record['actual_stem_to_floor_gap_m'] = abs(float(stem.bounds[1,1]+.2))
    assembly.contacts.append(record)
    assembly.metrics.setdefault('junctions', []).append({'id':name,'center_m':p.tolist(),
        'size_m':size.tolist(), 'bounds_m':np.array([p-size/2,p+size/2]).tolist(),
        'ports':ports})


def supported_fault_branch(assembly):
    from stasis_wiring_assemblies import sweep
    from stasis_wiring_clearance import segment_distance

    trunk = [r for r in assembly.routes if r['id'] in ['power-1', 'power-2']]
    starts = []
    for source in trunk:
        points = np.array(source['centerline_m'])
        starts.append(points[np.argmin(abs(points[:,0]+4.85))])
    start = np.mean(starts,axis=0)
    # Distinct +Z output ports are already separated from every continuing
    # jacket at the enclosure face. Only rigid internal links make the split.
    output = start+np.array([0.,0.,.075])
    left, left_supports = compact_path([output,[-4.55,2.82,output[2]],[-4.55,2.82,-.6],[-1.15,2.82,-.6]])
    splice_index = int(np.argmin(abs(left[:,2]+1.8)))
    splice = left[splice_index]
    right, right_supports = compact_path([splice,[.35,2.82,splice[2]],[.35,2.82,-.6],[-.05,2.82,-.6]])
    endpoints = []
    for side, center, support_indices in [('left',left,left_supports),('right',right,right_supports)]:
        tangent = np.gradient(center,axis=0)
        tangent /= np.linalg.norm(tangent,axis=1)[:,None]
        n = np.array([0.,1.,0.])-tangent*tangent[:,1,None]
        n /= np.linalg.norm(n,axis=1)[:,None]
        b = np.cross(tangent,n)
        centers = [center+b*.013,center-b*.013]
        if segment_distance(*centers)-.024<.001:
            raise ValueError('fault power jackets touch outside splice')
        for number,path in enumerate(centers):
            mesh,_ = assembly.route(f'fault-{side}-power-{number+1}',path,.012,.144,n,b)
            d = stations(path)
            supports = support_indices
            for count,index in enumerate(supports):
                assembly.clamp(f'fault-{side}-{number+1}-support-{count}',path,.012,index,mesh,n,b)
                assembly.contacts[-1]['support_id'] = 'production-cross-carrier'
            assembly.metrics[f'fault_{side}_{number+1}_maximum_support_pitch_m'] = float(np.diff(np.r_[0,d[supports],d[-1]]).max())
            endpoints.append(path[-1].tolist())
            if side=='right':
                # Rigid 3.2 mm copper splice links stay inside the box. The
                # 90-degree takeoff changes conductor packing here, without
                # pretending that a 24 mm flexible jacket makes a zero bend.
                origin = left[splice_index]+np.array([-.013 if number==0 else .013,0,0])
                link = np.array([origin,path[0]])
                assembly.add('copper',sweep(link,.0016)[0])
                assembly.metrics.setdefault('overhead_splice_links',[]).append({'junction':'fault-retained-end-branch',
                    'strand':number+1,'centerline_m':link.tolist(),'radius_m':.0016})
    junction(assembly,'source-power-branch',start,(.15,.10,.26))
    for number in range(2):
        origin = starts[number]
        target = np.array(next(r for r in assembly.routes if r['id']==f'fault-left-power-{number+1}')['start_m'])
        layer = np.array([0.,.025 if number==0 else -.025,0.])
        link = np.array([origin,origin+layer,target+layer,target])
        assembly.add('copper',sweep(link,.0016)[0])
        assembly.metrics.setdefault('overhead_splice_links',[]).append({'junction':'source-power-branch',
            'strand':number+1,'centerline_m':link.tolist(),'radius_m':.0016})
    junction(assembly,'fault-retained-end-branch',splice)
    assembly.metrics['fault_connection_endpoints_m'] = endpoints


def pipe_route(assembly, name, raw, kind):
    power = kind=='power'
    outer, inner = (.030, .027) if power else (.0125, .0105)
    row_bus = np.ptp(np.array(raw)[:,0])>0
    path, supports = compact_path(raw,pitch=.20 if row_bus and not power else .30)
    n, b = _frames(path)
    if name.endswith('-floor-entry'):
        # Match the accepted transition's exact downward-exit packing: +X
        # binormal, -Z normal. Transport that frame through the buried elbow.
        n, b = -b.copy(), n.copy()
    from stasis_wiring_ports import port_sections, section_meshes, terminated_jackets
    boxes = [j for j in assembly.metrics['junctions'] if j['center_m'][1]<0]
    sections, crossings = port_sections(path, boxes)
    pipe = trimesh.util.concatenate(section_meshes(path, sections, inner, outer, n, b))
    assembly.add('steel_pipe', pipe)
    support_witness = annulus(path,inner,outer,n,b)[0]
    offsets = [b*.013, -b*.013] if power else [(.0064*(n*math.cos(i*math.pi/3)+b*math.sin(i*math.pi/3))) for i in range(6)]
    terminated_jackets(assembly,name,path,offsets,sections,crossings,n,b,power)
    actual_supports = []
    distance = stations(path)
    for count, index in enumerate(supports):
        lo, hi = distance[max(0,index-2)], distance[min(len(path)-1,index+2)]
        if path[index, 1] > -.22 or not any(a<=lo and hi<=b for a,b in sections): continue
        # Lower data-row hangers rise past the power elevation. Reserve the
        # upper power crossing's 60 mm pipe plus hanger-width clearance.
        if not power and row_bus and abs(path[index,0]-DROP_X[0])<.07: continue
        actual_supports.append(index)
        shell = assembly.clamp(f'{name}-clip-{count}', path, outer, index, support_witness, n, b, rail=False)
        record = assembly.contacts[-1]
        record['support_id'] = 'production-floor-slab-underside'
        if np.ptp(np.array(raw)[:,1])>0:
            # A vertical hanger on the crown of an inclined/vertical pipe
            # would run through its bore. Mount these YZ-plane risers outboard.
            side = path[index]+np.array([outer+.002,0.,0.])
            arm = assembly.block('steel_clamps',side+[.012,0,0],[.024,.012,.024])
            foot = side+[.024,0,0]
            bottom = side[1]-.006
            stem = assembly.block('steel_clamps',[foot[0],(bottom-.2)/2,foot[2]],[.012,-.2-bottom,.024])
            record['actual_saddle_to_crossarm_gap_m'] = nearest_surface([side],shell)
            record['actual_crossarm_to_stem_gap_m'] = nearest_surface([foot+[0,-.006,0]],stem)
            crown = foot
        else:
            top = shell.bounds[1, 1]
            crown = shell.vertices[np.argmax(shell.vertices[:, 1])]
            stem = assembly.block('steel_clamps', [crown[0], (top-.2)/2, crown[2]], [.024, -.2-top, .024])
            record['actual_saddle_to_stem_gap_m'] = nearest_surface([crown],stem)
        floor = box([crown[0], -.1, crown[2]], [.1, .2, .1])
        record['actual_stem_to_slab_gap_m'] = nearest_surface([[crown[0],-.2,crown[2]]],floor)
    assembly.metrics[name+'_maximum_support_pitch_m'] = float(np.diff(np.r_[0, stations(path)[actual_supports], stations(path)[-1]]).max())
    assembly.metrics.setdefault('conduit_axes_m', {})[name] = path.tolist()
    return path


def underfloor(assembly, pods):
    for kind, x, wall_z, y in [('power', DROP_X[0], -3.93, -.55), ('data', DROP_X[1], -3.955, -.65)]:
        # Existing transition ends on the vertical axis at Y=-0.10. The
        # continuation shares its exact axis and transported strand packing.
        south_z, north_z = (-3.35,1.85) if kind=='power' else (-3.47,1.73)
        junction(assembly, kind+'-south-distribution', [x,y,south_z], (.18,.08,.18))
        junction(assembly, kind+'-north-distribution', [x,y,north_z], (.18,.08,.18))
        for index, pod in enumerate(pods):
            px, _, pz = pod['position']
            tx = px+(-.06 if kind=='power' else .06)
            bus_z = south_z if pz<0 else north_z
            junction(assembly, f'pod-{index+1}-{kind}-takeoff', [tx,y,bus_z], (.13,.08,.16))
        pipe_route(assembly, kind+'-floor-entry', [[x,-.1,wall_z],[x,y,wall_z],[x,y,south_z]], kind)
        pipe_route(assembly, kind+'-south-bus', [[-5.15,y,south_z],[-.25,y,south_z]], kind)
        pipe_route(assembly, kind+'-cross-bus', [[x,y,south_z],[x,y,north_z]], kind)
        pipe_route(assembly, kind+'-north-bus', [[-5.15,y,north_z],[-1.65,y,north_z]], kind)
        for index, pod in enumerate(pods):
            px, _, pz = pod['position']
            # Separate hidden bores within the measured stationary central
            # plinth. No above-floor branch crosses the walking gap.
            tx = px+(-.06 if kind=='power' else .06)
            bus_z = south_z if pz<0 else north_z
            pipe_route(assembly, f'pod-{index+1}-{kind}', [[tx,y,bus_z],[tx,y,pz],[tx,.08,pz]], kind)
    assembly.metrics['terminal_centers_m'] = [p['position'] for p in pods]
    assembly.metrics['terminal_power_x_offset_m'] = -.06
    assembly.metrics['terminal_data_x_offset_m'] = .06
    assembly.metrics['terminal_y_m'] = .08


def triangle_box_intersects(triangles, bounds):
    center = np.mean(bounds, axis=0)
    half = np.ptp(bounds, axis=0)/2
    t = triangles-center
    alive = np.all((t.max(axis=1)>=-half)&(t.min(axis=1)<=half), axis=1)
    t = t[alive]
    if len(t)==0: return False
    edges = np.roll(t, -1, axis=1)-t
    axes = [np.cross(edges[:,0], edges[:,1])]
    for axis in np.eye(3):
        for edge in range(3): axes.append(np.cross(edges[:,edge], axis))
    alive = np.ones(len(t), dtype=bool)
    for axis in axes:
        projection = np.einsum('nij,nj->ni', t, axis)
        radius = abs(axis)@half
        alive &= (projection.max(axis=1)>=-radius-1e-10)&(projection.min(axis=1)<=radius+1e-10)
    return bool(alive.any())


def base_margin(mesh, point):
    # Six explicit ray/triangle tests avoid the optional rtree dependency.
    distances = []
    for direction in np.r_[np.eye(3), -np.eye(3)]:
        a, b, c = np.moveaxis(mesh.triangles, 1, 0)
        e1, e2 = b-a, c-a
        h = np.cross(np.broadcast_to(direction, e2.shape), e2)
        determinant = np.einsum('ij,ij->i', e1, h)
        valid = abs(determinant)>1e-10
        inv = np.zeros_like(determinant); inv[valid] = 1/determinant[valid]
        s = point-a
        u = inv*np.einsum('ij,ij->i', s, h)
        q = np.cross(s, e1)
        v = inv*(q@direction)
        t = inv*np.einsum('ij,ij->i', e2, q)
        hits = t[valid&(u>=-1e-9)&(v>=-1e-9)&(u+v<=1+1e-9)&(t>1e-8)]
        distinct = np.unique(np.round(hits,7))
        if not len(distinct) or len(distinct)%2!=1:
            raise ValueError('terminal is not inside stationary base')
        distances.append(float(hits.min()))
    return min(distances)


def audit(assembly, context, measured):
    gap = measured['gap_interval_m']
    assembly.metrics['drop_centers_m'] = [[DROP_X[0],0,-3.93],[DROP_X[1],0,-3.955]]
    for kind,count in [('power',2),('data',6)]:
        path = np.mean([r['centerline_m'] for r in assembly.routes if r['id'] in [f'{kind}-{i+1}' for i in range(count)]],axis=0)
        delta = np.diff(path,axis=0)
        lengths = np.linalg.norm(delta,axis=1)
        distance = stations(path)
        contacts = [c['supported_center_m'] for c in assembly.contacts
                    if c['id']==kind+'-entry-union-support' or c['id'].startswith(kind+'-wall-clip-')]
        contacts.append(assembly.metrics['drop_centers_m'][0 if kind=='power' else 1])
        supported_stations = []
        for point in contacts:
            t = np.clip(np.einsum('ij,ij->i',np.asarray(point)-path[:-1],delta)/(lengths*lengths),0,1)
            index = np.argmin(np.linalg.norm(path[:-1]+delta*t[:,None]-point,axis=1))
            supported_stations.append(distance[index]+t[index]*lengths[index])
        assembly.metrics[kind+'_complete_wall_conduit_maximum_support_pitch_m'] = float(np.diff(sorted(supported_stations)).max())
    # Complete hardware, including collars and wall feet, below the lid sweep.
    low_vertices = []
    for parts in assembly.parts.values():
        for mesh in parts:
            vertices = mesh.vertices
            mask = (vertices[:,1]>=0)&(vertices[:,1]<=2.64)&(vertices[:,2]<-3.7)
            if mask.any(): low_vertices.append(vertices[mask])
    low_vertices = np.concatenate(low_vertices)
    clearance = min(low_vertices[:,0].min()-gap[0],gap[1]-low_vertices[:,0].max())
    if clearance<.10: raise ValueError(f'wall drop not in measured pod gap: {clearance}')
    assembly.metrics['drop_pod_side_clearance_m'] = float(clearance)
    # Every overhead jacket is above the analytic maximum over the entire
    # lid arc, not just the frozen open pose. Wall conduits use the X gap.
    overhead = [np.array(r['actual_mesh_bounds_m'])[0,1] for r in assembly.routes if r['id'].startswith('fault-')]
    for route in assembly.routes:
        if 'conduit_entry_index' not in route: continue
        points = np.array(route['centerline_m'])[:route['conduit_entry_index']+1]
        overhead.append(float(points[:,1].min())-route['jacket_od_m']/2-.003)
    assembly.metrics['all_lid_sweep_vertical_clearance_m'] = float(min(overhead)-measured['full_lid_sweep_max_y_m'])
    # Check complete triangles against every inflated native service envelope.
    for role, parts in assembly.parts.items():
        for mesh in parts:
            for bounds in context['services']:
                bounds = np.array(bounds)+np.array([[-.003]*3,[.003]*3])
                if np.any(mesh.bounds[0]>bounds[1]) or np.any(mesh.bounds[1]<bounds[0]): continue
                if triangle_box_intersects(mesh.triangles, bounds):
                    raise ValueError(f'{role} intersects native service envelope {bounds.tolist()}')
    assembly.metrics['service_envelope_clearance_m'] = .003
    assembly.metrics['service_clearance_method'] = 'SAT against every native service AABB inflated by 3 mm; certified lower bound, not minimum distance'
    margins = [base_margin(measured['base'], np.array([x,.08,0.]))-radius
               for x,radius in [(-.06,.030),(.06,.0125)]]
    assembly.metrics['terminal_hidden_base_margin_m'] = min(margins)
    for x,radius in [(-.06,.030),(.06,.0125),(.06,.030),(-.06,.0125)]:
        for y in [.0001,.04,.08]:
            for angle in np.arange(SIDES)*2*math.pi/SIDES:
                point = np.array([x+radius*math.cos(angle),y,radius*math.sin(angle)])
                base_margin(measured['base'],point)
    assembly.metrics['hidden_bore_containment_samples_per_pod'] = 2*3*SIDES
    # Verify each generated drop ends on a retained production rail triangle.
    for record in assembly.contacts:
        if 'actual_bracket_rail_underside_gap_m' not in record: continue
        point = np.array(record['rail_contact_point_m'])
        gap = nearest_surface([point], assembly.rail_meshes[round(float(point[2]),3)])
        if gap>1e-7: raise ValueError(f'bracket misses native retained carrier: {gap}')
        record['actual_native_carrier_contact_gap_m'] = gap
        record['rail_witness'] = 'native SupportedCrossRails readback'
    assembly.metrics['pod_measurements'] = {k:v for k,v in measured.items() if k!='base'}


def build_installation():
    context = json.loads(CONTEXT.read_text())
    assembly = transition(json.loads((OUT/'sockets.json').read_text()), drop_x=DROP_X)
    del assembly.parts['steel_frame']
    # The transition's witnesses have the same rail section as production.
    # Replace them with production rail segments before adding the longer runs.
    rail_witnesses(assembly, context)
    supported_fault_branch(assembly)
    from stasis_wiring_fault import add_fault
    add_fault(assembly)
    underfloor(assembly, context['pods'])
    audit(assembly, context, measure_pods())
    assembly.name = 'production-installation'
    for record in assembly.contacts:
        for key,value in record.items():
            if key.endswith('gap_m') and value>1e-7:
                raise ValueError(f"{record['id']}: contact misses by {value}")
    for key,value in assembly.metrics.items():
        if key.endswith(('support_pitch_m','clip_pitch_m')) and value>.8:
            raise ValueError(f'{key}: support pitch exceeds 0.8 m')
    return assembly
