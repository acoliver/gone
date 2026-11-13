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
        # #130: corrected upper-tip source and equally depth-scaled high/low.
        assert record['guide_sha256'] == '796c24f5298353dd35d1f29072158c49dac4e4b788e99f804b1de48fcddeaf4a'
        assert record['parent_generated_sha256'] == 'b98c7c4e688f1f3f6723db629493f965b2df3bb17b30fe923917092d525c3340'
        assert 0.002 <= record['body_depth_m'] <= 0.004
        assert record['body_diameter_m'] == .032
        assert record['raw_sample_count'] >= 100
        ribbon = [p for p in medal.data.polygons if medal.data.materials[p.material_index].name.startswith('RibbonFabric')]
        # #130: the lower U-folds add tessellation without changing the upper sew.
        assert sum(len(p.vertices)-2 for p in ribbon) == json.loads((HERE/'medal-budget.json').read_text())['ribbon_triangles'], (state, 'Closed-slot ribbon allocation')
        assert 'RibbonColours' in medal.data.color_attributes
        assert len(json.loads(medal['attachment'])['metal_base_vertex_indices']) >= 25
    print('PASS: eight endpoint buttons; fitted generated provenance, thickness, enamel and preserved sewn ribbon')


if __name__ == '__main__':
    check_sources()
