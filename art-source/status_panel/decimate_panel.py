import bpy

bpy.ops.import_scene.gltf(filepath="assets/props/status_panel/panel.glb")
meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
assert meshes
for obj in meshes:
    modifier = obj.modifiers.new("Runtime triangle budget", "DECIMATE")
    modifier.ratio = 0.17
bpy.ops.export_scene.gltf(
    filepath="tmp/issue91/panelmodel/panel-decimated.glb",
    export_format="GLB", export_yup=True, export_apply=True,
)
print("DECIMATED_PANEL_MESHES", len(meshes))
