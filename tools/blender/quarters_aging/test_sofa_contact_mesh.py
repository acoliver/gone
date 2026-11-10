"""Blender regressions for the physical contact-resolution limit."""
from pathlib import Path
import sys
import unittest

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import assert_surface_clear, midsurface
from densify import densify
from sofa_contact_mesh import resolve_elements
from sofa_full_decay import SOURCE


class ContactMesh(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
        self.obj = bpy.data.objects['Throw']
        self.obj.modifiers.clear()
        midsurface(self.obj)
        densify(self.obj, 2)

    def test_blender_clamps_requested_self_distance_to_one_mm(self):
        mod = self.obj.modifiers.new('Distance control', 'CLOTH')
        mod.collision_settings.self_distance_min = .0002
        self.assertAlmostEqual(mod.collision_settings.self_distance_min, .001)

    def test_resolved_throw_is_clear_and_active_faces_resolve_contact_diameter(self):
        source_count = len(self.obj.data.vertices)
        report = resolve_elements(self.obj)
        self.assertGreater(report['collapsed_edges'], 0)
        self.assertLess(len(self.obj.data.vertices), source_count)
        assert_surface_clear(self.obj)
        self.obj.data.calc_loop_triangles()
        p = np.array([v.co[:] for v in self.obj.data.vertices])
        f = np.array([t.vertices[:] for t in self.obj.data.loop_triangles])
        g = self.obj.vertex_groups['Self collision exclusion'].index
        excluded = np.array([any(w.group == g and w.weight > .5 for w in v.groups)
                             for v in self.obj.data.vertices])
        active = f[~np.all(excluded[f], axis=1)]
        triangles = p[active]
        altitude = np.linalg.norm(np.cross(triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0]), axis=1)
        altitude /= np.linalg.norm(triangles-np.roll(triangles, 1, axis=1), axis=2).max(1)
        self.assertGreaterEqual(float(altitude.min()), .002-1e-8)
        self.assertGreater(len(active)/len(f), .8)
        self.assertEqual(len(self.obj.data.uv_layers), 1)


class TearRelaxation(unittest.TestCase):
    def setUp(self):
        from fabric_mesh import material, new_object
        bpy.ops.wm.read_factory_settings(use_empty=True)
        n = 20
        points = [(i*.01, j*.01, 0) for j in range(n+1) for i in range(n+1)]
        faces = [(j*(n+1)+i, j*(n+1)+i+1, (j+1)*(n+1)+i+1, (j+1)*(n+1)+i)
                 for j in range(n) for i in range(n)]
        self.obj = new_object('Relaxation control', points, faces, material('Control', (.1, .1, .1)))

    def test_wide_relaxation_does_not_widen_lip_collision_exclusion(self):
        from split_contacts import exclude_split_contacts
        from tear_paths import split_polyline
        obj = self.obj
        result = split_polyline(obj, [(.04, .10, 0), (.16, .10, 0)], shrink_band=.06)
        self.assertAlmostEqual(result['area_before_m2'], result['area_after_m2'])
        exclude_split_contacts(obj)
        vertex = min(obj.data.vertices, key=lambda v: (v.co.x-.10)**2+(v.co.y-.13)**2)
        weights = {g.group: g.weight for g in vertex.groups}
        self.assertGreater(weights[obj.vertex_groups['Lip relaxation'].index], .4)
        self.assertNotIn(obj.vertex_groups['Lip shrink'].index, weights)
        self.assertNotIn(obj.vertex_groups['Self collision exclusion'].index, weights)

    def test_length_limit_truncates_the_physical_cut_and_its_shrink_field(self):
        from tear_paths import split_polyline
        obj = self.obj
        value = split_polyline(obj, [(.01, .10, 0), (.19, .10, 0)], max_length=.12)
        self.assertGreater(value['split_length_m'], .11)
        self.assertLessEqual(value['split_length_m'], .12)
        self.assertAlmostEqual(value['area_before_m2'], value['area_after_m2'])
        group = obj.vertex_groups['Lip shrink'].index
        self.assertFalse(any(v.co.x > .15 and any(g.group == group for g in v.groups) for v in obj.data.vertices))


class SeatOpeningContract(unittest.TestCase):
    def test_three_seats_have_two_length_limited_splits_and_a_long_opening(self):
        from foam_collapse import largest_shell
        from seat_tears import author
        from sofa_full_decay import open_cover_bottom
        from sofa_decay_policy import cushion_plan
        for name in ['SeatCushion_C', 'SeatCushion_L', 'SeatCushion_R']:
            with self.subTest(part=name):
                bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
                obj = bpy.data.objects[name]
                obj.modifiers.clear()
                largest_shell(obj)
                open_cover_bottom(obj, False)
                densify(obj, 2)
                resolve_elements(obj)
                value = author(obj, obj.matrix_world.translation.x, cushion_plan(name)['seed'])
                self.assertEqual(len(value['paths']), 3)
                for path in value['paths'][:2]:
                    self.assertGreaterEqual(path['split_length_m'], .120)
                    self.assertLessEqual(path['split_length_m'], .250)
                self.assertGreaterEqual(value['fallen_island_reference_size_m'], .120)
                self.assertLessEqual(value['fallen_island_reference_size_m'], .250)
                self.assertTrue(all(path['removed_area_m2'] == 0 for path in value['paths']))




class DebrisTemplates(unittest.TestCase):
    def test_loader_rejects_crossed_template_without_losing_required_variation(self):
        from sofa_decay_debris import load_templates
        bpy.ops.wm.read_factory_settings(use_empty=True)
        library = SOURCE.parents[4]/'tmp/age/pass4/fragments8/fragment-library.blend'
        templates = load_templates(library)
        self.assertEqual(len(templates), 8)
        self.assertNotIn('fragment-05', [name for name, _, _ in templates])


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]])
