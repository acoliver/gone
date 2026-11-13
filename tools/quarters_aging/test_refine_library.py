"""Targeted source edits must not change other approved library variants."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import refine_library
from steel_library import ROOT


class TargetedRefinementTests(unittest.TestCase):
    def test_only_requested_face_receives_the_refinement(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp/mat2') as name:
            library = Path(name)
            selected = dict(id='top-01', kind='top', seed=10, pixels=[64, 64],
                            image='top-01.png', raw='original.png', passed=True,
                            treatment=dict(denoise_px=1))
            untouched = dict(selected, id='top-02', image='top-02.png')
            manifest = dict(faces=[selected, untouched])
            (library/'manifest.json').write_text(json.dumps(manifest))
            (library/'top-01.png').write_bytes(b'approved source')
            (library/'top-01-test-raw.png').write_bytes(b'existing generated candidate')
            with patch.object(refine_library, 'LIBRARY', library), \
                 patch('sys.argv', ['refine_library', '--face', 'top-01', '--label', 'test']), \
                 patch.object(refine_library, 'wait_for_gpu') as gpu, \
                 patch.object(refine_library.subprocess, 'run') as run, \
                 contextlib.redirect_stdout(io.StringIO()):
                refine_library.main()
            result = json.loads((library/'manifest.json').read_text())
            self.assertEqual(result['faces'][1], untouched)
            self.assertEqual(result['faces'][0]['raw'], 'top-01-test-raw.png')
            self.assertFalse(result['faces'][0]['passed'])
            self.assertNotIn('treatment', result['faces'][0])
            self.assertEqual((library/'top-01-test-input.png').read_bytes(), b'approved source')
            gpu.assert_not_called()
            run.assert_not_called()

    def test_unknown_face_fails_before_any_generation_or_mutation(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp/mat2') as name:
            library = Path(name)
            path = library/'manifest.json'
            path.write_text('{"faces": []}')
            with patch.object(refine_library, 'LIBRARY', library), \
                 patch('sys.argv', ['refine_library', '--face', 'missing']), \
                 patch.object(refine_library, 'wait_for_gpu') as gpu, \
                 contextlib.redirect_stderr(io.StringIO()), \
                 self.assertRaises(SystemExit) as failure:
                refine_library.main()
            self.assertEqual(failure.exception.code, 2)
            self.assertEqual(path.read_text(), '{"faces": []}')
            gpu.assert_not_called()


if __name__ == '__main__':
    unittest.main()
