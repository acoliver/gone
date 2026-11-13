"""Measured offline proof construction in bay-local metres, +Y up.

The enclosure and ceiling panels remain external production-asset references.
No game scene is modified by this module.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image

from stasis_wiring_geometry import _frames, fillet_polyline

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/props/stasis-wiring'
# Issue 110: local +Z ports face +X along the trunk; the measured back mounts at X=-6.
SOURCE = np.array([-6-json.loads((OUT/'provenance.json').read_text())['rear_mounting_plane_local_z_m'], 2.75, -3.1])
SIDES = 24


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def minimum_radius(points):
    p = np.asarray(points)
    a, b, c = p[:-2], p[1:-1], p[2:]
    twice_area = np.linalg.norm(np.cross(b-a, c-a), axis=1)
    lengths = np.linalg.norm(b-a, axis=1)*np.linalg.norm(c-b, axis=1)*np.linalg.norm(c-a, axis=1)
    valid = twice_area > 1e-13
    return float(np.min(lengths[valid]/(2*twice_area[valid]))) if valid.any() else 1e9


def shaped_path(raw, radius=.24, step=.008):
    path = fillet_polyline(raw, radius, 256)
    distance = np.r_[0., np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
    stations = np.linspace(0, distance[-1], math.ceil(distance[-1]/step)+1)
    return np.column_stack([np.interp(stations, distance, path[:, i]) for i in range(3)])


def sweep(path, radius, normals=None, binormals=None, caps=True):
    path = np.asarray(path)
    if normals is None:
        normals, binormals = _frames(path)
    angles = np.arange(SIDES)*2*math.pi/SIDES
    rings = path[:, None, :] + radius*(normals[:, None, :]*np.cos(angles)[None, :, None] + binormals[:, None, :]*np.sin(angles)[None, :, None])
    vertices = rings.reshape(-1, 3).tolist()
    faces = []
    for j in range(len(path)-1):
        for k in range(SIDES):
            a, b = j*SIDES+k, j*SIDES+(k+1)%SIDES
            faces.extend([[a,b,a+SIDES],[b,b+SIDES,a+SIDES]])
    if caps:
        start, end = len(vertices), len(vertices)+1
        vertices.extend([path[0], path[-1]])
        for k in range(SIDES):
            nxt = (k+1)%SIDES
            faces.extend([[start,nxt,k],[end,(len(path)-1)*SIDES+k,(len(path)-1)*SIDES+nxt]])
    mesh = trimesh.Trimesh(vertices, faces, process=False)
    mesh.fix_normals()
    return mesh, rings


def annulus(path, inner, outer, normals=None, binormals=None):
    outside, _ = sweep(path, outer, normals, binormals, False)
    inside, rings = sweep(path, inner, normals, binormals, False)
    inside.invert()
    result = trimesh.util.concatenate([outside, inside])
    faces = result.faces.tolist()
    n = len(outside.vertices)
    for j in [0, len(path)-1]:
        for k in range(SIDES):
            a, b = j*SIDES+k, j*SIDES+(k+1)%SIDES
            faces.extend([[a,b,n+a],[b,n+b,n+a]])
    result = trimesh.Trimesh(result.vertices, faces, process=False)
    result.fix_normals()
    return result, rings


def box(center, size):
    mesh = trimesh.creation.box(size)
    mesh.apply_translation(center)
    return mesh


def nearest_surface(points, mesh):
    _, distances, _ = trimesh.proximity.closest_point_naive(mesh, np.asarray(points))
    return float(np.max(distances))


class Assembly:
    def __init__(self, name):
        self.name = name
        self.parts = defaultdict(list)
        self.contacts = []
        self.routes = []
        self.metrics = {}
        self.rail_meshes = {}

    def add(self, role, mesh):
        self.parts[role].append(mesh)
        return mesh

    def block(self, role, center, size):
        return self.add(role, box(center,size))

    def route(self, name, path, radius, minimum, normals=None, binormals=None):
        mesh, rings = sweep(path,radius,normals,binormals)
        self.add('jacket',mesh)
        measured = minimum_radius(path)
        # Measure each actual swept surface longitudinal, including the inner
        # bend side, rather than subtracting a nominal jacket diameter.
        surface_radius = min(minimum_radius(rings[:,i,:]) for i in range(SIDES))
        if measured < minimum-1e-4 or surface_radius < minimum-radius-.0004:
            raise ValueError(f'{name}: bend radius {measured}, jacket inner surface {surface_radius}')
        self.routes.append({'id':name,'start_m':path[0].tolist(),'end_m':path[-1].tolist(),
                            'centerline_m':path.tolist(),'jacket_od_m':radius*2,
                            'length_m':float(np.linalg.norm(np.diff(path,axis=0),axis=1).sum()),
                            'actual_mesh_bounds_m':mesh.bounds.tolist(),
                            'minimum_centerline_radius_m':measured,
                            'minimum_surface_longitudinal_radius_m':surface_radius,
                            'required_centerline_radius_m':minimum})
        return mesh,rings

    def clamp(self, name, path, radius, index, cable_mesh, normals=None, binormals=None, rail=True):
        normals,binormals = _frames(path) if normals is None else (normals,binormals)
        lo,hi = max(0,index-2),min(len(path),index+3)
        segment = path[lo:hi]
        shell, contacts = annulus(segment,radius,radius+.002,normals[lo:hi],binormals[lo:hi])
        self.add('steel_clamps',shell)
        # Only triangles in the contact neighbourhood are needed for exact
        # nearest-triangle distance, avoiding an optional spatial-index package.
        face_mask = np.all(cable_mesh.faces < len(path)*SIDES,axis=1)
        face_mask &= np.any((cable_mesh.faces >= lo*SIDES)&(cable_mesh.faces < hi*SIDES),axis=1)
        local = trimesh.Trimesh(cable_mesh.vertices,cable_mesh.faces[face_mask],process=False)
        gap = nearest_surface(contacts.reshape(-1,3),local)
        if gap > 1e-7:
            raise ValueError(f'{name}: clamp misses actual jacket by {gap}')
        self.contacts.append({'id':name,'actual_inner_surface_to_jacket_max_gap_m':gap,
                              'sample_count':int(contacts.size/3),'station_index':index,
                              'station_m':float(np.linalg.norm(np.diff(path[:index+1],axis=0),axis=1).sum()),
                              'jacket_center_m':path[index].tolist()})
        p = path[index]
        if rail:
            self.bracket(shell,p,self.contacts[-1])
        return shell

    def bracket(self,saddle,p,record):
        top=float(saddle.bounds[1,1])
        rail_z=round((p[2]+3.6)/.6)*.6-3.6
        # The drop stays in the 20 mm panel seam at the grid, while the
        # cantilever return is BELOW the panel. A drop at cable Z would
        # incorrectly pass through the retained panel body.
        # Size the bearing plate to the real saddle envelope, including bends.
        z0,z1=min(saddle.bounds[0,2],rail_z-.022),max(saddle.bounds[1,2],rail_z+.022)
        foot=self.block('steel_clamps',[(saddle.bounds[0,0]+saddle.bounds[1,0])/2,top+.006,(z0+z1)/2],
                        [max(.044,float(saddle.extents[0])+.004),.012,z1-z0])
        bottom=top+.012
        drop=self.block('steel_clamps',[p[0],(bottom+3.0925)/2,rail_z],
                        [.044,3.0925-bottom,.016])
        crown=saddle.vertices[np.argmax(saddle.vertices[:,1])]
        rail_contact=[p[0],drop.bounds[1,1],rail_z]
        crown_gap=nearest_surface([crown],foot)
        rail_gap=nearest_surface([rail_contact],self.rail_meshes[round(rail_z,3)])
        if crown_gap>1e-7 or rail_gap>1e-7: raise ValueError('support bracket misses actual saddle or rail')
        record['actual_saddle_crown_to_crossarm_gap_m']=crown_gap
        record['actual_drop_to_crossarm_gap_m']=abs(float(drop.bounds[0,1]-foot.bounds[1,1]))
        record['actual_bracket_rail_underside_gap_m']=rail_gap
        record['rail_contact_point_m']=rail_contact
        record['crossarm_panel_underside_clearance_m']=float(2.934-foot.bounds[1,1])
        record['drop_panel_seam_side_clearance_m']=float((.020-np.ptp(drop.bounds,axis=0)[2])/2)
        if record['crossarm_panel_underside_clearance_m']<=0 or record['drop_panel_seam_side_clearance_m']<=0:
            raise ValueError('bracket penetrates retained panel envelope')

    def scene(self):
        scene = trimesh.Scene()
        for role, parts in self.parts.items():
            mesh = trimesh.util.concatenate(parts)
            uv = mesh.vertices[:,[0,2]]*2
            if role in ['seat_healthy', 'seat_retained', 'fallen_fragment']:
                from seat_rail import material
                uv = np.concatenate([part.visual.uv for part in parts])
                mat = material()
            elif role == 'jacket':
                mat = trimesh.visual.material.PBRMaterial(name=role,baseColorFactor=[.018,.021,.020,1],roughnessFactor=.7,metallicFactor=0)
            elif role == 'copper':
                mat = trimesh.visual.material.PBRMaterial(name=role,baseColorFactor=[.48,.22,.08,1],roughnessFactor=.42,metallicFactor=.88)
            elif role == 'fault_insulation':
                mat = trimesh.visual.material.PBRMaterial(name=role,baseColorFactor=[.075,.030,.018,1],roughnessFactor=.7,metallicFactor=0)
            elif role == 'bands':
                mat = trimesh.visual.material.PBRMaterial(name=role,baseColorFactor=[.28,.26,.16,1],roughnessFactor=.8,metallicFactor=0)
            elif self.name in ['supported-transition-aligned', 'production-installation'] and role in ['steel_clamps','steel_pipe','metal_entry_unions', 'junction_metal']:
                mat = trimesh.visual.material.PBRMaterial(name=role,baseColorFactor=[.28,.30,.29,1],roughnessFactor=.58,metallicFactor=.75)
            else:
                scan = ROOT/'assets/surfaces/steel/r4-green_metal_rust-albedo.png'
                mat = trimesh.visual.material.PBRMaterial(name=role,baseColorTexture=Image.open(scan),baseColorFactor=[.5,.5,.5,1],roughnessFactor=.85,metallicFactor=.62)
            mesh.visual = trimesh.visual.TextureVisuals(uv=uv,material=mat)
            scene.add_geometry(mesh,node_name=role,geom_name=role)
        return scene


def with_slack(path, amount):
    result = path.copy()
    tangent = np.gradient(path,axis=0)
    straight = (np.abs(tangent[:,0]) > .003)&(np.abs(tangent[:,2])<1e-6)&(path[:,1]>2.6)
    indices = np.flatnonzero(straight)
    if len(indices) < 4:
        raise ValueError('missing straight supported span')
    first,last = indices[0],indices[-1]
    # Zero slope at each support avoids a curvature singularity at clamps.
    station_count = max(1,math.ceil((path[last,0]-path[first,0])/.5))
    anchors = np.linspace(first,last,station_count+1).round().astype(int)
    for lo,hi in zip(anchors,anchors[1:]):
        t = np.linspace(0,1,hi-lo+1)
        result[lo:hi+1,1] -= amount*16*t*t*(1-t)*(1-t)
    return result


def transition(sockets):
    from stasis_wiring_transition import transition as supported_transition
    return supported_transition(sockets)


def fault():
    assembly=Assembly('fault-frame-pair')
    from seat_rail_proof import add_seat_failure
    retained_left = add_seat_failure(assembly)
    for z in [-1.8,-1.2,0.]:
        assembly.block('steel_frame',[-.6,3.12,z],[3.6,.055,.055])
        assembly.block('steel_frame',[-.6,3.04025,z],[3.6,.1045,.016])
    for x in [-2.4,-1.2,0,1.2]:
        assembly.block('steel_frame',[x,3.12,-.9],[.055,.055,1.8])
        assembly.block('steel_frame',[x,3.04025,-.9],[.016,.1045,1.8])
        # The prototype's longitudinal flat seats butt to the formed cross
        # returns with the accepted 2 mm seam instead of overlapping sheet.
        for a,b in [(-1.777,-1.223),(-1.177,-.623),(-.577,-.023)]:
            assembly.block('steel_frame',[x,2.9865,(a+b)/2],[.036,.003,b-a])
    # Issue 110 user correction: only the lower formed seat detaches.
    # Both the 16 mm web and the separate upper carrier stay continuous.
    assembly.block('steel_frame',[-.6,3.04025,-.6],[3.6,.1045,.016])
    tip_points=[]
    for cable,x in enumerate([-1.30,-1.24]):
        # A bounded, stiff hanging span; the supported origin stays on the
        # surviving rail rather than terminating in the missing metre.
        t=np.linspace(0,1,161)[:,None]
        controls=np.array([[x,2.88,-.57],[x+.005,2.69,-.57],
                           [x+.13,2.60,-.50],[x+.13,2.42-cable*.035,-.50]])
        path=(1-t)**3*controls[0]+3*(1-t)**2*t*controls[1]+3*(1-t)*t*t*controls[2]+t**3*controls[3]
        mesh,_=assembly.route(f'fault-power-{cable+1}',path,.012,.144)
        clamp=assembly.clamp(f'fault-retained-clamp-{cable+1}',path,.012,3,mesh,rail=False)
        p=path[3]
        back=float(clamp.bounds[0,2])
        arm=assembly.block('steel_clamps',[p[0],p[1],(-.6+back)/2],[.04,.04,back+.6])
        bottom=arm.bounds[1,1]
        drop=assembly.block('steel_clamps',[p[0],(bottom+3.0925)/2,-.6],[.04,3.0925-bottom,.016])
        clamp_contact=clamp.vertices[np.argmin(clamp.vertices[:,2])]
        actual_contact=nearest_surface([clamp_contact],arm)
        rail_contact=nearest_surface([[p[0],drop.bounds[1,1],-.6]],retained_left)
        if max(actual_contact,rail_contact)>1e-7: raise ValueError('fault support misses actual clamp or retained rail')
        assembly.contacts[-1].update({'actual_clamp_back_to_arm_gap_m':actual_contact,
            'actual_arm_to_drop_gap_m':abs(float(arm.bounds[1,1]-drop.bounds[0,1])),
            'actual_drop_to_retained_rail_gap_m':rail_contact})
        for core in range(2 if cable==0 else 1):
            center=path[-1]+np.array([(core-.5)*.008 if cable==0 else 0,0,0])
            end=center+[0,-.004,0]
            assembly.add('copper',sweep(np.array([center,end]),.0016)[0])
            tip_points.append(end.tolist())
        assembly.metrics[f'fault_power_{cable+1}_vertical_drop_m']=float(path[0,1]-path[-1,1])
    data_path=np.column_stack([np.linspace(-1.75,.55,501),np.full(501,2.86),np.full(501,-1.8)])
    n,b=_frames(data_path)
    data_meshes=[]
    for strand in range(6):
        center=data_path+.0064*(n*math.cos(strand*math.pi/3)+b*math.sin(strand*math.pi/3))
        data_meshes.append(assembly.route(f'fault-retained-data-{strand+1}',center,.003,.048)[0])
    for index in range(25,500,54):
        band,_=annulus(data_path[index-1:index+2],.0094,.0104,n[index-1:index+2],b[index-1:index+2])
        assembly.add('bands',band)
        p=data_path[index]
        top=band.bounds[1,1]
        drop=assembly.block('steel_clamps',[p[0],(top+3.0925)/2,-1.8],[.02,3.0925-top,.016])
        crown=band.vertices[np.argmax(band.vertices[:,1])]
        gap=nearest_surface([crown],drop)
        jacket_gap=0.
        for mesh in data_meshes:
            ring=mesh.vertices[index*SIDES:(index+1)*SIDES]
            radial=ring.mean(axis=0)-p
            jacket_crown=ring[np.argmax((ring-p)@radial)]
            jacket_gap=max(jacket_gap,nearest_surface([jacket_crown],band))
        if max(gap,jacket_gap)>1e-7: raise ValueError('fault data tie is unsupported or misses jacket')
        assembly.contacts.append({'id':f'fault-data-tie-{index}',
            'actual_tie_to_drop_gap_m':gap,'actual_all_six_jacket_crowns_to_tie_max_gap_m':jacket_gap,
            'actual_drop_to_rail_gap_m':abs(float(drop.bounds[1,1])-3.0925)})
    assembly.metrics['power_core_tips_m']=tip_points
    assembly.metrics['power_core_exposed_length_m']=.004
    assembly.metrics['opening_cell']=[4,4]
    assembly.metrics['opening_center_m']=[-.6,2.99,-.9]
    assembly.metrics['fragment_has_cable_attachment']=False
    return assembly


def physical_route_graph(routes):
    graph={'nodes':{},'edges':[],'source_feed_pairs':[], 'source_sockets':{},
           'source_frame':{'position_m':SOURCE.tolist(),'rotation_y_degrees':90.0}}
    for route in routes:
        graph['source_sockets'][route['id']]={'socket_id':route['source_socket'],
            'center_world_m':route['source_socket_world_m'],'axis_world':route['source_axis_world']}
        points=route['centerline_m']
        indices=[0,route['conduit_entry_index'],len(points)-1]
        ids=[route['id']+suffix for suffix in [':gland-padding',':conduit-inlet',':underfloor-proof-boundary']]
        for name,index in zip(ids,indices): graph['nodes'][name]=points[index]
        for a,b,i,j in zip(ids,ids[1:],indices,indices[1:]):
            graph['edges'].append({'from':a,'to':b,'route':route['id'],'first_sample':i,'last_sample':j})
        graph['source_feed_pairs'].append([ids[0],ids[-1]])
    validate_physical_graph(graph,routes)
    return graph


def validate_physical_graph(graph,routes):
    by_id={r['id']:r for r in routes}
    outgoing=defaultdict(list)
    for edge in graph['edges']:
        if edge['from'] not in graph['nodes'] or edge['to'] not in graph['nodes']:
            raise ValueError('physical graph has a missing endpoint')
        points=by_id[edge['route']]['centerline_m']
        i,j=edge['first_sample'],edge['last_sample']
        if not 0<=i<j<len(points): raise ValueError('physical graph has an empty route section')
        if not np.array_equal(points[i],graph['nodes'][edge['from']]) or not np.array_equal(points[j],graph['nodes'][edge['to']]):
            raise ValueError('physical graph disagrees with constructed mesh endpoints')
        outgoing[edge['from']].append(edge['to'])
    for source,feed in graph['source_feed_pairs']:
        reached={source}
        frontier=[source]
        while frontier:
            for node in outgoing[frontier.pop()]:
                if node not in reached:
                    reached.add(node)
                    frontier.append(node)
        if feed not in reached: raise ValueError('disconnected physical feed: '+feed)


def build():
    OUT.mkdir(parents=True,exist_ok=True)
    sockets=json.loads((OUT/'sockets.json').read_text())
    # Missing production references are build failures, never skipped objects.
    for path in [OUT/'stasis-wiring-enclosure.glb', ROOT/'assets/props/bay-ceiling/intact.glb']:
        if not path.is_file(): raise FileNotFoundError(path)
    assemblies=[transition(sockets),fault()]
    manifest={'issue':110,'frame':'bay-local +Y up, metres','source_position_m':SOURCE.tolist(),
              'socket_manifest_sha256':digest(OUT/'sockets.json'),'assemblies':{}}
    for assembly in assemblies:
        scene=assembly.scene()
        path=OUT/(assembly.name+'.glb')
        path.write_bytes(scene.export(file_type='glb'))
        loaded=trimesh.load(path,force='scene')
        np.testing.assert_allclose(loaded.bounds,scene.bounds,atol=1e-6)
        manifest['assemblies'][assembly.name]={'glb':str(path.relative_to(ROOT)),'sha256':digest(path),
            'bounds_m':loaded.bounds.tolist(),'mesh_groups':list(assembly.parts),
            'triangles':sum(len(m.faces) for m in loaded.geometry.values()),
            'routes':assembly.routes,'contacts':assembly.contacts,'metrics':assembly.metrics}
        if assembly.name.startswith('supported-transition'):
            manifest['assemblies'][assembly.name]['physical_graph']=physical_route_graph(assembly.routes)
    (OUT/'proof-assemblies.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


if __name__=='__main__':
    manifest=build()
    print(json.dumps({name:{'bounds_m':row['bounds_m'],'metrics':row['metrics'],'triangles':row['triangles']}
                      for name,row in manifest['assemblies'].items()},indent=2))
