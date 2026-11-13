"""Refresh only the seat manifest's rebuilt standalone context, not seat assets."""
import json

import numpy as np

from seat_rail_context_checks import frame_metrics
from seat_rail_proof import CEILING_ORIGIN
from stasis_wiring_assemblies import OUT, ROOT, digest
from stasis_wiring_provenance import RESULTS, verify


def main():
    path = OUT/'seat-rail/manifest.json'
    data = json.loads(path.read_text())
    previous = data['sources_sha256'].copy()
    changed = 'tools/seat_rail_proof.py'
    verify({p:h for p,h in previous.items() if p!=changed})
    np.testing.assert_allclose(CEILING_ORIGIN,[-.6,2.988,-.6],atol=1e-12)
    data['prototype_frame'] = frame_metrics()
    data['sources_sha256'][changed] = digest(ROOT/changed)
    data['proof_context_revision'] = {
        'failed_seat_center_m':CEILING_ORIGIN.tolist(),
        'reason':'Standalone context now uses the production lower-seat failure; profile, PBR and floor pose unchanged.',
        'previous_source_sha256':previous[changed],
        'context_glb_sha256':digest(OUT/'fault-frame-pair.glb'),
        'archived_manifest':'tmp/verify-stasis-wiring/production-corrected/historical-manifests/manifest.json'}
    path.write_text(json.dumps(data,indent=2)+'\n')
    verify(data['sources_sha256'])
    (RESULTS/'proof-context-refresh.json').write_text(json.dumps(data['proof_context_revision'],indent=2)+'\n')
    print('PROOF_CONTEXT_REFRESH_PASS seat/profile/PBR/floor inputs unchanged')


if __name__ == '__main__':
    main()
