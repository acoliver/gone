import bpy

bpy.ops.wm.open_mainfile(filepath="tmp/issue91/assembly3/assembly.blend")
tray_prefixes = (
    "Olive steel tray", "Tray ", "Terminal mounting back flange",
    "Flange back perimeter rubber gasket", "Flange hex bolt",
)
keyboard_prefixes = (
    "Keyboard ", "Keycap ", "Rugged olive steel perimeter housing",
    "Inset olive seal", "Left hand onset seal", "Right hand vowel seal",
)
selected = []
for obj in bpy.context.scene.objects:
    if obj.type != "MESH":
        continue
    if obj.name.startswith(tray_prefixes + keyboard_prefixes):
        selected.append(obj)
    else:
        obj.hide_set(True)
assert any(obj.name.startswith("Olive steel tray") for obj in selected)
assert any(obj.name.startswith("Keycap ") for obj in selected)
bpy.ops.object.select_all(action="DESELECT")
for obj in selected:
    obj.hide_set(False)
    obj.select_set(True)
bpy.context.view_layer.objects.active = selected[0]
for obj in selected:
    modifier = obj.modifiers.new("Runtime triangle budget", "DECIMATE")
    modifier.ratio = 0.34
bpy.ops.export_scene.gltf(
    filepath="assets/props/terminal/keyboard-tray.glb",
    export_format="GLB", export_yup=True, use_selection=True, export_apply=True,
)
print("EXPORTED_KEYBOARD_TRAY", len(selected), "objects")
