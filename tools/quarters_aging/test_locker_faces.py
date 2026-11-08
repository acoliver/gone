"""Regression controls for directly mapped generated face colour."""
import inspect
import unittest
from unittest.mock import patch
from tempfile import TemporaryDirectory

import numpy as np
from PIL import Image

import locker_faces as faces


class FaceTests(unittest.TestCase):
    def test_layout_is_disjoint_and_meets_density(self):
        occupied = np.zeros((faces.ATLAS[1],faces.ATLAS[0]),bool)
        for name,row in faces.manifest()['faces'].items():
            x0,y0,x1,y1 = row['rect']
            self.assertFalse(occupied[y0-4:y1+4,x0-4:x1+4].any(),name)
            occupied[y0-4:y1+4,x0-4:x1+4] = True
            self.assertGreaterEqual(min(row['pixels_per_metre']),600 if name=='door' else 300)

    def test_no_procedural_field_drives_colour(self):
        implementation = inspect.getsource(faces.pack)
        for old_generator in ('noise(', 'blister_field', 'gravity_runs', 'edge_reach'):
            self.assertNotIn(old_generator,implementation)
        shader = (faces.ROOT/'app/shaders/quarters_steel.gdshader').read_text()
        self.assertNotIn('gravity_trails(',shader)
        self.assertNotIn('oxide_field(',shader)

    def test_flat_colour_is_not_eligible_as_pattern_free(self):
        with self.assertRaisesRegex(ValueError,'constant albedo'):
            faces.scores(Image.new('RGB',(128,128),'#808080'),Image.new('RGB',(128,128),'#808080'),faces.FACES['top'])

    def test_thresholds_reject_each_defect(self):
        good = dict(delta_e=2.,paint_mean_delta_e=2.,rust_std_delta_e=2.,planar_light_gradient=.02,
                    secondary_autocorrelation=.3,edge_broad_ratio=2.)
        self.assertTrue(faces.eligible(good))
        for key,value in [('delta_e',8.1),('planar_light_gradient',.06),('secondary_autocorrelation',.501),('edge_broad_ratio',1.79)]:
            self.assertFalse(faces.eligible(dict(good,**{key:value})),key)

    def test_pack_preserves_every_generated_rgb_pixel_and_hatch_alpha(self):
        with TemporaryDirectory(dir=faces.SCRATCH) as name:
            directory = faces.Path(name)
            output = directory/'out'
            output.mkdir()
            pixels = np.full((16,16,3),[130,140,132],np.uint8)
            pixels[:,:4] = [105,40,15]
            image = Image.fromarray(pixels)
            image.save(directory/'chosen.png')
            face = dict(size=[.1,.1],rect=[8,8,24,24])
            with patch.multiple(faces,SOURCE=directory,ATLAS=(32,32),FACES={'door':face}):
                faces.pack({'door':{'chosen':'chosen.png'}},output)
            atlas = np.asarray(Image.open(output/'aged-face-albedo.png'))
            np.testing.assert_array_equal(atlas[8:24,8:24,:3],pixels)
            expected = np.round((1-faces.paint_fields(image)[1])*255).astype(np.uint8)
            np.testing.assert_array_equal(atlas[8:24,8:24,3],expected)
            normal = np.asarray(Image.open(output/'aged-face-normal.png'))
            self.assertGreater(np.max(abs(normal[8:24,8:24,0].astype(float)-128)),10)

    def test_hw_export_has_smooth_knuckles_below_fifteen_degrees(self):
        from locker_face_gates import hinge_metrics
        measurements = hinge_metrics()
        self.assertLessEqual(measurements['knuckle_adjacent_face_angle_max_deg'],15.)
        self.assertLessEqual(measurements['knuckle_split_normal_jump_max_deg'],15.)

    def test_knuckle_end_rims_also_meet_adjacent_normal_limit(self):
        import trimesh
        scene = trimesh.load(faces.SOURCE/'hinges.glb',force='scene',process=False)
        for mesh in scene.geometry.values():
            mesh.merge_vertices(merge_tex=True,merge_norm=True)
            self.assertLessEqual(float(np.degrees(mesh.face_adjacency_angles).max()),15.)

    def test_optional_stains_do_not_change_existing_image_rust(self):
        from locker_face_runoff import attached_runs
        image = Image.new('RGB',(128,512),(130,140,132))
        pixels = np.asarray(image).copy()
        pixels[:30,:10] = [105,40,15]
        image = Image.fromarray(pixels)
        result,records = attached_runs(image,'door')
        self.assertGreater(len(records),0)
        self.assertTrue(all(row['max_opacity']<=.3 for row in records))
        original_rust = faces.paint_fields(image)[1]<.5
        np.testing.assert_array_equal(np.asarray(result)[original_rust],pixels[original_rust])


if __name__ == '__main__':
    unittest.main()
