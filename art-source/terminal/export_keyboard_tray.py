from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tmp/issue91/assembly3/assembly.blend"
OUTPUT = ROOT / "assets/props/terminal/keyboard-tray.glb"
TRAY_PREFIXES = (
    "Olive steel tray shelf 8mm", "Tray rounded downturned front lip",
    "Tray side return", "Tray triangular gusset ", "Terminal mounting back flange",
    "Flange back perimeter rubber gasket", "Flange hex bolt ",
)
KEYBOARD_PREFIXES = (
    "Keycap ", "Black rubber bellows ", "Recessed black elastomer membrane",
    "Rugged olive steel perimeter housing", "Keyboard steel skirt ",
    "Proud 13 mm hex socket cap screw.", "Dark recessed hex socket",
)

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
for obj in list(scene.objects):
    if obj.type == "MESH" and not (obj.name.startswith(TRAY_PREFIXES) or obj.name.startswith(KEYBOARD_PREFIXES)):
        bpy.data.objects.remove(obj, do_unlink=True)

# Replace the separate shelf, lip and returns with one mesh containing the
# connected formed panels. Coordinates follow the authored 12 degree shelf.
old = [obj for obj in scene.objects if obj.type == "MESH" and obj.name.startswith((
    "Olive steel tray shelf 8mm", "Tray rounded downturned front lip", "Tray side return"))]
steel = next(m for obj in scene.objects if obj.name == "Rugged olive steel perimeter housing" for m in obj.data.materials if m)
for obj in old:
    bpy.data.objects.remove(obj, do_unlink=True)
verts, faces = [], []
def panel(points):
    start = len(verts)
    verts.extend(points)
    faces.append(tuple(range(start, len(verts))))
# 8 mm shelf, extending from the rear flange to the downturned front bend.
rear_y, rear_z = -0.842537, 1.104376
front_y, front_z = -1.112537, 1.0469
width = 0.44
panel([(-width,rear_y,rear_z), (width,rear_y,rear_z), (width,front_y,front_z), (-width,front_y,front_z)])
panel([(-width,front_y,front_z), (width,front_y,front_z), (width,front_y,front_z-0.025), (-width,front_y,front_z-0.025)])
# Upturned edges are continued from the shelf edges to form integral returns.
for side in (-1, 1):
    x = side * width
    panel([(x,rear_y,rear_z), (x,front_y,front_z), (x,front_y,front_z+0.020), (x,rear_y,rear_z+0.020)])
mesh = bpy.data.meshes.new("Bent steel tray formed panels")
mesh.from_pydata(verts, [], faces)
mesh.materials.append(steel)
mesh.update()
obj = bpy.data.objects.new("Bent steel keyboard tray", mesh)
scene.collection.objects.link(obj)
# Keep the flange, gasket, gussets, bolts and keyboard assembly as authored.
meshes = [o for o in scene.objects if o.type == "MESH"]
assert len([o for o in meshes if o.name == "Bent steel keyboard tray"]) == 1
assert sum(o.name.startswith("Keycap ") for o in meshes) == 29
for obj in meshes:
    modifier = obj.modifiers.new("Runtime triangle budget", "DECIMATE")
    modifier.ratio = 0.34
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)
bpy.ops.object.select_all(action="DESELECT")
for obj in meshes:
    obj.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.export_scene.gltf(filepath=str(OUTPUT), export_format="GLB", export_yup=True,
                          use_selection=True, export_apply=True, export_image_format="AUTO")
print("EXPORTED_KEYBOARD_TRAY", len(meshes), "named objects")
