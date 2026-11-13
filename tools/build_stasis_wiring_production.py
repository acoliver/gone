"""Build only the installed issue-110 network, preserving seat and proof assets."""
import json
import subprocess

import numpy as np
import trimesh

from build_stasis_wiring import DEFAULT_BLENDER
from stasis_wiring_assemblies import ROOT, OUT, digest
from stasis_wiring_production import build_installation
from stasis_wiring_installation_graph import graph
from stasis_wiring_provenance import (RESULTS, establish_protected_baseline,
                                      implementation_inputs, snapshot, verify)
from stasis_wiring_export_checks import verify_export


def main():
    protected = establish_protected_baseline()
    inputs = snapshot(implementation_inputs())
    assembly = build_installation()
    scene = assembly.scene()
    glb = OUT/(assembly.name+'.glb')
    glb.write_bytes(scene.export(file_type='glb'))
    row = {'glb':str(glb.relative_to(ROOT)), 'bounds_m':scene.bounds.tolist(),
           'routes':assembly.routes,'contacts':assembly.contacts,'metrics':assembly.metrics,
           'mesh_groups':list(assembly.parts)}
    manifest = {'issue':110,'frame':'bay-local +Y up; metres',
                'assemblies':{assembly.name:row},
                'fault_installed':True,'inputs_sha256':inputs,
                'verification_snapshot':str((RESULTS/'build-snapshot.json').relative_to(ROOT))}
    path = OUT/'production-installation.json'
    path.write_text(json.dumps(manifest,indent=2)+'\n')
    subprocess.run([DEFAULT_BLENDER,'--background','--python-exit-code','1','--python',
                    str(ROOT/'tools/blender/stasis_wiring_proofs.py'),'--','--manifest',str(path)],
                   check=True,cwd=ROOT)
    exported = trimesh.load(glb,force='scene')
    np.testing.assert_allclose(exported.bounds,scene.bounds,atol=1e-6)
    for mesh in exported.geometry.values():
        if not np.isfinite(mesh.vertices).all() or not mesh.is_winding_consistent or mesh.volume<=0:
            raise ValueError('invalid exported production mesh')
    assembly.metrics['exported_physical_checks'] = verify_export(exported,assembly.routes,assembly.metrics)
    from stasis_wiring_fault import verify_exported_tips
    assembly.metrics['fault']['exported_tip_check'] = verify_exported_tips(exported,assembly.metrics['fault'])
    row.update({'exported_bounds_m':exported.bounds.tolist(),
                'export_verified_outside_blender':True,
                'triangles':sum(len(m.faces) for m in exported.geometry.values()),
                'sha256':digest(glb)})
    path.write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'production-routes.json').write_text(json.dumps(graph(assembly),separators=(',',':'))+'\n')
    summary = {'triangles':row['triangles'],'routes':len(assembly.routes),'contacts':len(assembly.contacts),
               'bounds_m':exported.bounds.tolist(),
               'maximum_contact_gap_m':max(v for c in assembly.contacts for k,v in c.items() if k.endswith('gap_m')),
               'minimum_power_radius_m':min(r['minimum_centerline_radius_m'] for r in assembly.routes if r['jacket_od_m']==.024),
               'minimum_data_radius_m':min(r['minimum_centerline_radius_m'] for r in assembly.routes if r['jacket_od_m']==.006),
               'maximum_support_pitch_m':max(v for k,v in assembly.metrics.items() if k.endswith(('support_pitch_m','clip_pitch_m'))),
               'pod_gap_clearance_m':assembly.metrics['drop_pod_side_clearance_m'],
               'lid_sweep_clearance_m':assembly.metrics['all_lid_sweep_vertical_clearance_m'],
               'hidden_terminal_margin_m':assembly.metrics['terminal_hidden_base_margin_m'],
               'fault_endpoints_m':assembly.metrics['fault_connection_endpoints_m'],
               'fault':assembly.metrics['fault']}
    output = RESULTS
    output.mkdir(parents=True,exist_ok=True)
    (output/'build-results.json').write_text(json.dumps(summary,indent=2)+'\n')
    verify(inputs)
    protected_after = verify(protected)
    (output/'protected-after-build.json').write_text(json.dumps(protected_after,indent=2)+'\n')
    outputs = snapshot([glb,OUT/(assembly.name+'.blend'),path,OUT/'production-routes.json'])
    binding = {'inputs_sha256':inputs,'outputs_sha256':outputs,
               'protected_before':protected,'protected_after':protected_after,
               'protected_unchanged':protected==protected_after,
               'hash_cycle_policy':'The build snapshot binds the finalized asset manifest and routes; neither hashes the snapshot.'}
    (output/'build-snapshot.json').write_text(json.dumps(binding,indent=2)+'\n')
    (output/'exported-junction-collision-results.json').write_text(json.dumps(assembly.metrics['exported_physical_checks'],indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
