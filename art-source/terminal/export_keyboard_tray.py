from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tmp/issue91/assembly3/assembly.blend"
OUTPUT = ROOT / "assets/props/terminal/keyboard-tray.glb"

TRAY_NAMES = (
    "Olive steel tray shelf 8mm",
    "Tray rounded downturned front lip",
    "Tray side return ",
    "Tray triangular gusset ",
    "Terminal mounting back flange",
    "Flange back perimeter rubber gasket",
    "Flange hex bolt ",
)
KEYBOARD_NAMES = (
    "Keycap ",
    "Black rubber bellows ",
    "Recessed black elastomer membrane",
    "Rugged olive steel perimeter housing",
    "Keyboard steel skirt ",
    "Proud 13 mm hex socket cap screw.",
    "Dark recessed hex socket",
)
ALLOWED_NAMES = TRAY_NAMES + KEYBOARD_NAMES

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
for obj in list(bpy.context.scene.objects):
    if obj.type == "MESH" and not obj.name.startswith(ALLOWED_NAMES):
        bpy.data.objects.remove(obj, do_unlink=True)

meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
assert sum(obj.name == "Olive steel tray shelf 8mm" for obj in meshes) == 1
assert sum(obj.name.startswith("Keycap ") for obj in meshes) == 29
assert not any("seal" in obj.name.lower() for obj in meshes)

for obj in meshes:
    modifier = obj.modifiers.new("Runtime triangle budget", "DECIMATE")
    modifier.ratio = 0.34
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)

bpy.ops.object.select_all(action="DESELECT")
for obj in meshes:
    obj.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.export_scene.gltf(
    filepath=str(OUTPUT),
    export_format="GLB",
    export_yup=True,
    use_selection=True,
    export_apply=True,
    export_image_format="AUTO",
)
print("EXPORTED_KEYBOARD_TRAY", len(meshes), "named objects")
