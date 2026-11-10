"""Build the fitted locker from its generated guide proportions and export GLB.

Run from the repository root with Blender --background --factory-startup
--python-exit-code 1 --python tools/blender/quarters/storage_locker_module/build.py --
--output assets/props/quarters/storage_locker_module.glb --save-source.
"""
import argparse
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "assets/props/quarters/storage_locker_module.glb"
SOURCE = Path(__file__).resolve().parent / "locker-working.blend"
PAINT = (0.19, 0.29, 0.27, 1.0)


def material(name, color, metallic=0.65, roughness=0.42):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    shader = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = roughness
    return mat


def box_piece(name, dims, center, mat, bevel=0.0025):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new("Edge radii", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        mod.limit_method = "ANGLE"
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return obj


def join_pieces(name, pieces, parent=None):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in pieces:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = pieces[0]
    bpy.ops.object.join()
    obj = bpy.context.object
    obj.name = name
    if parent:
        obj.parent = parent
        obj.matrix_parent_inverse = parent.matrix_world.inverted()
    return obj


def uv_unwrap(obj):
    if obj.type != "MESH":
        return
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(island_margin=0.02)
    bpy.ops.object.mode_set(mode="OBJECT")


def cut_box(obj, center, dims):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    cutter = bpy.context.object
    cutter.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.context.view_layer.objects.active = obj
    mod = obj.modifiers.new("Recess cut", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def create_asset():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    painted = material("PaintedSteel", PAINT)
    bare = material("BareSteel", (0.34, 0.39, 0.37, 1.0), 0.82, 0.3)
    dark = material("DarkSteel", (0.045, 0.060, 0.058, 1.0), 0.76, 0.48)

    # Geometry is laid out in the former fitting frame, then the two asset
    # roots are rotated into Blender's native Z-up frame before export.
    carcass_parts = []
    carcass_parts += [
        box_piece("Side shell", (0.022, 2.295, 0.56), (-0.289, 1.2525, 0.0), painted, 0.003),
        box_piece("Side shell", (0.022, 2.295, 0.56), (0.289, 1.2525, 0.0), painted, 0.003),
        box_piece("Rear shell", (0.556, 2.295, 0.022), (0.0, 1.2525, -0.289), painted),
        box_piece("Top return", (0.556, 0.022, 0.580), (0.0, 2.389, 0.0), painted),
        box_piece("Lower return", (0.556, 0.022, 0.580), (0.0, 0.094, 0.0), painted),
        box_piece("Kick plate", (0.520, 0.105, 0.520), (0.0, 0.0525, 0.0), dark, 0.003),
        box_piece("Surround left", (0.040, 2.18, 0.018), (-0.280, 1.30, 0.291), painted),
        box_piece("Surround right", (0.040, 2.18, 0.018), (0.280, 1.30, 0.291), painted),
        box_piece("Surround top", (0.520, 0.055, 0.018), (0.0, 2.3625, 0.291), painted),
        box_piece("Surround bottom", (0.520, 0.018, 0.018), (0.0, 0.100, 0.291), painted),
    ]
    carcass = bpy.data.objects.new("Carcass", None)
    bpy.context.scene.collection.objects.link(carcass)
    for index, piece in enumerate(carcass_parts, start=1):
        piece.name = ["SidePanel_L", "SidePanel_R", "BackPanel", "TopPanel",
                      "BottomPanel", "KickPlate", "SurroundStile_L",
                      "SurroundStile_R", "SurroundHead", "SurroundSill"][index - 1]
        piece.parent = carcass
        piece.matrix_parent_inverse = carcass.matrix_world.inverted()

    door_width, door_height, door_depth = 0.514, 2.220, 0.024
    door = box_piece("Door", (door_width, door_height, door_depth), (-0.260 + door_width / 2, 0.110 + door_height / 2, 0.258), painted, 0)
    # Local origin is the left hinge axis at the bottom of the leaf.
    door.location = (-0.260, 0.110, 0.258)
    for v in door.data.vertices:
        v.co.x += door_width / 2 + 0.003
        v.co.y += door_height / 2
    # Slots stop short of the back skin, leaving real recessed cavities.
    slot_x, slot_w, slot_h = 0.120, 0.240, 0.014
    slot_ys = (1.990, 2.045, 2.100)
    for sy in slot_ys:
        cut_box(door, (slot_x + slot_w / 2 - 0.240, sy + 0.110, 0.258 + 0.004), (slot_w, slot_h, 0.018))
    # The handle pocket is below waist level, on the right door edge.
    pocket_x, pocket_y, pocket_w, pocket_h = 0.405, 0.770, 0.060, 0.170
    cut_box(door, (pocket_x + pocket_w / 2 - 0.240, pocket_y + pocket_h / 2 + 0.110, 0.258 + 0.004), (pocket_w, pocket_h, 0.018))
    edge = door.modifiers.new("Door edge bevel", "BEVEL")
    edge.width = 0.002
    edge.segments = 2
    edge.limit_method = "ANGLE"
    bpy.context.view_layer.objects.active = door
    bpy.ops.object.modifier_apply(modifier=edge.name)
    door.location = (-0.260, 0.110, 0.301)
    for vertex in door.data.vertices:
        vertex.co.z -= 0.043
    door.data.materials.clear()
    door.data.materials.append(painted)
    door["pivot_description"] = "Origin is the left hinge edge at the 110 mm door bottom."
    # Shallow returns along the back perimeter give the leaf a folded-sheet edge.
    return_parts = [
        box_piece("DoorReturn_L", (0.008, door_height - 0.012, 0.012), (-0.249, 1.220, 0.240), painted, 0.002),
        box_piece("DoorReturn_R", (0.008, door_height - 0.012, 0.012), (0.249, 1.220, 0.240), painted, 0.002),
        box_piece("DoorReturn_B", (door_width - 0.012, 0.012, 0.012), (0.0, 0.116, 0.240), painted, 0.002),
        box_piece("DoorReturn_T", (door_width - 0.012, 0.012, 0.012), (0.0, 2.324, 0.240), painted, 0.002),
    ]
    for part in return_parts:
        part.parent = door
        part.matrix_parent_inverse = door.matrix_world.inverted()

    vent_parts = []
    for sy in slot_ys:
        piece = box_piece("Louvre", (0.300, 0.025, 0.022),
                          (slot_x + slot_w / 2 - 0.240, sy + 0.110, 0.258 + 0.020), painted, 0.001)
        piece.rotation_euler.x = math.radians(-30)
        vent_parts.append(piece)
        backing = box_piece("Vent recess", (slot_w, slot_h, 0.003),
                            (slot_x + slot_w / 2 - 0.240, sy + 0.110, 0.252), dark, 0.0005)
        vent_parts.append(backing)
    vents = join_pieces("DoorVents", vent_parts, door)
    pocket = box_piece("HandlePocket", (pocket_w - 0.008, pocket_h - 0.012, 0.003),
                       (pocket_x + pocket_w / 2 - 0.240, pocket_y + pocket_h / 2 + 0.110, 0.258 - 0.006), dark, 0.001)
    pocket.parent = door
    pocket.matrix_parent_inverse = door.matrix_world.inverted()
    lever = box_piece("Handle", (0.110, 0.014, 0.010),
                      (pocket_x + pocket_w / 2 - 0.240, pocket_y + 0.012 + 0.110, 0.258 + 0.021), bare, 0.002)
    lever.parent = door
    lever.matrix_parent_inverse = door.matrix_world.inverted()

    hinge_parts = []
    for center_y in (0.350, 1.250, 2.150):
        bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.010, depth=0.080,
                                            location=(-0.260, center_y, 0.301),
                                            rotation=(math.radians(90), 0, 0))
        knuckle = bpy.context.object
        knuckle.name = "Hinge knuckle"
        bevel = knuckle.modifiers.new("Rounded knuckle rims", "BEVEL")
        bevel.width = .0007
        bevel.segments = 7
        bevel.limit_method = 'ANGLE'
        bevel.angle_limit = .5
        bpy.ops.object.modifier_apply(modifier=bevel.name)
        for face in knuckle.data.polygons:
            face.use_smooth = abs(face.normal.z) < .9999
        knuckle.data.materials.append(bare)
        hinge_parts.append(knuckle)
    hinges = join_pieces("Hinges", hinge_parts, carcass)
    bpy.ops.object.select_all(action="DESELECT")
    hinges.select_set(True)
    bpy.context.view_layer.objects.active = hinges
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.0001)
    bpy.ops.object.mode_set(mode="OBJECT")

    rivet_parts = []
    rivet_locations = []
    for y in [0.260 + i * 0.135 for i in range(16)]:
        rivet_locations.extend(((-0.295, y, 0.2965), (0.295, y, 0.2965)))
    for x in [(-0.2025 + i * 0.135) for i in range(4)]:
        rivet_locations.extend(((x, 0.100, 0.2965), (x, 2.390, 0.2965)))
    for x in (-0.286, 0.286):
        for y in [0.260 + i * 0.135 for i in range(16)]:
            rivet_locations.append((x, y, 0.2825))
    for location in rivet_locations:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=3, radius=1, location=location)
        r = bpy.context.object
        r.name = "Rivet"
        r.scale = (0.006, 0.006, 0.0035)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        r.data.materials.append(bare)
        rivet_parts.append(r)
    rivets = join_pieces("Rivets", rivet_parts, carcass)

    # Rotate every world transform, then restore parenting without changing
    # the transformed world matrices. Parenting inverses otherwise cancel a
    # root-only rotation in the glTF exporter.
    carcass.rotation_euler = (0, 0, 0)
    door.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()
    frame = Matrix.Rotation(math.radians(90), 4, "X")
    objects = [obj for obj in bpy.context.scene.objects if obj.type in {"MESH", "EMPTY"}]
    parent_by_object = {obj: obj.parent for obj in objects}
    world_by_object = {obj: frame @ obj.matrix_world.copy() for obj in objects}
    for obj in objects:
        obj.parent = None
        obj.matrix_world = world_by_object[obj]
    for obj in objects:
        parent = parent_by_object[obj]
        if parent:
            obj.parent = parent
            obj.matrix_parent_inverse = parent.matrix_world.inverted()
            obj.matrix_world = world_by_object[obj]
    bpy.context.view_layer.update()
    for obj in (carcass, door, vents, pocket, lever, hinges, rivets):
        uv_unwrap(obj)
    bpy.context.view_layer.update()
    return carcass, door


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def setup_camera(name, location, target, ortho, resolution):
    data = bpy.data.cameras.new(name)
    camera = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = location
    aim(camera, target)
    data.type = "ORTHO"
    data.ortho_scale = ortho
    bpy.context.scene.camera = camera
    bpy.context.scene.render.resolution_x = resolution
    bpy.context.scene.render.resolution_y = resolution
    bpy.context.scene.render.resolution_percentage = 100
    return camera


def render_previews(render_dir):
    render_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.72, 0.72, 0.72)
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "Medium High Contrast"
    scene.display.shading.light = "STUDIO"
    scene.render.resolution_percentage = 100
    light_data = bpy.data.lights.new("Studio", "AREA")
    light = bpy.data.objects.new("Studio", light_data)
    scene.collection.objects.link(light)
    light.location = (2.8, -4.2, 4.0)
    light_data.energy = 450
    light_data.shape = "DISK"
    light_data.size = 4
    fill_data = bpy.data.lights.new("StudioFill", "AREA")
    fill = bpy.data.objects.new("StudioFill", fill_data)
    scene.collection.objects.link(fill)
    fill.location = (-3.0, 3.5, 2.8)
    fill_data.energy = 300
    fill_data.shape = "DISK"
    fill_data.size = 3.5
    key = setup_camera("HeroCamera", (-2.0, -3.5, 2.6), (0, 0, 1.2), 3.15, 768)
    scene.render.filepath = str(render_dir / "compare-hero.png")
    bpy.ops.render.render(write_still=True)
    setup_camera("FrontCamera", (0, -4.5, 1.2), (0, 0, 1.2), 2.75, 768)
    scene.render.filepath = str(render_dir / "compare-front.png")
    bpy.ops.render.render(write_still=True)
    rad = math.radians(30)
    setup_camera("TurntableCamera", (4.0 * math.sin(rad), -4.0 * math.cos(rad), 1.2), (0, 0, 1.2), 3.15, 768)
    scene.render.filepath = str(render_dir / "turntable.png")
    bpy.ops.render.render(write_still=True)
    setup_camera("DetailCamera", (-0.6, -2.0, 2.02), (0, 0.28, 2.02), 0.92, 768)
    scene.render.filepath = str(render_dir / "compare-detail.png")
    bpy.ops.render.render(write_still=True)
    scene.camera = key


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--save-source", action="store_true")
    parser.add_argument("--render-dir", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.save_source or not SOURCE.exists():
        carcass, door = create_asset()
        if args.save_source:
            bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))
    else:
        bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
        carcass = bpy.data.objects["Carcass"]
        door = bpy.data.objects["Door"]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.data.objects:
        if obj.type in {"MESH", "EMPTY"}:
            obj.select_set(True)
    bpy.context.view_layer.objects.active = carcass
    bpy.ops.export_scene.gltf(filepath=str(output.resolve()), export_format="GLB", use_selection=True,
                              export_yup=True, export_apply=False, export_materials="EXPORT",
                              export_cameras=False, export_lights=False)
    if args.render_dir:
        render_previews(args.render_dir if args.render_dir.is_absolute() else ROOT / args.render_dir)


if __name__ == "__main__":
    main()
