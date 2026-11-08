"""Run in Blender: every face incident to a lip must be wholly excluded."""
import sys
import unittest
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from split_contacts import exclude_split_contacts


class SplitContacts(unittest.TestCase):
    def test_incident_triangles_include_vertices_outside_the_shrink_band(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        mesh = bpy.data.meshes.new('Split control')
        mesh.from_pydata([(0,0,0), (1,0,0), (0,1,0), (1,1,0), (2,1,0)], [], [(0,1,2), (1,3,2), (1,4,3)])
        obj = bpy.data.objects.new('Split control', mesh)
        bpy.context.collection.objects.link(obj)
        obj.vertex_groups.new(name='Lip shrink').add([0], 1., 'REPLACE')
        result = exclude_split_contacts(obj)
        group = obj.vertex_groups['Self collision exclusion']
        excluded = {v.index for v in mesh.vertices if any(g.group == group.index for g in v.groups)}
        self.assertEqual(excluded, {0,1,2})
        self.assertEqual(result['incident_faces'], 1)
        self.assertEqual(result['excluded_vertices'], 3)
        self.assertAlmostEqual(obj.vertex_groups['Lip shrink'].weight(0), 1.)


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]])
