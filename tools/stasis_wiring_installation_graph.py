"""Semantic axes derived from the same physical sweeps as the production GLB."""
import numpy as np

from stasis_wiring_assemblies import SOURCE


def graph(assembly):
    nodes, edges = [], []
    routes = {r['id']:r for r in assembly.routes}
    axes = assembly.metrics['conduit_axes_m']

    def node(name, kind, point):
        nodes.append({'id':name,'kind':kind,'position':np.asarray(point).tolist()})
        return name

    def edge(a, b, kind, points, physical):
        edges.append({'id':a+'_to_'+b,'from':a,'to':b,'class':kind,
                      'points':np.asarray(points).tolist(),'supported':True,
                      'physical_routes':physical})

    node('enclosure', 'source', SOURCE)
    for kind, count in [('power',2),('data',6)]:
        center = np.mean([routes[f'{kind}-{i+1}']['centerline_m'] for i in range(count)], axis=0)
        trunk = node(kind+'_underpanel_trunk', 'supported_trunk', center[0])
        drop = node(kind+'_floor_drop', 'wall_floor_conduit', center[-1])
        edge('enclosure', trunk, kind, [SOURCE,center[0]], ['enclosure internal bus'])
        edge(trunk, drop, kind, center, [f'{kind}-{i+1}' for i in range(count)])
        entry = np.array(axes[kind+'-floor-entry'])
        south = node(kind+'_south_distribution','hidden_floor_junction',entry[-1])
        edge(drop, south, kind, entry, [kind+'-floor-entry'])
        cross = np.array(axes[kind+'-cross-bus'])
        north = node(kind+'_north_distribution','hidden_floor_junction',cross[-1])
        edge(south, north, kind, cross, [kind+'-cross-bus'])
        for row, hub, hub_point in [('south',south,entry[-1]),('north',north,cross[-1])]:
            takeoffs = []
            for index, pod in enumerate(assembly.metrics['terminal_centers_m']):
                if (pod[2]<0)!=(row=='south'): continue
                path = np.array(axes[f'pod-{index+1}-{kind}'])
                takeoff = node(f'{kind}_bus_{index+1}','hidden_floor_takeoff',path[0])
                terminal = node(f'pod_{index+1}_{kind}_base','pod_base_terminal',path[-1])
                edge(takeoff,terminal,kind,path,[f'pod-{index+1}-{kind}'])
                takeoffs.append((takeoff,path[0]))
            # Split the actual straight row bus at its physical T takeoffs.
            stations = sorted([(hub,hub_point)]+takeoffs,key=lambda pair:pair[1][0])
            for a,b in zip(stations,stations[1:]):
                edge(a[0],b[0],kind,[a[1],b[1]],[kind+'-'+row+'-bus'])
                edge(b[0],a[0],kind,[b[1],a[1]],[kind+'-'+row+'-bus'])
        if kind=='power':
            for side in ['left','right']:
                for index in [1,2]:
                    route = routes[f'fault-{side}-power-{index}']
                    start = node(f'fault_{side}_{index}_splice','power_splice',route['start_m'])
                    end = node(f'fault_{side}_{index}_connection','retained_power_connection',route['end_m'])
                    # Source-side splice and retained-branch splice are inside
                    # their manufactured enclosures on the continuous trunk.
                    origin = trunk if side=='left' else f'fault_left_{index}_splice'
                    origin_point = next(n['position'] for n in nodes if n['id']==origin)
                    physical = [f'power-{index}'] if side=='left' else [f'fault-left-power-{index}']
                    physical_path = routes[physical[0]]['centerline_m']
                    nearest = int(np.argmin(np.linalg.norm(np.array(physical_path)-route['start_m'],axis=1)))
                    edge(origin,start,kind,physical_path[:nearest+1],physical)
                    # The power trunk node is its pair center; this short
                    # first point is inside the actual common gland enclosure.
                    edges[-1]['points'][0] = origin_point
                    edges[-1]['points'][-1] = route['start_m']
                    edge(start,end,kind,route['centerline_m'],[route['id']])
    fault = assembly.metrics['fault']
    for lead, tip in zip(fault['leads'], fault['tips']):
        side, number = lead['id'].split('-')[1:]
        connection = f'fault_{side}_{number}_connection'
        endpoint = node(tip['id'], 'exposed_power_tip', tip['end_m'])
        edge(connection, endpoint, 'power', lead['centerline_m'][1:]+[tip['end_m']], [lead['id'],tip['id']])
        edges[-1]['retained_clamp'] = lead['retained_clamp']
        edges[-1]['free_tail'] = True
    sealed = node('fault_right_2_sealed','insulated_end_cap',fault['sealed_end_axis_m'][-1])
    edge('fault_right_2_connection', sealed, 'power', fault['sealed_end_axis_m'], ['fault-right-2-seal'])
    by_node = {n['id']:n for n in nodes}
    for connection in edges:
        interfaces = []
        for endpoint in ['from','to']:
            terminal = by_node[connection[endpoint]]
            if not terminal['kind'].startswith('hidden_floor_'):
                continue
            junction = next(j for j in assembly.metrics['junctions'] if np.allclose(j['center_m'],terminal['position'],atol=1e-9,rtol=0))
            links = [link for link in assembly.metrics['junction_links'] if link['junction']==junction['id']
                and any(link['route'].startswith(route+'-') for route in connection['physical_routes'])]
            count = 2 if connection['class']=='power' else 6
            if {link['strand'] for link in links}!=set(range(1,count+1)):
                raise ValueError('graph edge lacks physical strand interfaces: '+connection['id'])
            interfaces.append(junction['id'])
        connection['junction_interfaces'] = interfaces
    return {'frame':'bay_local_y_up','nodes':nodes,'edges':edges,
        'junction_interfaces':assembly.metrics['junction_links'],
        'overhead_splice_interfaces':assembly.metrics['overhead_splice_links'],'fault':{
        'id':'lower_seat_break_4_4','opening_cell':[4,4],'opening_center':[-.6,2.99,-.9],
        'seat_center':[-.6,2.988,-.6],'carrier_z':-.6,'carrier_centerline_y':3.12,
        'upper_carriers_intact':True,'fragment_roll_degrees':115.0,
        'connection_endpoints':assembly.metrics['fault_connection_endpoints_m'],
        'power_tip_positions':[t['end_m'] for t in fault['tips']], 'tips':fault['tips'],
        'released_leads':fault['leads'],'sealed_connection':fault['sealed_connection'],
        'all_tips_power_only':True,'released_cores_and_sparks_installed':True}}
