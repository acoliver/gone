"""Content mutations must invalidate evidence, even with unchanged filenames."""
import copy
import tempfile
from pathlib import Path
import unittest

from stasis_wiring_provenance import snapshot, verify, verify_capture


class ProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        for name in ['implementation.py','context.json','routes.json','production.glb','image.png','readback.json']:
            (self.root/name).write_bytes(name.encode())
        self.inputs = snapshot([self.root/p for p in ['implementation.py','context.json','routes.json','production.glb']],self.root)
        self.data = {'fingerprints_before':self.inputs,'fingerprints_after':self.inputs.copy(),
                     'protected_before':self.inputs.copy(),'protected_after':self.inputs.copy(),
                     'readback_sha256':snapshot([self.root/'readback.json'],self.root),
                     'captures':[{'path':str(self.root/'image.png'),'sha256':snapshot([self.root/'image.png'],self.root)['image.png']}]}

    def test_valid_snapshot_and_capture_pass(self):
        self.assertEqual(verify(self.inputs,self.root),self.inputs)
        self.assertTrue(verify_capture(self.data,self.root))

    def test_tampered_implementation_context_routes_and_glb_fail(self):
        for name in self.inputs:
            with self.subTest(name=name):
                path = self.root/name
                original = path.read_bytes()
                path.write_bytes(original+b'tampered')
                with self.assertRaisesRegex(ValueError,'fingerprint mismatch'):
                    verify(self.inputs,self.root)
                with self.assertRaisesRegex(ValueError,'fingerprint mismatch'):
                    verify_capture(self.data,self.root)
                path.write_bytes(original)

    def test_tampered_png_fails(self):
        (self.root/'image.png').write_bytes(b'changed pixels')
        with self.assertRaisesRegex(ValueError,'PNG fingerprint mismatch'):
            verify_capture(self.data,self.root)

    def test_tampered_actual_readback_fails(self):
        (self.root/'readback.json').write_bytes(b'changed readback')
        with self.assertRaisesRegex(ValueError,'fingerprint mismatch'):
            verify_capture(self.data,self.root)

    def test_changed_during_capture_fails(self):
        data = copy.deepcopy(self.data)
        data['fingerprints_after']['implementation.py'] = 'changed'
        with self.assertRaisesRegex(ValueError,'changed during rendering'):
            verify_capture(data,self.root)
