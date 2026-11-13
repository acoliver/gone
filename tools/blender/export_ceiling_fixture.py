"""Export the selected packed fixture without its hidden generated source."""
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'art-source/ceiling-props/fixture/aging/fixture.blend'
PARTS = (
    'Seed720_CleanedGeneratedBeam',
    'GeneratedUnderside_ArmouredGrille',
    'RaisedRails_Rivets_GravityFasteners',
    'RecessedGlass_13mm',
)


def main(output=ROOT / 'assets/props/ceiling/fixture.glb'):
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    bpy.ops.object.select_all(action='DESELECT')
    for name in PARTS:
        obj = bpy.data.objects[name]
        obj.hide_set(False)
        obj.select_set(True)
    bpy.context.view_layer.objects.active = bpy.data.objects[PARTS[0]]
    bpy.ops.export_scene.gltf(
        filepath=str(output),
        export_format='GLB', use_selection=True, export_yup=True,
        export_apply=True, export_materials='EXPORT', export_extras=True,
    )


if __name__ == '__main__':
    main()
