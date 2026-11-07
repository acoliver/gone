"""Export the applied cloth meshes from the saved, editable sofa source."""
import argparse
import sys
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[4]
SOURCE = Path(__file__).with_name('sofa-working.blend')
OUT = ROOT / 'assets/props/quarters/sofa.glb'
NAMES = ('Frame', 'Feet', 'Rivets', 'SeatCushion_L', 'SeatCushion_C',
         'SeatCushion_R', 'BackCushion_L', 'BackCushion_C', 'BackCushion_R', 'Throw')


def export(path):
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    if set(o.name for o in meshes) != set(NAMES):
        raise ValueError('Sofa source must contain exactly the ten named baked meshes')
    if any(o.modifiers for o in meshes):
        raise ValueError('Apply simulation and thickness modifiers before saving the source')
    bpy.ops.object.select_all(action='DESELECT')
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = bpy.data.objects['Frame']
    bpy.ops.export_scene.gltf(
        filepath=str(path), export_format='GLB', use_selection=True,
        export_yup=True, export_apply=False, export_materials='EXPORT',
        export_cameras=False, export_lights=False,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=Path, default=OUT)
    ap.add_argument('--render-dir', type=Path)
    args = ap.parse_args(sys.argv[sys.argv.index('--') + 1:])
    out = args.output if args.output.is_absolute() else ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    export(out)
    if args.render_dir:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import render
        render.render(args.render_dir if args.render_dir.is_absolute() else ROOT / args.render_dir)


if __name__ == '__main__':
    main()
