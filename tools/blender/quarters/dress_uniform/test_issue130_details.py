"""Issue #130: saved cloth supports eight buttons and a generated, fitted medal."""
import json
from pathlib import Path
import sys

import bpy
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from aging_support import components


def check_sources():
    for state, filename in [('remembered', 'tunic-working.blend'), ('present', 'tunic-pilot.blend')]:
        bpy.ops.wm.open_mainfile(filepath=str(HERE / filename))
        buttons = bpy.data.objects['Buttons']
        groups = components(buttons)
        assert len(groups) == 8, (state, 'Issue #130 requires eight supported buttons')
        centers = np.array([np.mean([buttons.matrix_world @ buttons.data.vertices[i].co for i in group], axis=0)
                            for group in groups])
        centers = centers[np.argsort(-centers[:, 2])]
        np.testing.assert_allclose(centers[:, 2], np.linspace(-.180, -.850, 8), atol=.0001)
        np.testing.assert_allclose(-np.diff(centers[:, 2]), .670 / 7, atol=.0001)
        medal = bpy.data.objects['Medal']
        materials = {mat.name for mat in medal.data.materials}
        assert 'MedalEnamel' in materials or 'MedalEnamel_Aged' in materials, (state, materials)
        record = json.loads(medal['fitted_medal'])
        assert record['guide_sha256'] == 'cf71dd7144f44bc91e0867ec56f8d23b0289ebf9bf91ec135559f577f4ac26a8'
        assert 0.002 <= record['body_depth_m'] <= 0.004
        assert record['body_diameter_m'] == .032
        assert record['raw_sample_count'] >= 100
        ribbon = [p for p in medal.data.polygons if medal.data.materials[p.material_index].name == 'RibbonFabric']
        # #130: the lower U-folds add tessellation without changing the upper sew.
        assert len(ribbon) == 326, (state, 'Lower ribbon loops and central suspension slot')
        assert 'RibbonColours' in medal.data.color_attributes
        assert len(json.loads(medal['attachment'])['metal_base_vertex_indices']) >= 25
    print('PASS: eight endpoint buttons; fitted generated provenance, thickness, enamel and preserved sewn ribbon')


if __name__ == '__main__':
    check_sources()
