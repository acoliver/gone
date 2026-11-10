"""The collar-side shoulder samples must not expose dark rear-ply triangles."""
import argparse
from pathlib import Path
import sys
import bpy
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out', type=Path, default=ROOT/'tmp/age/tunic9/binding')
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
bpy.ops.wm.open_mainfile(filepath=str(args.out/'baked.blend'))
body = bpy.data.objects['TunicBody']
body.data.calc_loop_triangles()
vertices = np.array([body.matrix_world @ v.co for v in body.data.vertices])
triangles = list(body.data.loop_triangles)
centers = np.array([vertices[list(t.vertices)].mean(0) for t in triangles])
image = bpy.data.images.load(str(args.out/'textures/tunic_opacity.png'), check_existing=False)
pixels = np.array(image.pixels[:]).reshape(image.size[1], image.size[0], 4)
uv = body.data.uv_layers['BakeUV'].data
samples = 0
for target in [(.133, -.0058, -.1577), (.139, -.005, -.1577), (.1485, -.0048, -.1608)]:
    i = np.linalg.norm(centers-target, axis=1).argmin()
    assert np.linalg.norm(centers[i]-target) < .003
    corners = np.array([uv[k].uv[:] for k in triangles[i].loops])
    for a in np.linspace(.05, .90, 32):
        for b in np.linspace(.05, .95-a, 32):
            weights = np.array([a, b, 1-a-b])
            point = weights @ corners
            x, y = np.floor(point*np.array(image.size[:])).astype(int)
            assert pixels[y, x, 0] == 1., (target, point, pixels[y, x, 0])
            samples += 1
assert (pixels[:, :, 0] == 0).any(), 'Actual released lips must keep their opacity loss'
print('PASS:', samples, 'collar-side shoulder samples stay opaque; released lips retain opacity loss')
