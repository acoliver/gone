"""The retained shoulder holds the neckline beyond the old 100 mm cutoff."""
from pathlib import Path
import sys
import tempfile

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from age_tunic import prepare
from aging_support import ROOT
from common import surface_tree

with tempfile.TemporaryDirectory(dir=ROOT / 'tmp/age/tunic8') as scratch:
    record = prepare(Path(scratch))
    body = bpy.data.objects['TunicBody']
    neck = [v for v in body.data.vertices
            if -.10 < v.co.x < -.085 and v.co.z > -.22 and abs(v.co.y) < .003]
    assert neck, 'The source neckline control must contain actual grid vertices'
    wire = surface_tree(bpy.data.objects['Hanger'])
    for vertex in neck:
        assert record['pins'][vertex.index] == 1., vertex.index
        hit, _, _, _ = wire.ray_cast(Vector((vertex.co.x, vertex.co.y, .1)), Vector((0, 0, -1)))
        assert hit is not None
        assert vertex.co.z >= hit.z+.0039999
print('PASS: retained neckline vertices remain held above the unchanged hanger')
