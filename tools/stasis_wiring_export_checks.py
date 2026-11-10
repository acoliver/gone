"""Physical regression checks against transformed, exported production triangles."""
import numpy as np
import trimesh

from stasis_wiring_clearance import segment_distance
from stasis_wiring_ports import port_sections, slice_path


def exported_group(scene, role):
    pieces = []
    for node in scene.graph.nodes_geometry:
        transform, name = scene.graph[node]
        if node == role or node.startswith(role+'.'):
            mesh = scene.geometry[name].copy()
            mesh.apply_transform(transform)
            pieces.append(mesh)
    if not pieces:
        raise ValueError('missing exported group: '+role)
    return trimesh.util.concatenate(pieces)


def segment_hits(mesh, paths):
    starts = np.concatenate([p[:-1] for p in paths])
    deltas = np.concatenate([np.diff(p,axis=0) for p in paths])
    lengths = np.linalg.norm(deltas,axis=1)
    nonzero = lengths>1e-9
    starts, deltas, lengths = starts[nonzero], deltas[nonzero], lengths[nonzero]
    tree = mesh.triangles_tree
    triangles = mesh.triangles
    total = 0
    for a, delta, length in zip(starts,deltas,lengths):
        end = a+delta
        bounds = np.r_[np.minimum(a,end)-1e-8,np.maximum(a,end)+1e-8]
        ids = list(tree.intersection(bounds))
        if not ids:
            continue
        tri = triangles[ids]
        e1,e2 = tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]
        h = np.cross(delta,e2)
        determinant = np.einsum('ij,ij->i',e1,h)
        valid = abs(determinant)>1e-14
        inv = np.zeros_like(determinant)
        inv[valid] = 1/determinant[valid]
        offset = a-tri[:,0]
        u = inv*np.einsum('ij,ij->i',offset,h)
        q = np.cross(offset,e1)
        v = inv*(q@delta)
        t = inv*np.einsum('ij,ij->i',e2,q)
        total += int(np.sum(valid&(u>=-1e-8)&(v>=-1e-8)&(u+v<=1+1e-8)&(t*length>1e-5)&((1-t)*length>1e-5)))
    return total



def verify_buried(scene, routes, metrics):
    steel = exported_group(scene,'steel_pipe')
    walls = exported_group(scene,'junction_metal')
    jacket = exported_group(scene,'jacket')
    # Exported jacket edges, not merely authored axes or exception volumes.
    vertices = jacket.vertices
    edges = jacket.edges_unique
    edges = edges[np.all(vertices[edges][...,1]<.15,axis=1)]
    paths = list(vertices[edges])
    pipe_hits = segment_hits(steel,paths)
    wall_hits = segment_hits(walls,paths)
    supports = exported_group(scene,'steel_clamps')
    support_hits = segment_hits(supports,paths)
    reverse_hits = {}
    buried = jacket.submesh([np.all(jacket.triangles[:,:,1]<.15,axis=1)],append=True)
    for role,mesh in [('pipe',steel),('box',walls),('support',supports)]:
        edges_other = mesh.edges_unique
        edges_other = edges_other[np.min(mesh.vertices[edges_other][...,1],axis=1)<.15]
        reverse_hits[role] = segment_hits(buried,list(mesh.vertices[edges_other]))
    if any(reverse_hits.values()):
        raise ValueError('exported foreign-wall edges penetrate buried jacket triangles: '+str(reverse_hits))
    if pipe_hits or wall_hits or support_hits:
        raise ValueError(f'exported buried jacket penetrates solid wall: pipe={pipe_hits}, box={wall_hits}, support={support_hits}')
    regression_points = [[-4.007,-.55,-3.37850010238],[-4.18,-.6564,-3.47946059664]]
    if steel.contains(regression_points).any():
        raise ValueError('review regression points remain inside exported steel')
    axis_paths = [np.array(r['centerline_m']) for r in routes if 'physical_sections_m' in r]
    axis_hits = segment_hits(steel,axis_paths)
    if axis_hits:
        raise ValueError(f'buried semantic centerline crosses exported pipe wall: {axis_hits}')
    copper = exported_group(scene,'copper')
    links = metrics['junction_links']
    _,port_gaps,_ = trimesh.proximity.closest_point(jacket,np.array([link['port_m'] for link in links]))
    _,hub_gaps,_ = trimesh.proximity.closest_point(copper,np.array([link['hub_m'] for link in links]))
    if max(port_gaps.max(),hub_gaps.max())>1e-6:
        raise ValueError('exported jacket/connector terminal contact gap exceeds one micrometre')
    groups = {}
    minimum_link_clearance = float('inf')
    for index, first in enumerate(links):
        for second in links[index+1:]:
            if first['junction']!=second['junction'] or first['strand']==second['strand']:
                continue
            gap = segment_distance(np.array([first['port_m'],first['hub_m']]),np.array([second['port_m'],second['hub_m']]))-first['radius_m']-second['radius_m']
            minimum_link_clearance = min(minimum_link_clearance,gap)
            if gap<0:
                raise ValueError(f"internal conductor short: {first['route']} / {second['route']}: {gap}")
    for link in links:
        port, hub = np.array(link['port_m']), np.array(link['hub_m'])
        # Check the exported connector center against actual closed conductor
        # triangles; the terminal cap center itself is a surface boundary.
        if not copper.contains([(port+hub)/2])[0]:
            raise ValueError('missing exported conductor link: '+link['route'])
        groups.setdefault((link['junction'],link['strand']),[]).append(link)
        route = next(r for r in routes if r['id']==link['route'])
        ends = np.array([p for section in route['physical_sections_m'] for p in [section[0],section[-1]]])
        if np.linalg.norm(ends-port,axis=1).min()>1e-8:
            raise ValueError('terminal does not meet a physical jacket end')
    for key, group in groups.items():
        if len(group)<2 or any(not np.allclose(row['hub_m'],group[0]['hub_m'],atol=1e-10) for row in group):
            raise ValueError('disconnected physical junction: '+str(key))
    return {'buried_routes':len(axis_paths),'exported_jacket_edges':len(edges),
            'pipe_triangle_intersections':pipe_hits,'box_triangle_intersections':wall_hits,'support_triangle_intersections':support_hits,
            'foreign_wall_edge_jacket_intersections':reverse_hits,
            'centerline_pipe_intersections':axis_hits,'connected_strand_junctions':len(groups),
            'exported_conductor_links':len(links),'maximum_exported_port_contact_gap_m':float(port_gaps.max()),
            'maximum_exported_hub_contact_gap_m':float(hub_gaps.max()),
            'minimum_internal_conductor_clearance_m':minimum_link_clearance,
            'review_points_in_steel':[False,False]}


def verify_overhead(scene, routes, metrics):
    # Exterior segments are clipped at real enclosure surfaces, then compared
    # continuously, including both endpoints. No inflated collision exceptions.
    boxes = []
    for junction in metrics['junctions']:
        if junction['center_m'][1]<=0:
            continue
        interior = dict(junction)
        interior['bounds_m'] = (np.array(junction['bounds_m'])+np.array([[.015]*3,[-.015]*3])).tolist()
        boxes.append(interior)
    trunk_ids = {f'{kind}-{number}' for kind,count in [('power',2),('data',6)] for number in range(1,count+1)}
    continuing = [r for r in routes if r['id'] in trunk_ids or r['id'].startswith('fault-left-power-')]
    pairs = []
    for branch in [r for r in routes if r['id'].startswith('fault-')]:
        for trunk in continuing:
            if branch['id']==trunk['id'] or (branch['id'].startswith('fault-left') and trunk['id'].startswith('fault-left')):
                continue
            a,b = np.array(branch['centerline_m']),np.array(trunk['centerline_m'])
            sections,_ = port_sections(a,boxes)
            clearance = min(segment_distance(slice_path(a,lo,hi),b)-(branch['jacket_od_m']+trunk['jacket_od_m'])/2 for lo,hi in sections)
            if clearance < -1e-6:
                raise ValueError(f"outside jacket overlap: {branch['id']} / {trunk['id']}: {clearance}")
            pairs.append({'branch':branch['id'],'continuing':trunk['id'],'surface_clearance_m':clearance})
    jackets = exported_group(scene,'jacket')
    exterior_edges = jackets.edges_unique
    exterior_edges = exterior_edges[np.all(jackets.vertices[exterior_edges][...,1]>2.7,axis=1)]
    wall_hits = segment_hits(exported_group(scene,'junction_metal'),list(jackets.vertices[exterior_edges]))
    if wall_hits:
        raise ValueError(f'overhead jacket crosses exported enclosure wall: {wall_hits}')
    points = [[-4.756292362,2.818268494,-3.084045511],[-4.750640293,2.818320525,-3.109734528]]
    components = jackets.split(only_watertight=False)
    if not all(mesh.is_watertight for mesh in components):
        raise ValueError('exported jacket component is not a closed solid')
    occupancy = [sum(bool(m.contains([p])[0]) for m in components if np.all(p>=m.bounds[0]) and np.all(p<=m.bounds[1])) for p in np.array(points)]
    if max(occupancy)>1:
        raise ValueError('review overhead points remain inside multiple exported jackets')
    links = metrics['overhead_splice_links']
    copper = exported_group(scene,'copper')
    for index,link in enumerate(links):
        points = np.array(link['centerline_m'])
        junction = next(j for j in metrics['junctions'] if j['id']==link['junction'])
        bounds = np.array(junction['bounds_m'])+np.array([[.003]*3,[-.003]*3])
        if np.any(points-link['radius_m']<bounds[0]) or np.any(points+link['radius_m']>bounds[1]):
            raise ValueError('rigid splice leaves real enclosure interior')
        if not copper.contains((points[:-1]+points[1:])/2).all():
            raise ValueError('missing exported overhead splice conductor')
        for other in links[index+1:]:
            if link['junction']==other['junction'] and segment_distance(points,np.array(other['centerline_m']))<=link['radius_m']+other['radius_m']:
                raise ValueError('overhead source splice shorts its two poles')
    return {'overhead_conductor_links':len(links),'exported_box_wall_intersections':wall_hits,'branch_to_continuing_pairs':pairs,'minimum_surface_clearance_m':min(p['surface_clearance_m'] for p in pairs),
            'review_point_closed_component_occupancy':occupancy}


def verify_export(scene, routes, metrics):
    return {'buried_junctions':verify_buried(scene,routes,metrics),
            'overhead_jackets':verify_overhead(scene,routes,metrics)}
