"""Positive/negative controls for the small-prop export gates."""
import unittest
import numpy as np
import trimesh

from verify import ROOT, dust_difference, topology


class TopologyTests(unittest.TestCase):
    def test_closed_box(self):
        self.assertTrue(topology(trimesh.creation.box())['pass'])

    def test_missing_face_fails(self):
        mesh=trimesh.creation.box()
        mesh.update_faces(np.arange(len(mesh.faces))!=0)
        self.assertFalse(topology(mesh)['pass'])

    def test_inverted_shell_fails(self):
        mesh=trimesh.creation.box()
        mesh.invert()
        self.assertFalse(topology(mesh)['pass'])

    def test_hollow_open_mouth_is_closed_wall(self):
        mesh=trimesh.creation.annulus(r_min=.035,r_max=.04,height=.10,sections=24)
        self.assertTrue(topology(mesh)['pass'])

    def test_mixed_outward_and_inward_shells_fail(self):
        a=trimesh.creation.box(); b=trimesh.creation.box()
        b.apply_translation((2,0,0)); b.invert()
        self.assertFalse(topology(trimesh.util.concatenate([a,b]))['pass'])


class DustTests(unittest.TestCase):
    def test_identical_capture_fails(self):
        import tempfile
        from pathlib import Path
        from PIL import Image
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp/small') as tmp:
            path=Path(tmp)/'control.png'
            Image.new('RGB',(16,16),(100,100,100)).save(path)
            self.assertFalse(dust_difference(path,path)['pass'])

    def test_visible_change_passes(self):
        import tempfile
        from pathlib import Path
        from PIL import Image
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp/small') as tmp:
            a,b=Path(tmp)/'a.png',Path(tmp)/'b.png'
            Image.new('RGB',(16,16),(100,100,100)).save(a)
            Image.new('RGB',(16,16),(115,110,105)).save(b)
            self.assertTrue(dust_difference(a,b)['pass'])


if __name__=='__main__':
    unittest.main()
