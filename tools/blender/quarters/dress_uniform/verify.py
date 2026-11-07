"""Verify the exported tunic GLB using trimesh, including a deterministic re-export."""
import hashlib
import json
import math
import subprocess
from pathlib import Path

import numpy as np
import trimesh

ROOT=Path(__file__).resolve().parents[4]
GLB=ROOT/'assets/props/quarters/dress_uniform.glb'
REPORT=Path(__file__).resolve().parent/'verify.json'
BUILD=Path(__file__).resolve().parent/'build.py'
BLENDER='/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender'
SCRATCH=ROOT/'tmp/fit/tunic'
EXPECTED=['TunicBody','Sleeve_L','Sleeve_R','Collar','ShoulderBoard_L','ShoulderBoard_R','Buttons','CollarInsignia_L','CollarInsignia_R','RibbonBar','Medal','Hanger']
MATERIALS=['NaturalFabric','Brass','RibbonFabric','BareSteel']


def geom_name(name):
    return name.split('.')[0]


def main():
    scene=trimesh.load(GLB,force='scene',process=False)
    mesh_items=[]
    material_names=set()
    for node in scene.graph.nodes_geometry:
        transform,geometry_name=scene.graph[node]
        raw=scene.geometry[geometry_name].copy()
        raw_material=getattr(raw.visual,'material',None)
        if raw_material is not None and raw_material.name:material_names.add(raw_material.name)
        raw.apply_transform(transform)
        welded, remap=np.unique(np.round(raw.vertices,7),axis=0,return_inverse=True)
        geom=trimesh.Trimesh(vertices=welded,faces=remap[raw.faces],process=True)
        mesh_items.append((str(node),geom))
    all_vertices=np.vstack([g.vertices for _,g in mesh_items])
    mins=all_vertices.min(axis=0);maxs=all_vertices.max(axis=0);extents=maxs-mins
    meshes_by_part={}
    for name,mesh in mesh_items:meshes_by_part.setdefault(geom_name(name),[]).append(mesh)
    part_report={}
    for part in EXPECTED:
        candidates=meshes_by_part.get(part,[])
        closed=bool(candidates) and all(m.is_watertight and m.is_winding_consistent for m in candidates)
        part_report[part]={'mesh_count':len(candidates),'closed_manifold':closed,'triangles':sum(len(m.faces) for m in candidates)}
    triangles=sum(len(m.faces) for _,m in mesh_items)
    # Front-facing brass pieces must have a measurable positive exported-Z normal component.
    front_normal_max={}
    for part in ['Buttons','CollarInsignia_L','CollarInsignia_R','Medal']:
        faces=np.vstack([m.face_normals for m in meshes_by_part.get(part,[])]) if meshes_by_part.get(part) else np.empty((0,3))
        front_normal_max[part]=float(faces[:,2].max()) if len(faces) else None
    # The sleeves start below the body side wall. Measure nearest Euclidean surface distance at the arm opening.
    body_mesh=trimesh.util.concatenate(meshes_by_part['TunicBody'])
    gaps={}
    for part in ['Sleeve_L','Sleeve_R']:
        sleeve_mesh=trimesh.util.concatenate(meshes_by_part[part])
        # Compare vertices in a 10 cm armpit band, including body and sleeve surface samples.
        body_v=body_mesh.vertices[(body_mesh.vertices[:,1]>-.67)&(body_mesh.vertices[:,1]<-.34)]
        sleeve_v=sleeve_mesh.vertices[(sleeve_mesh.vertices[:,1]>-.67)&(sleeve_mesh.vertices[:,1]<-.34)]
        if len(body_v) and len(sleeve_v):
            dist=trimesh.proximity.closest_point_naive(body_mesh,sleeve_v)[1]
            gap=float(dist.min())
        else:gap=None
        gaps[part]={'minimum_armpit_gap_m':gap,'required_m':.005,'pass':gap is not None and gap>=.005}
    required_present=all(part_report[p]['mesh_count']>0 for p in EXPECTED)
    manifold=all(v['closed_manifold'] for v in part_report.values())
    orientation={'up_axis':'+Y','front_axis':'+Z','front_normal_z_max':front_normal_max,
                 'front_normals_positive':all(v is not None and v>.05 for v in front_normal_max.values())}
    bounds_pass=bool(abs(extents[0]-.55)<=.04 and abs(extents[1]-.95)<=.04 and extents[2]<=.25)
    bounds={'min_xyz':mins.tolist(),'max_xyz':maxs.tolist(),'extents_xyz':extents.tolist(),
            'target_extents_xyz':[.55,.95,.25],'tolerance_m':[.04,.04,.04],'pass':bounds_pass}
    # Export the saved Blender source again, then compare exact bytes.
    reexport=SCRATCH/'verify-reexport.glb'
    subprocess.run([BLENDER,'--background','--factory-startup','--python-exit-code','1','--python',str(BUILD),'--','--output',str(reexport)],cwd=ROOT,check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    byte_equal=hashlib.sha256(GLB.read_bytes()).digest()==hashlib.sha256(reexport.read_bytes()).digest()
    reexport.unlink(missing_ok=True)
    collision_path=SCRATCH/'collision-check.json'
    collision_script=Path(__file__).resolve().parent/'collision_check.py'
    subprocess.run([BLENDER,'--background','--factory-startup','--python-exit-code','1','--python',str(collision_script),'--','--input',str(GLB),'--report',str(collision_path)],cwd=ROOT,check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    collision_report=json.loads(collision_path.read_text())
    intersection_pairs=collision_report['intersecting_part_pairs']
    required_materials_present=set(MATERIALS).issubset(material_names)
    report={'bounds':bounds,'orientation':orientation,'parts':part_report,'materials':sorted(material_names),
            'required_materials':MATERIALS,'required_materials_present':required_materials_present,'armpit_gaps':gaps,'intersections_over_1mm':intersection_pairs,
            'triangle_count':triangles,'triangle_limit':12000,'byte_identical_reexport':byte_equal}
    report['pass']=bounds['pass'] and orientation['front_normals_positive'] and required_present and manifold and required_materials_present and all(v['pass'] for v in gaps.values()) and not intersection_pairs and triangles<12000 and byte_equal
    REPORT.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if not report['pass']:raise SystemExit('tunic verification failed')

if __name__=='__main__':main()
