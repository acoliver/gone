"""Regression checks for physical outlets shared by overlapping fixture meshes."""
import tempfile
import unittest
from pathlib import Path

from streak_sources import write_sources


class StreakSourceTests(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).resolve().parents[2] / 'tmp/mat/locker/pass3'
        scratch.mkdir(parents=True, exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.directory.cleanup)
        self.output = Path(self.directory.name) / 'sources.tres'

    def test_handle_and_pocket_share_one_outlet(self):
        sources = [dict(part='Handle', position_blender=[.195, -.279, .885]),
                   dict(part='HandlePocket', position_blender=[.195, -.253, .886])]
        self.assertEqual(write_sources(self.output, sources, 9501), 1)

    def test_vent_backing_does_not_duplicate_louvre_outlet(self):
        sources = [dict(part='DoorVents', position_blender=[0, -.28, 2.1],
                        bounds_blender=[[-.1, -.3, 2.1], [.1, -.26, 2.12]]),
                   dict(part='DoorVents', position_blender=[0, -.27, 2.1],
                        bounds_blender=[[-.1, -.271, 2.1], [.1, -.269, 2.12]])]
        self.assertEqual(write_sources(self.output, sources, 9501), 1)

    def test_seeded_source_table_is_byte_identical(self):
        sources = [dict(part='Rivets', position_blender=[-.295, -.296, 2.1])]
        write_sources(self.output, sources, 9501)
        original = self.output.read_bytes()
        write_sources(self.output, sources, 9501)
        self.assertEqual(original, self.output.read_bytes())


if __name__ == '__main__':
    unittest.main()
