"""Reduce the original generated sector once, repeat it, and Boolean weld joins."""
from pathlib import Path
import json, math, sys, subprocess
import numpy as np
import manifold3d as m
import argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--blender',required=True)
args=parser.parse_args()
OUT=args.output.resolve()
OUT.mkdir(parents=True,exist_ok=True)
SOURCE=Path(__file__).resolve().parents[1]
ROOT=SOURCE.parents[3]
sys.path.insert(0,str(ROOT/'tools/blender'))

inputs=np.load(OUT/'hub-cut-input.npz')
p, inverse=np.unique(inputs['vertices'],axis=0,return_inverse=True)
f=inverse[inputs['faces']]
t=p[f]
f=f[np.linalg.norm(np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]),axis=1)>0]
raw=m.Manifold(m.Mesh(p.astype(np.float32),f.astype(np.uint32)))
assert raw.status()==m.Error.NoError
radius=.30*.3233824063811834
cylinder=m.Manifold.cylinder(2.,radius,circular_segments=192,center=True)
hub=raw^cylinder
outer=raw-cylinder
lo,hi=map(math.radians,[7.5,67.5])
sector=outer.trim_by_plane((-math.sin(lo),math.cos(lo),0),0).trim_by_plane((math.sin(hi),-math.cos(hi),0),0)
cut=json.loads((SOURCE/'hub-cut.json').read_text())['rows'][0]
# Keep the hub separate throughout reduction; the approved planar cut follows assembly.

def reduce(name, source, budget):
    mesh=source.to_mesh()
    np.savez_compressed(OUT/(name.lower()+'-high.npz'),vertices=np.asarray(mesh.vert_properties)[:,:3],faces=np.asarray(mesh.tri_verts))
    blender=args.blender
    subprocess.run([blender,'--background','--factory-startup','--threads','8','--python-exit-code','1','--python',str(SOURCE/'edits/decimate_wheel_sector.py'),'--',str(OUT),name,str(budget)],check=True)
    data=np.load(OUT/(name.lower()+'-low.npz'))
    result=m.Manifold(m.Mesh(data['vertices'].astype(np.float32),data['faces'].astype(np.uint32)))
    assert result.status()==m.Error.NoError,(name,result.status())
    return result

sector=reduce('Sector',sector,550)
hub=reduce('Hub',hub,450)
assembled=hub
for index in range(6):
    assembled=assembled+sector.rotate((0,0,index*60))
assembled=assembled.trim_by_plane((0,0,-1),-cut['cut_plane_z_m'])
assert assembled.status()==m.Error.NoError,assembled.status()
mesh=assembled.to_mesh()
p=np.asarray(mesh.vert_properties)[:,:3].astype(float)
f=np.asarray(mesh.tri_verts)
p[:,2]*=-1; f=f[:,[0,2,1]]
np.savez_compressed(OUT/'wheel-low.npz',vertices=p,faces=f)
print('ASSEMBLED',len(f),'components',len(assembled.decompose()),flush=True)
assert len(f)<=4000,len(f)

subprocess.run([args.blender,'--background','--factory-startup','--threads','8','--python-exit-code','1','--python',str(SOURCE/'edits/cleanup_wheel.py'),'--',str(OUT)],check=True)
