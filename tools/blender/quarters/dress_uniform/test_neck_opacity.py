"""Released-lip breakup must not perforate the reinforced retained neckline."""
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from tear_opacity import wool_opacity

bpy.ops.wm.open_mainfile(filepath=str(ROOT/'tmp/age/tunic8/final/baked.blend'))
image, report = wool_opacity(bpy.data.objects['TunicBody'], ROOT/'tmp/age/tunic8/neck-opacity-control.png')
pixels = np.array(image.pixels[:]).reshape(image.size[1], image.size[0], 4)
for uv in ((.01370196, .17742443), (.01417995, .17778875)):
    x, y = np.floor(np.array(uv)*image.size[:]).astype(int)
    assert pixels[y, x, 0] == 1., (uv, pixels[y, x])
assert report['transparent_texels'] > 0, 'Released lips must retain their breakup'
print('PASS: both retained-neckline texels are opaque; released lip breakup remains')
