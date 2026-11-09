"""Pilot finishing keeps the accepted garment intact outside its free hem."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pilot_finish import hem_displacement

points = np.array([[-.101, -.07, -.859], [.151, -.035, -.879],
                   [0., -.10, -.88], [.09, -.10, -.60], [.20, -.10, -.88], [-.101, -.07, -.83]])
delta = hem_displacement(points)
assert np.all(delta[:2, 2] < -.075), 'Two retained tongues must become distinct longer strips'
assert np.array_equal(delta[2:], np.zeros((4, 3))), 'Placket, torso, sides and strip roots must stay frozen'
assert np.array_equal(delta[:, 0], np.zeros(6)), 'Lengthening must not move strips sideways'
assert np.all(delta[:2, 1] < 0), 'Extended strips drape forward, away from the separate floor deposit'
assert abs(delta[0, 2]-delta[1, 2]) > .01, 'Strip lengths must remain irregular'
print('PASS: two longer tongues, frozen placket/torso/sides/roots, no lateral displacement')
