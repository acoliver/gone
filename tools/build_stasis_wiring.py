"""Rebuild both issue-110 physical proofs using the existing local toolchain.

Run with a Python environment containing numpy, scipy, trimesh and Pillow.
No packages or assets are downloaded. Blender is only an editable-file and
native-frame exporter; all fit measurements also run outside Blender.
"""
import argparse
import json
from pathlib import Path
import subprocess

import numpy as np
import trimesh

from stasis_wiring_assemblies import ROOT, OUT, build, digest

DEFAULT_BLENDER='/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--blender',default=DEFAULT_BLENDER)
    args=parser.parse_args()
    manifest=build()
    subprocess.run([args.blender,'--background','--python-exit-code','1','--python',
                    str(ROOT/'tools/blender/stasis_wiring_proofs.py')],check=True,cwd=ROOT)
    for name,row in manifest['assemblies'].items():
        path=ROOT/row['glb']
        scene=trimesh.load(path,force='scene')
        np.testing.assert_allclose(scene.bounds,row['bounds_m'],atol=1e-6)
        meshes=list(scene.geometry.values())
        if not meshes or not all(np.isfinite(m.vertices).all() for m in meshes):
            raise ValueError('invalid exported mesh: '+name)
        if not all(m.is_winding_consistent and m.volume>0 for m in meshes):
            raise ValueError('invalid export winding: '+name)
        row['sha256']=digest(path)
        row['exported_bounds_m']=scene.bounds.tolist()
        row['editable_blend']=str((OUT/(name+'.blend')).relative_to(ROOT))
        row['export_verified_outside_blender']=True
        row['export_material_names']=[m.visual.material.name for m in meshes]
    manifest['source_files']={p:digest(ROOT/p) for p in [
        'tools/build_stasis_wiring.py','tools/stasis_wiring_assemblies.py',
        'tools/blender/stasis_wiring_proofs.py','tools/stasis_wiring_geometry.py',
        'tools/seat_rail.py','tools/seat_rail_proof.py','tools/stasis_wiring_transition.py',
        'tools/stasis_wiring_clearance.py']}
    manifest['external_references']={
        'enclosure':'assets/props/stasis-wiring/stasis-wiring-enclosure.glb',
        'panel':'assets/props/bay-ceiling/intact.glb'}
    manifest['scope']='Two static proof sections, not installed in ShipScene. Seven-pod branches and full motion clearance are integration work.'
    (OUT/'proof-assemblies.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'result':'PASS','assemblies':{name:{
        'glb':row['glb'],'editable_blend':row['editable_blend'],
        'triangles':row['triangles'],'bounds_m':row['exported_bounds_m'],
        'contacts':len(row['contacts']),
        'minimum_centerline_radius_m':min(r['minimum_centerline_radius_m'] for r in row['routes']),
        'minimum_surface_radius_m':min(r['minimum_surface_longitudinal_radius_m'] for r in row['routes'])}
        for name,row in manifest['assemblies'].items()}},indent=2))


if __name__=='__main__':
    main()
