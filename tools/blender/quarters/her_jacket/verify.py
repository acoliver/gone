"""Independent game-space clothing gates, including exact collider triangle tests."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import trimesh

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
ASSETS=ROOT/'assets/props/quarters'
SCRATCH=ROOT/'tmp/clothes'
spec=importlib.util.spec_from_file_location('bed_verification',HERE.parent/'bed_soft/verify.py')
bed_verification=importlib.util.module_from_spec(spec)
spec.loader.exec_module(bed_verification)
crossings=bed_verification.crossings


def load(path):
    scene=trimesh.load(path,force='scene')
    meshes={}
    for node in scene.graph.nodes_geometry:
        transform,key=scene.graph[node]
        obj=scene.geometry[key].copy();obj.apply_transform(transform)
        ancestors=[node];current=node
        while current in scene.graph.transforms.parents:
            current=scene.graph.transforms.parents[current];ancestors.append(current)
        parent=next((n for n in ancestors if n in ('Jacket','RoseDress','BlueDress')),node)
        meshes.setdefault(parent,[]).append(obj)
    return scene,{name:trimesh.util.concatenate(parts) for name,parts in meshes.items()}


def near_gap(part,support):
    points=np.vstack([part.vertices,part.triangles_center])
    _,distance,_=trimesh.proximity.closest_point(support,points)
    return float(distance.min())


def support_pass(gaps):
    return bool(gaps and all(0<=gap<=.003 for gap in gaps.values()))


def tunic(state):
    _,parts=load(ASSETS/f'dress_uniform{"_aged" if state=="aged" else ""}.glb')
    fragments=[];hanging=[]
    for name,part in parts.items():
        part.vertices[:,0]*=-1
        part.vertices[:,2]+=.003038027
        (fragments if name.startswith(('FallenHem','FibreDust','HeapFibres')) else hanging).append(part)
    result=[]
    for part in hanging:
        part.vertices[:,1]+=1.82;result.append(part)
    if fragments:
        bottom=min(p.bounds[0,1] for p in fragments)
        for part in fragments:
            part.vertices[:,1]+=.1445-bottom;result.append(part)
    return trimesh.util.concatenate(result)


def state_report(prop,state):
    path=ASSETS/f'{prop}{"_aged" if state=="aged" else ""}.glb'
    scene,parts=load(path)
    _,supports=load(ASSETS/('dining_chair.glb' if prop=='her_jacket' else 'wardrobe.glb'))
    support=trimesh.util.concatenate(list(supports.values()))
    collider={name:crossings(part,support) for name,part in parts.items()}
    count=sum(len(p.faces) for p in parts.values())
    gaps={}
    if prop=='her_jacket':
        gaps['Jacket/chair']=near_gap(parts['Jacket'],support)
        for name,part in parts.items():
            if name.startswith(('Lapel_','JacketButton_')):
                gaps[name+'/Jacket']=near_gap(part,parts['Jacket'])
        if state=='aged':
            gaps['SeatFibreDust/seat']=near_gap(parts['SeatFibreDust'],supports['SeatPad'])
            gaps['FloorFibreDust/floor']=float(parts['FloorFibreDust'].bounds[0,1])
    else:
        for name in ('RoseDress','BlueDress'):
            hanger=parts[name+'_Hanger']
            gaps[name+'/hanger']=near_gap(parts[name],hanger)
            gaps[name+'_Hanger/rail']=near_gap(hanger,supports['Rail'])
            if state=='aged':gaps[name+'_FibreHeap/shelf']=near_gap(parts[name+'_FibreHeap'],supports['BottomPanel'])
    source_record=json.loads((HERE.parent/prop/f'{state}.json').read_text())
    native=np.asarray(source_record['bounds_blender_native_m'])
    expected=np.array([[native[0,0],native[0,2],-native[1,1]],
                       [native[1,0],native[1,2],-native[0,1]]])
    axes=bool(np.allclose(scene.bounds,expected,atol=2e-6))
    repeat=SCRATCH/f'{prop}-{state}-repeat.glb'
    primary=('Jacket',) if prop=='her_jacket' else ('RoseDress','BlueDress')
    origins={name:scene.graph[name][0][:3,3].tolist() for name in primary}
    record={'triangles':count,'triangle_limit':6000 if prop=='her_jacket' else 10000,
            'collider_triangle_crossings':collider,'support_gaps_m':gaps,
            'support_limit_m':.003,'bounds_gltf_m':scene.bounds.tolist(),
            'part_bounds_gltf_m':{n:p.bounds.tolist() for n,p in parts.items()},
            'byte_identical_reexport':path.read_bytes()==repeat.read_bytes() if repeat.exists() else False,
            'axes_y_up_front_z':axes,'axis_bounds_max_error_m':float(np.abs(scene.bounds-expected).max()),
            'degenerate_triangles':{n:int(np.count_nonzero(p.area_faces<1e-12)) for n,p in parts.items()},
            'origins_gltf_m':origins}
    if prop=='her_dresses':
        other=tunic(state)
        record['tunic_triangle_crossings']={n:crossings(p,other) for n,p in parts.items()}
        record['dress_pair_crossings']=crossings(parts['RoseDress'],parts['BlueDress'])
        record['tunic_transform']='wardrobe-local X reflection; hook [0,1.82,0.003038027]; debris separately seated at shelf+0.5mm, as issue-114 demo'
    record['pass']=bool(count<=record['triangle_limit'] and not sum(collider.values())
                        and support_pass(gaps) and axes and record['byte_identical_reexport']
                        and not sum(record['degenerate_triangles'].values())
                        and all(np.allclose(p,[0,0,0],atol=1e-8) for p in origins.values())
                        and not sum(record.get('tunic_triangle_crossings',{}).values())
                        and not record.get('dress_pair_crossings',0))
    return record


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('prop',choices=['her_jacket','her_dresses'])
    p.add_argument('--state',choices=['remembered','aged'])
    a=p.parse_args()
    states=[a.state] if a.state else ['remembered','aged']
    result={state:state_report(a.prop,state) for state in states}
    result['pass']=all(r['pass'] for r in result.values())
    out=HERE.parent/a.prop/'verify.json'
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)
    if not result['pass']:raise SystemExit('Clothing gates failed')


if __name__=='__main__':main()
