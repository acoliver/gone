"""Reuse the power-room keyboard, without changing its mesh or installed scale."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE.parent / 'wardrobe'))
from batch_tools import export, unwrap

SOURCE = ROOT / 'assets/props/terminal/keyboard.glb'
SCALE = json.loads((SOURCE.parent / 'keyboard-placement.json').read_text())['scale'][0]


def refit():
    bpy.ops.wm.open_mainfile(filepath=str(HERE / 'console-working.blend'))
    removed = False
    for obj in list(bpy.data.objects):
        if obj.name in {'Keys', 'Toggles'} or obj.name.startswith(('Key_', 'Toggle')):
            bpy.data.objects.remove(obj, do_unlink=True)
            removed = True
    # The old caps were independent closed solids, not holes in this panel.
    console = [o for o in bpy.context.scene.objects if o.get('quarters_prop') == 'console']
    if removed:
        unwrap([o for o in console if o.type == 'MESH'])
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'console-working.blend'))
    deck = bpy.data.objects['ControlPanel']
    deck_frame = deck.matrix_world.copy()
    deck_depth = max(v.co.y for v in deck.data.vertices) - min(v.co.y for v in deck.data.vertices)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
    base, mesh = bpy.data.objects['KeyboardBase'], bpy.data.objects['Keyboard']
    points = np.array([v.co[:] for v in mesh.data.vertices])
    # Use the terminal pipeline's 25 first-hit underside rays, not side vertices.
    tree = BVHTree.FromPolygons([v.co for v in mesh.data.vertices],
                               [tuple(p.vertices) for p in mesh.data.polygons], all_triangles=True)
    underside = []
    for y in np.linspace(-.075, .075, 5):
        for x in np.linspace(-.30, .30, 5):
            hit = tree.ray_cast(Vector((x, y, -.1)), Vector((0, 0, 1)))[0]
            assert hit is not None, 'Keyboard underside support ray'
            underside.append(list(hit))
    underside = np.array(underside)
    design = np.column_stack([underside[:, :2], np.ones(len(underside))])
    a, b, _ = np.linalg.lstsq(design, underside[:, 2], rcond=None)[0]
    normal = Vector((-a, -b, 1)).normalized()
    right = Vector((1, 0, a)).normalized()
    back = normal.cross(right).normalized()
    rotation = Matrix((right, back, normal)).to_4x4()
    local = rotation @ Matrix.Diagonal((SCALE, SCALE, SCALE, 1))
    positioned = np.array([local @ Vector(p) for p in points])
    local.translation = Vector((-(positioned[:, 0].min()+positioned[:, 0].max())/2,
                                -deck_depth/2 + .010 - positioned[:, 1].min(),
                                .0095 - positioned[:, 2].min()))
    base.matrix_world = deck_frame @ local
    base['quarters_prop'] = 'console_keyboard'
    mesh['quarters_prop'] = 'console_keyboard'
    bpy.context.view_layer.update()
    placement = dict(source=str(SOURCE.relative_to(ROOT)), installed_uniform_scale=SCALE,
                     scale_reason='Retains power-room installed key and case sizes; deck already fits the unit.',
                     deck_size_m=[1.02, deck_depth], front_margin_m=.010,
                     minimum_deck_gap_m=.0005,
                     native_console_frame=[list(row) for row in base.matrix_world])
    (HERE / 'keyboard-placement.json').write_text(json.dumps(placement, indent=2)+'\n')
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'keyboard-working.blend'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refit', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT / 'assets/props/quarters/console_keyboard.glb')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    if args.refit:
        refit()
    else:
        bpy.ops.wm.open_mainfile(filepath=str(HERE / 'keyboard-working.blend'))
    export(args.output, [bpy.data.objects['KeyboardBase'], bpy.data.objects['Keyboard']])


if __name__ == '__main__':
    main()
