"""Run with Blender --background --factory-startup --python <this script>.

Reads the issue-91 assembly below and writes assets/props/terminal/keyboard-tray.glb
relative to this checkout. No command-line arguments are required.
"""
from pathlib import Path
import math
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path("/Volumes/XS1000/acoliver/projects/gone/branch-3/tmp/issue91/assembly3/assembly.blend")
OUTPUT = ROOT / "assets/props/terminal/keyboard-tray.glb"
FRAME_NAME = "Rugged olive steel perimeter housing"
TRAY_NAME = "Bent steel keyboard tray"
KEY_PREFIXES = (
    "Keycap ", "Black rubber bellows ", "Recessed black elastomer membrane",
    FRAME_NAME, "Proud 13 mm hex socket cap screw", "Dark recessed hex socket",
)
TRAY_PREFIXES = (
    "Olive steel tray shelf 8mm", "Tray rounded downturned front lip", "Tray side return",
    "Tray triangular gusset ", "Terminal mounting back flange",
    "Flange back perimeter rubber gasket", "Flange hex bolt ",
)


def world_geometry(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    points = [obj.matrix_world @ vertex.co for vertex in mesh.vertices]
    tree = BVHTree.FromPolygons(points, [list(face.vertices) for face in mesh.polygons])
    evaluated.to_mesh_clear()
    return tree, points


def largest_upward_face(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    mesh.transform(obj.matrix_world)
    faces = sorted(mesh.polygons, key=lambda polygon: polygon.area, reverse=True)
    result = next((polygon for polygon in faces if polygon.normal.z > 0.5), None)
    assert result is not None, f"{obj.name} has no upward face"
    normal = result.normal.normalized()
    point = result.center.copy()
    evaluated.to_mesh_clear()
    return normal, point


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
for obj in list(scene.objects):
    if obj.type == "MESH" and not obj.name.startswith(KEY_PREFIXES + TRAY_PREFIXES):
        bpy.data.objects.remove(obj, do_unlink=True)

frame = bpy.data.objects[FRAME_NAME]
# Keep the connected formed tray from the runtime asset. The source assembly's
# separate front lip hangs below the shelf instead of meeting its front edge.
for obj in list(scene.objects):
    if obj.type == "MESH" and obj.name.startswith(TRAY_PREFIXES[:3]):
        bpy.data.objects.remove(obj, do_unlink=True)
vertices, faces = [], []
indices = {}


def panel(points):
    face = []
    for point in points:
        if point not in indices:
            indices[point] = len(vertices)
            vertices.append(point)
        face.append(indices[point])
    faces.append(face)


rear_y, rear_z = -0.842537, 1.104376
front_y, front_z = -1.112537, 1.0469
width = 0.44
panel([(-width, front_y, front_z), (width, front_y, front_z),
       (width, rear_y, rear_z), (-width, rear_y, rear_z)])
panel([(-width, front_y, front_z), (-width, front_y, front_z - 0.025),
       (width, front_y, front_z - 0.025), (width, front_y, front_z)])
for side in (-1, 1):
    x = side * width
    points = [(x, front_y, front_z), (x, rear_y, rear_z),
              (x, rear_y, rear_z + 0.020), (x, front_y, front_z + 0.020)]
    panel(points if side == -1 else list(reversed(points)))
mesh = bpy.data.meshes.new("Bent steel tray formed panels")
mesh.from_pydata(vertices, [], faces)
mesh.materials.append(next(material for material in frame.data.materials if material))
mesh.update()
tray = bpy.data.objects.new(TRAY_NAME, mesh)
scene.collection.objects.link(tray)
# Thicken downward before measuring the evaluated top surface.
solidify = tray.modifiers.new("3 mm downward tray sheet", "SOLIDIFY")
solidify.thickness = 0.003
solidify.offset = -1.0
bpy.context.view_layer.objects.active = tray
bpy.ops.object.modifier_apply(modifier=solidify.name)
tray_normal, tray_point = largest_upward_face(tray)
assert tray_normal.y < 0 and tray_normal.z > 0, f"invalid tray normal {tray_normal}"
keyboard = [obj for obj in scene.objects if obj.type == "MESH" and obj.name.startswith(KEY_PREFIXES)]
frame_normal, _ = largest_upward_face(frame)
# Rotate the entire assembly about its combined world-space centre.
all_points = [obj.matrix_world @ Vector(corner) for obj in keyboard for corner in obj.bound_box]
centre = sum(all_points, Vector()) / len(all_points)
rotation = frame_normal.rotation_difference(tray_normal)
transform = Matrix.Translation(centre) @ rotation.to_matrix().to_4x4() @ Matrix.Translation(-centre)
for obj in keyboard:
    obj.matrix_world = transform @ obj.matrix_world
bpy.context.view_layer.update()

across = Vector((1, 0, 0))
rearward = tray_normal.cross(across).normalized()
tray_tree, tray_points = world_geometry(tray)
_, frame_points = world_geometry(frame)
# Measure the 15 mm front inset along the tray, rather than its world-space AABB.
front_tray = min(point.dot(rearward) for point in tray_points)
front_frame = min(point.dot(rearward) for point in frame_points)
for obj in keyboard:
    obj.location += rearward * (front_tray + 0.015 - front_frame)
bpy.context.view_layer.update()


def underside_clearances():
    frame_tree, points = world_geometry(frame)
    x_min, x_max = min(p.dot(across) for p in points), max(p.dot(across) for p in points)
    y_min, y_max = min(p.dot(rearward) for p in points), max(p.dot(rearward) for p in points)
    clearances = []
    for u in (0.15, 0.5, 0.85):
        for v in (0.15, 0.5, 0.85):
            point = (across * (x_min + u * (x_max - x_min))
                     + rearward * (y_min + v * (y_max - y_min))
                     + tray_normal * tray_point.dot(tray_normal))
            # A downward ray hits the frame's top. Cast upward from below the
            # tray to measure its underside, and downward for the tray's top.
            bottom = frame_tree.ray_cast(point - tray_normal * 0.05, tray_normal)[0]
            top = tray_tree.ray_cast(point + tray_normal * 0.05, -tray_normal)[0]
            assert bottom is not None and top is not None, f"missing support at {u}, {v}"
            clearances.append((bottom - top).dot(tray_normal))
    return clearances


normal_shift = 0.0005 - min(underside_clearances())
for obj in keyboard:
    obj.location += tray_normal * normal_shift
bpy.context.view_layer.update()
clearances = underside_clearances()
for distance in clearances:
    assert 0.0 <= distance <= 0.001, f"frame bottom sample clearance {distance}"
print("UNDERSIDE_CLEARANCES_MM", [round(distance * 1000, 4) for distance in clearances])

frame_normal, _ = largest_upward_face(frame)
assert frame_normal.y < 0 and frame_normal.z > 0, f"invalid frame normal {frame_normal}"
angle = math.degrees(tray_normal.angle(frame_normal))
assert angle < 0.5, f"tray/frame normals differ by {angle} degrees"
print("TRAY_FRAME_ANGLE_DEGREES", angle)

meshes = [obj for obj in scene.objects if obj.type == "MESH"]
for obj in meshes:
    if obj not in (tray, frame) and len(obj.data.polygons) > 16:
        modifier = obj.modifiers.new("Runtime triangle budget", "DECIMATE")
        modifier.ratio = 0.32
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=modifier.name)


def seat_on_surface(obj, support, normal):
    tree, points = world_geometry(obj)
    support_tree, _ = world_geometry(support)
    centre = sum(points, Vector()) / len(points)
    bottom = tree.ray_cast(centre - normal * 0.1, normal)[0]
    top = support_tree.ray_cast(centre + normal * 0.1, -normal)[0]
    assert bottom is not None and top is not None, f"{obj.name} misses {support.name}"
    clearance = (bottom - top).dot(normal)
    obj.location += normal * (0.0005 - clearance)
    bpy.context.view_layer.update()


# The assembly rotated each key in place without rotating its centre, leaving
# some caps and boots unsupported. Seat each on its own physical support.
membrane = bpy.data.objects["Recessed black elastomer membrane"]
for boot in [obj for obj in keyboard if obj.name.startswith("Black rubber bellows ")]:
    seat_on_surface(boot, membrane, tray_normal)
    cap = bpy.data.objects["Keycap " + boot.name.removeprefix("Black rubber bellows ")]
    seat_on_surface(cap, boot, tray_normal)
flange = bpy.data.objects["Terminal mounting back flange"]
seat_on_surface(bpy.data.objects["Flange back perimeter rubber gasket"], flange,
                (flange.matrix_world.to_3x3() @ Vector((0, 1, 0))).normalized())

geometry = {obj: world_geometry(obj) for obj in meshes}
# Intersecting surfaces are attached even when their vertices are farther apart.
for obj in meshes:
    tree, points = geometry[obj]
    nearest = float("inf")
    for other in meshes:
        if other == obj:
            continue
        other_tree, other_points = geometry[other]
        if tree.overlap(other_tree):
            nearest = 0.0
            break
        nearest = min(nearest, min(other_tree.find_nearest(point)[3] for point in points),
                      min(tree.find_nearest(point)[3] for point in other_points))
        if nearest <= 0.001:
            break
    assert nearest <= 0.001, f"{obj.name} is {nearest:.6f} m from other exported meshes"

allowlist = {
    FRAME_NAME, TRAY_NAME, "Recessed black elastomer membrane",
    "Tray triangular gusset +0.34", "Tray triangular gusset -0.34",
    "Terminal mounting back flange", "Flange back perimeter rubber gasket",
}
allowlist.update(f"Flange hex bolt {index:02d}" for index in range(1, 7))
for prefix in ("Proud 13 mm hex socket cap screw", "Dark recessed hex socket"):
    allowlist.add(prefix)
    allowlist.update(f"{prefix}.{index:03d}" for index in range(1, 10))
keys = (
    "01 onset n", "02 onset l", "03 onset p", "04 onset m", "05 onset k",
    "06 onset w", "07 onset sh", "08 onset t", "09 onset ch", "10 onset carrier",
    "11 vowel a", "12 vowel e", "13 vowel i", "14 vowel o", "15 vowel u",
    "16 command power", "17 command map", "18 command systems", "19 command help",
    "20 control space", "21 control back", "22 control enter", "23 control box",
    "24 control number", "25 control punct", "26 control up", "27 control left",
    "28 control down", "29 control right",
)
allowlist.update(prefix + key for prefix in ("Keycap ", "Black rubber bellows ") for key in keys)
assert {obj.name for obj in meshes} == allowlist, "export mesh names differ from allowlist"
print("EXPORT_ALLOWLIST", sorted(allowlist))

bpy.ops.object.select_all(action="DESELECT")
for obj in meshes:
    obj.select_set(True)
bpy.context.view_layer.objects.active = tray
bpy.ops.export_scene.gltf(filepath=str(OUTPUT), export_format="GLB", export_yup=True,
                          use_selection=True, export_apply=True, export_image_format="AUTO")
print("EXPORTED_KEYBOARD_TRAY", len(meshes), "named objects")
