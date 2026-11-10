"""Verify exported small props independently of Blender, including saved-source repeats."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
import trimesh

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'tools/blender/quarters/wardrobe'))
from verify_common import welded, uv_report


def topology(mesh):
    mesh=welded(mesh)
    parts=mesh.split(only_watertight=False,repair=False)
    # Face-normal probes work for intentionally hollow cup/boot interiors too.
    # Bounding-box-to-centre probes incorrectly classify those cavities as holes.
    misses=0; probes=0
    for part in parts:
        step=max(float(part.extents.max())*1e-5,1e-7)
        indices=np.arange(len(part.faces))[::max(1,len(part.faces)//128)]
        centers=part.triangles_center[indices]
        normals=part.face_normals[indices]
        starts=centers+normals*step
        hits, rays, _=part.ray.intersects_location(starts,-normals,multiple_hits=False)
        good=np.unique(rays[np.linalg.norm(np.asarray(hits).reshape(-1,3)-starts[rays],axis=1)<step*2])
        misses+=len(indices)-len(good); probes+=len(indices)
    return {'closed':bool(mesh.is_watertight),'winding':bool(mesh.is_winding_consistent),
            'positive_shells':bool(parts and all(p.volume>0 for p in parts)),
            'shells':len(parts),'inward_probes':probes,'missed_probes':misses,
            'pass':bool(mesh.is_watertight and mesh.is_winding_consistent and
                        parts and all(p.volume>0 for p in parts) and misses==0)}


def load(path):
    import struct
    data=Path(path).read_bytes()
    json_size=struct.unpack_from('<I',data,12)[0]
    document=json.loads(data[20:20+json_size])
    original_nodes={node['name'] for node in document['nodes']}
    scene=trimesh.load(path,force='scene',process=False)
    grouped={}
    for node in scene.graph.nodes_geometry:
        transform,geometry=scene.graph[node]
        mesh=scene.geometry[geometry].copy(); mesh.apply_transform(transform)
        # trimesh splits glTF material primitives into random-suffixed child nodes.
        # Reassemble the actual exported shell before topology/identity checks.
        name=node if node in original_nodes else scene.graph.transforms.parents[node]
        grouped.setdefault(name,[]).append(mesh)
    meshes={}
    for name,parts in grouped.items():
        parts.sort(key=lambda mesh: mesh.visual.material.name.removesuffix('_Aged'))
        if len(parts)>1:
            combined=trimesh.util.concatenate(parts)
            # Concatenation otherwise atlas-packs unlike materials and replaces
            # untextured clean primitives' UVs with zeroes. Preserve exported UVs.
            combined.visual=trimesh.visual.texture.TextureVisuals(
                uv=np.vstack([part.visual.uv for part in parts]),material=parts[0].visual.material)
            meshes[name]=combined
        else:
            meshes[name]=parts[0]
    return scene,meshes


def dust_difference(aged, control):
    from PIL import Image
    def linear(path):
        rgb=np.asarray(Image.open(path).convert('RGB'),dtype=float)/255
        return np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
    difference=np.mean(np.abs(linear(aged)-linear(control)),axis=2)
    mean=float(difference.mean())
    fraction=float(np.mean(difference>.01))
    return {'mean_absolute_linear_rgb':mean,'pixels_above_0_01_fraction':fraction,
            'minimum_mean':.001,'minimum_changed_fraction':.01,
            'pass':mean>.001 and fraction>.01}


def check(item):
    folder=ROOT/'tools/blender/quarters'/item
    spec=json.loads((folder/'construction.json').read_text())
    design=json.loads((ROOT/'docs/art/quarters/prompts/batch3.json').read_text())
    target=np.array(next(x['size_whd_m'] for x in design['items'] if x['id']==item))
    result={'item':item,'states':{},'design_size_whd_m':target.tolist()}
    all_meshes={}
    for state,suffix in [('remembered',''),('aged','_aged')]:
        path=ROOT/f'assets/props/quarters/{item}{suffix}.glb'
        repeat=ROOT/f'tmp/small/{item}/{state}-repeat.glb'
        scene,meshes=load(path)
        all_meshes[state]=meshes
        joined=trimesh.util.concatenate(list(meshes.values()))
        count=sum(len(m.faces) for m in meshes.values())
        size_ok=bool(np.all(np.abs(joined.extents-target)<=np.maximum(.005,target*.10)))
        if item=='boots' and state=='aged':
            size_ok=bool(np.all(np.abs(joined.extents[[0,2]]-target[[0,2]])<=target[[0,2]]*.10))
        topo={name:topology(mesh) for name,mesh in meshes.items()}
        expected=np.asarray(spec['bounds_gltf'])
        bound_error=float(np.max(np.abs(joined.bounds-expected)))
        root,_=scene.graph[item]
        origin_ok=bool(np.allclose(root,np.eye(4),atol=1e-7) and abs(joined.bounds[0,1])<.001)
        center_ok=bool(np.max(np.abs(joined.bounds[:,[0,2]].mean(axis=0)))<.001)
        if item=='boots' and state=='aged':
            # The boot upper changes shape; the untouched sole fixes floor and footprint.
            soles=trimesh.util.concatenate([mesh for name,mesh in meshes.items() if name.startswith('Sole_')])
            _,clean=load(ROOT/f'assets/props/quarters/{item}.glb')
            oldsoles=trimesh.util.concatenate([mesh for name,mesh in clean.items() if name.startswith('Sole_')])
            bounds_ok=bool(np.allclose(soles.bounds,oldsoles.bounds,atol=1e-7) and joined.bounds[1,1]<expected[1,1])
        else:
            bounds_ok=bound_error<.001
        # The dedicated print UV covers the full photograph. All other parts use
        # the common no-overlap, equal-density packing; print UV is checked separately.
        uv_meshes={n:m for n,m in meshes.items() if n!='PhotoPlate'}
        uv=uv_report(uv_meshes)
        degenerate=sum(int(np.sum(m.area_faces<1e-12)) for m in meshes.values())
        identical=path.read_bytes()==repeat.read_bytes()
        state_result={'bounds_gltf_m':joined.bounds.tolist(),'max_bounds_delta_m':bound_error,
                      'bounds_pass':bounds_ok,'design_size_pass':size_ok,'base_origin_pass':origin_ok,'base_center_pass':center_ok,
                      'root_matrix':root.tolist(),'triangles':count,'triangle_limit':spec['triangle_limit'],
                      'topology':topo,'degenerate_faces':degenerate,'uv':uv,
                      'byte_identical_reexport':identical,
                      'required_parts_pass':set(spec['required_nodes'])==set(meshes)}
        state_result['pass']=bool(bounds_ok and size_ok and origin_ok and center_ok and
            count<=spec['triangle_limit'] and all(t['pass'] for t in topo.values()) and
            degenerate==0 and uv['pass'] and identical and state_result['required_parts_pass'])
        result['states'][state]=state_result
    a,b=all_meshes['remembered'],all_meshes['aged']
    same_geometry=all(np.array_equal(a[n].vertices,b[n].vertices) and np.array_equal(a[n].faces,b[n].faces) for n in a)
    result['rigid_geometry_identical']=same_geometry
    result['axis_contract']=spec['axis_contract']
    images=ROOT/'docs/art/quarters/sheets'/item
    result['dust_visibility']=dust_difference(images/'aged/hero.png',images/'dust-disabled-control/hero.png')
    result['pass']=all(s['pass'] for s in result['states'].values()) and (same_geometry or item=='boots') and result['dust_visibility']['pass']
    (folder/'verify.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'item':item,'pass':result['pass'],'triangles':{s:v['triangles'] for s,v in result['states'].items()},
                      'states':{s:{k:v[k] for k in ('bounds_pass','base_origin_pass','base_center_pass','uv','byte_identical_reexport')} for s,v in result['states'].items()}},indent=2))
    if not result['pass']:
        failures={s:{n:t for n,t in r['topology'].items() if not t['pass']} for s,r in result['states'].items()}
        print('Topology failures',json.dumps(failures,indent=2))
        raise SystemExit(1)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('item')
    check(parser.parse_args().item)
