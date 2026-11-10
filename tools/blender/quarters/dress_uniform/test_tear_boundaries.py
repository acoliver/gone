"""Upper binding is intact; only actual released shoulder edges receive opacity loss."""
import sys
from pathlib import Path
import bpy
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from tear_boundaries import labelled_samples, release_weights
from aging_cards import edge_groups

bpy.ops.wm.open_mainfile(filepath=str(ROOT/'tmp/age/tunic8/final/simulated.blend'))
body = bpy.data.objects['TunicBody']
samples, allowed = labelled_samples(body)
points = np.array(samples)
retained = (np.abs(points[:, 0]) < .075) & (points[:, 2] > -.24)
assert retained.any()
assert not allowed[retained].any(), 'Intact shoulder binding must not reveal dark inner-ply speckles'
released = (points[:, 0] > .14) & (points[:, 0] < .24) & (points[:, 2] > -.24)
assert allowed[released].any(), 'Released shoulder still needs frayed lips'
assert release_weights(body).max() == 1.
categories = edge_groups(body)
for ids in categories.values():
    for i in ids:
        point = body.data.vertices[i].co
        assert not (abs(point.x) < .075 and point.z > -.24), 'Fringe grew on retained neck binding'
from tear_boundaries import lip_opacity
distance = np.linspace(0., .004, 80)
boundary = np.zeros((24, 80, 3))
boundary[:, :, 0] = np.linspace(0., .04, 24)[:, None]
opaque = lip_opacity(np.tile(distance, 24), boundary.reshape(-1, 3), 9521).reshape(24, 80)
assert not opaque[:, 0].any()
assert opaque[:, -1].all()
assert (np.diff(opaque.astype(int), axis=1) >= 0).all(), 'Lip erosion created floating opaque islands or inward pinholes'
print('PASS: retained binding stays intact; released-lip erosion is monotone inward and card classification agrees')
