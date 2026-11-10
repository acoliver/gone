"""Check the embedded powder pigment, not just the Blender image datablock."""
import io
import json
from pathlib import Path
import struct
import unittest

import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[4]


class ExportedFinishTests(unittest.TestCase):
    def test_powder_keeps_neutral_fibre_pigment_after_packing(self):
        data=(ROOT/'assets/props/quarters/her_dresses_aged.glb').read_bytes()
        length=struct.unpack_from('<I',data,12)[0]
        document=json.loads(data[20:20+length])
        binary=28+length
        powders=[m for m in document['materials'] if m['name'].startswith('FloorDust_')]
        self.assertEqual(len(powders),2)
        for material in powders:
            index=material['pbrMetallicRoughness']['baseColorTexture']['index']
            image=document['images'][document['textures'][index]['source']]
            view=document['bufferViews'][image['bufferView']]
            start=binary+view.get('byteOffset',0)
            rgba=np.asarray(Image.open(io.BytesIO(data[start:start+view['byteLength']])).convert('RGBA'))
            color=np.median(rgba[:,:,:3][rgba[:,:,3]>.5],axis=0)
            self.assertGreater(float(color[0]),100)
            self.assertGreater(float(color[1]),90)
            self.assertGreater(float(color[2]),75)
            self.assertLess(float(color[0]/color[2]),1.5)
            self.assertEqual(material['alphaMode'],'MASK')
            self.assertFalse(material.get('doubleSided',False))


if __name__=='__main__':unittest.main()
