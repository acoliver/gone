"""Audit only the baked proof's carrier/ledger topology, not production geometry."""
import numpy as np
import trimesh
from seat_rail import OUT


def frame_metrics():
    scene=trimesh.load(OUT.parent/'fault-frame-pair.glb',force='scene')
    frame=next(mesh.copy() for name,mesh in scene.geometry.items() if 'steel_frame' in name)
    frame.merge_vertices()
    parts=frame.split(only_watertight=False)
    bounds=np.asarray([part.bounds for part in parts])
    unique=len(np.unique(np.round(bounds.reshape(len(parts),-1),6),axis=0))
    duplicate_count=len(parts)-unique
    extents=np.ptp(bounds,axis=1)
    # Cross seats run along X. The remaining long ledgers run along Z.
    replaced=[part for part in parts if part.extents[0]>.5 and part.bounds[0,1]<2.988-1e-6]
    upper=[part for part in parts if np.allclose(part.extents,[3.6,.055,.055],atol=1e-6)
           and abs(part.centroid[2]+.6)<1e-6]
    assert duplicate_count==0 and len(replaced)==0 and len(upper)==1
    np.testing.assert_allclose(upper[0].bounds[:,0],[-2.4,1.2],atol=1e-6)
    return {'frame_components':len(parts),'duplicated_frame_components':duplicate_count,
            'replaced_flat_cross_ledger_count':len(replaced),
            'intact_upper_carrier_at_failure_count':len(upper),
            'intact_upper_carrier_bounds_m':upper[0].bounds.tolist(),
            'long_flat_ledger_count':int(np.sum((extents[:,2]>.5)&(extents[:,1]<.00301)))}
