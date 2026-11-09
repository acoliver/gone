"""Mound fibres retain resolved bundle coverage at the close camera's scale."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from soft_wool_atlas import heap_bundle_alpha

alpha = heap_bundle_alpha(9521)
assert alpha.shape == (1024, 1024)
assert np.isfinite(alpha).all() and alpha.min() >= 0 and alpha.max() <= 1
for variant in range(8):
    root = alpha[variant*128+8] >= .5
    edges = np.flatnonzero(np.diff(np.r_[False, root, False]))
    widths = edges[1::2]-edges[::2]
    assert len(widths) == 4
    assert widths.min() >= 32, 'A three-millimetre card needs bundle coverage wider than 0.09 mm'
np.testing.assert_array_equal(alpha, heap_bundle_alpha(9521))
print('PASS: four curled, resolved bundles per mound card; deterministic fractional coverage')
