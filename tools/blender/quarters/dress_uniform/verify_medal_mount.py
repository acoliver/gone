"""Independent accepted-metal and incremental-contact preservation checks for #130."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from tunic_details import points


def verify(sources, materials, contacts, evidence_directory):
    frames=json.loads((contacts/'contact-frames.json').read_text())
    report={}
    for state,name in [('remembered','working'),('present','pilot')]:
        bpy.ops.wm.open_mainfile(filepath=str(sources/f'tunic-{name}.blend'))
        mounted=bpy.data.objects['Medal']
        frame=json.loads(mounted['medal_frame'])
        with bpy.data.libraries.load(str(materials/f'medal-pbr-{state}.blend'),link=False) as (_,dest): dest.objects=['MedalLow']
        accepted=dest.objects[0]
        v=np.array([p.co[:] for p in accepted.data.vertices])[:4041]
        expected=np.array(frame['origin'])+np.einsum('ij,jk->ik',v,np.array(frame['frame']))
        actual=points(mounted)[:len(v)]
        reverse=np.array(json.loads(mounted['attachment'])['metal_base_vertex_indices'])
        visible=np.ones(len(v),bool);visible[reverse]=False
        error=np.max(abs(expected[visible]-actual[visible]))
        assert error <= 3e-8,(state,'Accepted visible metal moved beyond source float32 quantization',error)
        assert np.all(abs(v[reverse,1])<1e-8),'Only original reverse-datum vertices may be fitted'
        assert len(accepted.data.polygons)==8270
        retained=[p for p in accepted.data.polygons if all(i<len(v) for i in p.vertices)]
        assert len(retained)==8082
        for before,after in zip(retained,mounted.data.polygons[:len(retained)]):
            assert tuple(before.vertices)==tuple(after.vertices),'Metal topology changed'
            assert before.material_index==after.material_index,'Metal/enamel region changed'
            assert before.use_smooth==after.use_smooth,'Accepted facet shading changed'
        a=np.array([accepted.data.uv_layers['MedalUV'].data[i].uv[:] for p in retained for i in p.loop_indices])
        b=np.array([p.uv[:] for p in mounted.data.uv_layers['DetailUV'].data[:len(a)]])
        np.testing.assert_array_equal(a,b)
        key='aged' if state=='present' else 'as_built'
        assert frame==frames[key]['source_frame'],'Contact bake used a different mount frame'
        evidence=np.load(evidence_directory/f'{key}_contact-evidence.npz')
        ao=evidence['ao'];base=evidence['baseline'];combined=evidence['mounted']
        valid=base>0
        np.testing.assert_allclose(ao[valid],combined[valid]/base[valid],atol=0,rtol=0)
        assert np.all(ao[~evidence['bounded']]==1),'Contact escaped its bounded patch'
        assert np.any((base-combined)[valid]>0),'Empty incremental contact bake'
        report[state]=dict(accepted_metal_topology_uv_material_regions_smooth_flags_exact=True,
            visible_position_max_quantization_error_m=float(error),reverse_only_fitting_vertices=len(reverse),
            contact_frame_exact=True,contact_ratio_exact=True,
            contact_outside_bound_max_delta=float(np.max(abs(1-ao[~evidence['bounded']]))),
            contact_changed_texels=int((ao<1).sum()))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['sources','materials','contacts','evidence','output']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    result=verify(a.sources.resolve(),a.materials.resolve(),a.contacts.resolve(),a.evidence.resolve())
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print('PASS: accepted visible metal and UVs unchanged; reverse-only fitting and bounded incremental contact ratios',flush=True)
