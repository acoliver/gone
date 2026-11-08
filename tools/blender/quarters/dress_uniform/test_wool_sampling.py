"""Damping selection follows measured edge length and reproduces both swatches."""
from pathlib import Path
import json
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from age_tunic import wool_config
from aging_support import HERE

samples = json.loads((HERE/'aging-calibration.json').read_text())['selected']
for sample in samples.values():
    config = wool_config(600, sample['edge_m'])
    np.testing.assert_allclose(config['damping_multiplier'], sample['settings']['damping_multiplier'], rtol=1e-12)
    assert config['stiffness'] == 500.
    assert config['shear'] == 350.
    np.testing.assert_allclose(config['bending'], .3, rtol=1e-6)
assert wool_config(600, .006)['damping_multiplier'] > wool_config(600, .003)['damping_multiplier']
print('PASS: measured-density damping reproduces calibration without changing wool stiffness')
