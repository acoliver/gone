"""Verify exported meshes, including exact BVH triangle crossings in Blender."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
import bpy
from mathutils.bvhtree import BVHTree

PYTHON = '/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python'
ROOT = Path(__file__).resolve().parents[4]
SCRATCH = ROOT / 'tmp/fit/sofa/cloth2'


def tree(part):
    return BVHTree.FromPolygons(part['vertices'], part['faces'], all_triangles=True, epsilon=0)


def crossings(parts):
    result={}
    for name,components in parts.items():
        counts=[]
        for part in components:
            faces=part['faces'];bvh=tree(part)
            pairs=[(a,b) for a,b in bvh.overlap(bvh)
                   if a<b and not set(faces[a]).intersection(faces[b])]
            counts.append(len(pairs))
        result[name]=counts
    pairs={}
    cushions=[name for name in parts if 'Cushion' in name]
    for name in cushions:
        a=tree(parts[name][0])
        pairs[name+'/Frame']=sum(len(a.overlap(tree(part))) for part in parts['Frame'])
    for i,left in enumerate(cushions):
        for right in cushions[i+1:]:
            pairs[left+'/'+right]=len(tree(parts[left][0]).overlap(tree(parts[right][0])))
    for name in ['Frame']+cushions:
        pairs['Throw/'+name]=sum(len(tree(ply).overlap(tree(part))) for ply in parts['Throw'] for part in parts[name])
    ply_crossings={}
    for i,left in enumerate(parts['Throw']):
        for j,right in enumerate(parts['Throw'][i+1:],start=i+1):
            ply_crossings[str(i)+'/'+str(j)]=len(tree(left).overlap(tree(right)))
    return {'self_triangle_crossings':result,'part_triangle_crossings':pairs,
            'throw_ply_crossings':ply_crossings,
            'pass':not any(count for counts in result.values() for count in counts)
                   and not any(ply_crossings.values())
                   and not any(count for name,count in pairs.items() if name.startswith('Throw/'))}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--report',type=Path,required=True);ap.add_argument('--reexport',type=Path)
    args=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);SCRATCH.mkdir(parents=True,exist_ok=True)
    mesh_data=SCRATCH/(args.input.parent.name+'-meshes.json')
    numeric_report=SCRATCH/(args.input.parent.name+'-trimesh-checks.json')
    numeric_report.unlink(missing_ok=True)
    command=[PYTHON,str(Path(__file__).with_name('trimesh_verify.py')),str(args.input.resolve()),
             '--mesh-data',str(mesh_data),'--report',str(numeric_report)]
    run=subprocess.run(command,capture_output=True,text=True,check=False)
    if run.returncode not in (0,1) or not numeric_report.exists():
        print(run.stdout);print(run.stderr,file=sys.stderr);raise SystemExit('Export measurement failed')
    report=json.loads(numeric_report.read_text())
    report['intersections']=crossings(json.loads(mesh_data.read_text()))
    report['pass']=report['pass'] and report['intersections']['pass']
    if args.reexport:
        report['byte_identical_reexport']=args.input.read_bytes()==args.reexport.read_bytes()
        report['pass']=report['pass'] and report['byte_identical_reexport']
    args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if not report['pass']:raise SystemExit('Sofa exported geometry gates failed')


if __name__=='__main__':main()
