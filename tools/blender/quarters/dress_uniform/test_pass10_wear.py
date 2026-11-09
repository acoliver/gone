"""Pass-ten finishing fields preserve binding and concentrate wear on cloth stress."""
from pathlib import Path
import sys
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wear_pass10 import body_wear, finishing_displacement, ragged_erosion

binding = np.array([[.13, -.006, -.158], [-.18, 0., -.17]])
pattern = np.array([[.33, .94], [.12, .94]])
np.testing.assert_array_equal(finishing_displacement(binding, pattern), np.zeros((2, 3)))
back = np.array([[.20, .003, -.18]])
front = np.array([[.20, -.006, -.18]])
assert finishing_displacement(back, np.array([[.85, .94]]))[0, 1] > .010
assert finishing_displacement(front, np.array([[.35, .94]]))[0, 1] == 0.
hem = np.array([[.08, -.08, -.845], [.08, -.08, -.65]])
movement = finishing_displacement(hem, np.array([[.3, .03], [.3, .3]]))
assert movement[0, 2] >= .015
assert movement[1, 2] == 0.
station = np.c_[np.linspace(.17, .25, 1000), np.zeros(1000), np.full(1000, -.18)]
erosion = ragged_erosion(station, 9521)
assert erosion.min() >= .0002 and erosion.max() <= .0065
assert np.ptp(erosion) > .003
uv = np.array([[.12, .38], [.12, .40], [.37, .62], [.25, .3], [.26, .90], [1.3, .4]])
wear = body_wear(uv)
assert wear['hole'][0] and wear['hole'][2]
assert not wear['hole'][1:].all()
assert not wear['hole'][-2:].any()
assert np.all((wear['thinning'] >= 0) & (wear['thinning'] <= 1))
np.testing.assert_array_equal(body_wear(uv)['hole'], wear['hole'])
print('PASS: retained crest, separated rear shoulder lip, deeper hem, ragged erosion and sparse stress holes')
