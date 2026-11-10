"""Build only the aligned issue-110 prototype; preserve the fault/seat assets."""
import json
import struct
import subprocess
from pathlib import Path

import numpy as np
import trimesh

from build_stasis_wiring import DEFAULT_BLENDER
from stasis_wiring_assemblies import ROOT, OUT, SOURCE, digest, physical_route_graph, transition

MANIFEST = OUT/'supported-transition-aligned.json'


def gltf_document(path):
    data = Path(path).read_bytes()
    length = struct.unpack_from('<I', data, 12)[0]
    return json.loads(data[20:20+length])


def material_map(path):
    doc = gltf_document(path)
    return {'glb':str(path.relative_to(ROOT)), 'sha256':digest(path),
            'materials':doc.get('materials', []),
            'nodes':[{'node_id':i, 'name':node.get('name'), 'mesh_id':node['mesh'],
                      'primitive_material_ids':[p.get('material') for p in doc['meshes'][node['mesh']]['primitives']]}
                     for i,node in enumerate(doc['nodes']) if 'mesh' in node]}


def main():
    assembly = transition(json.loads((OUT/'sockets.json').read_text()))
    scene = assembly.scene()
    glb = OUT/(assembly.name+'.glb')
    glb.write_bytes(scene.export(file_type='glb'))
    row = {'glb':str(glb.relative_to(ROOT)), 'bounds_m':scene.bounds.tolist(),
           'routes':assembly.routes, 'contacts':assembly.contacts, 'metrics':assembly.metrics,
           'physical_graph':physical_route_graph(assembly.routes), 'mesh_groups':list(assembly.parts)}
    manifest = {'issue':110, 'frame':'bay-local +Y up; metres', 'source_position_m':SOURCE.tolist(),
                'source_rotation_y_degrees':90, 'assemblies':{assembly.name:row},
                'socket_manifest_sha256':digest(OUT/'sockets.json'),
                'scope':'Supported transition only. No ShipScene installation, seven-pod network or moving-lid clearance claim.'}
    MANIFEST.write_text(json.dumps(manifest, indent=2)+'\n')
    subprocess.run([DEFAULT_BLENDER,'--background','--python-exit-code','1','--python',
                    str(ROOT/'tools/blender/stasis_wiring_proofs.py'),'--','--manifest',str(MANIFEST)], check=True, cwd=ROOT)
    exported = trimesh.load(glb, force='scene')
    np.testing.assert_allclose(exported.bounds, scene.bounds, atol=1e-6)
    for mesh in exported.geometry.values():
        if not np.isfinite(mesh.vertices).all() or not mesh.is_winding_consistent or mesh.volume<=0:
            raise ValueError('Invalid exported transition mesh')
    row.update({'sha256':digest(glb), 'exported_bounds_m':exported.bounds.tolist(),
                'triangles':sum(len(m.faces) for m in exported.geometry.values()),
                'editable_blend':str((OUT/(assembly.name+'.blend')).relative_to(ROOT)),
                'export_verified_outside_blender':True})
    manifest['sources_sha256'] = {p:digest(ROOT/p) for p in [
        'tools/build_supported_transition.py', 'tools/stasis_wiring_transition.py',
        'tools/stasis_wiring_clearance.py', 'tools/stasis_wiring_assemblies.py',
        'tools/blender/stasis_wiring_proofs.py', 'assets/props/stasis-wiring/stasis-wiring-enclosure.glb',
        'assets/props/stasis-wiring/sockets.json', 'assets/props/stasis-wiring/provenance.json']}
    MANIFEST.write_text(json.dumps(manifest, indent=2)+'\n')
    proof = ROOT/'tmp/verify-stasis-wiring/transition-fit'
    (proof/'gltf-material-map.json').write_text(json.dumps({
        'enclosure':material_map(OUT/'stasis-wiring-enclosure.glb'),
        'transition':material_map(glb)}, indent=2)+'\n')
    print(json.dumps({'triangles':row['triangles'], 'contacts':len(row['contacts']),
                      'metrics':row['metrics'], 'radius_by_route':{r['id']:r['minimum_centerline_radius_m'] for r in row['routes']}}, indent=2))


if __name__ == '__main__':
    main()
