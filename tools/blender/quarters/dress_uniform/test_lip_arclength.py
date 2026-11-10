"""Lip wavelengths follow physical travel, including a folded return."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lip_arclength import chain_stations

points = np.array([[0., 0., 0.], [.003, .004, 0.], [.003, .004, .012], [0., 0., .012]])
np.testing.assert_allclose(chain_stations(points), [0., .005, .017, .022])
rotation = np.array([[0., 0., 1.], [1., 0., 0.], [0., 1., 0.]])
np.testing.assert_allclose(chain_stations(points@rotation+3.), chain_stations(points), atol=1e-12)
print('PASS: physical stations preserve wavelength through folds, rotations and translations')
