"""Refresh only Medal finish images and ribbon sampling in the saved mounted sources."""
import argparse
from pathlib import Path
import sys

import bpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from medal_suspender import refresh_maps
from tunic_details import geometry_hash


def refresh(baseline, output):
    output.mkdir(parents=True, exist_ok=True)
    for name, state in [('working', 'remembered'), ('pilot', 'present')]:
        bpy.ops.wm.open_mainfile(filepath=str(baseline / f'tunic-{name}.blend'))
        frozen = {o.name: geometry_hash(o) for o in bpy.context.scene.objects if o.type == 'MESH'}
        medal = bpy.data.objects['Medal']
        refresh_maps(medal, state)
        ribbon = medal.data.materials[2]
        for node in ribbon.node_tree.nodes:
            if node.type == 'MAPPING':
                # DetailUV represents 1.066 m; 16 ribs per tile gives 0.256 mm ribs.
                node.inputs['Scale'].default_value = (260, 260, 1)
            elif node.type == 'TEX_IMAGE':
                image = bpy.data.images.load(str(HERE.parents[3] / 'assets/props/quarters/dress_uniform/medal' / Path(node.image.filepath).name), check_existing=False)
                image.colorspace_settings.name = 'sRGB' if 'albedo' in image.name else 'Non-Color'
                image.pack()
                node.image = image
        for obj in bpy.context.scene.objects:
            if obj.type == 'MESH':
                assert geometry_hash(obj) == frozen[obj.name], obj.name
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(output / f'tunic-{name}.blend'))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
    refresh(a.baseline.resolve(), a.output.resolve())
