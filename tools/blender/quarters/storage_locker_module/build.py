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
from mathutils import Vector

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

    # The measured hero guide is upright on Y, with its visible front on +Z.
    # Its cross-sections are wider than the 600 mm inventory module, so the
    # clean cage is proportionally fitted to the fixed 600 mm envelope.
    carcass_parts = []
    carcass_parts += [
        box_piece("Side shell", (0.022, 2.20, 0.56), (-0.289, 1.30, 0.0), painted),
        box_piece("Side shell", (0.022, 2.20, 0.56), (0.289, 1.30, 0.0), painted),
        box_piece("Rear shell", (0.556, 2.20, 0.022), (0.0, 1.30, -0.269), painted),
        box_piece("Top return", (0.556, 0.022, 0.250), (0.0, 2.389, -0.145), painted),
        box_piece("Lower return", (0.556, 0.022, 0.250), (0.0, 0.211, -0.145), painted),
        box_piece("Plinth", (0.600, 0.200, 0.600), (0.0, 0.100, 0.0), painted, 0.003),
        box_piece("Surround left", (0.040, 2.18, 0.018), (-0.280, 1.30, 0.291), painted),
        box_piece("Surround right", (0.040, 2.18, 0.018), (0.280, 1.30, 0.291), painted),
        box_piece("Surround top", (0.520, 0.055, 0.018), (0.0, 2.3625, 0.291), painted),
        box_piece("Surround bottom", (0.520, 0.040, 0.018), (0.0, 0.180, 0.291), painted),
        # The kick plate front face sits 40 mm behind the cabinet front.
        box_piece("Kick plate", (0.490, 0.150, 0.012), (0.0, 0.110, 0.254), dark, 0.0015),
    ]
    carcass = bpy.data.objects.new("Carcass", None)
    bpy.context.scene.collection.objects.link(carcass)
    for index, piece in enumerate(carcass_parts, start=1):
        piece.name = f"CarcassPart_{index:02d}"
        piece.parent = carcass
        piece.matrix_parent_inverse = carcass.matrix_world.inverted()

    door_width, door_height, door_depth = 0.480, 2.120, 0.024
    door = box_piece("Door", (door_width, door_height, door_depth), (-0.240 + door_width / 2, 0.210 + door_height / 2, 0.258), painted, 0)
    # Local origin is the left hinge edge at the bottom of the leaf.
    door.location = (-0.240, 0.210, 0.258)
    for v in door.data.vertices:
        v.co.x += door_width / 2
        v.co.y += door_height / 2
    # Slots stop short of the back skin, leaving real recessed cavities.
    slot_x, slot_w, slot_h = 0.142, 0.196, 0.022
    slot_ys = (1.890, 1.940, 1.990)
    for sy in slot_ys:
        cut_box(door, (slot_x + slot_w / 2 - 0.240, sy + 0.210, 0.258 + 0.004), (slot_w, slot_h, 0.018))
    # The handle pocket is below waist level, on the right door edge.
    pocket_x, pocket_y, pocket_w, pocket_h = 0.405, 0.770, 0.060, 0.170
    cut_box(door, (pocket_x + pocket_w / 2 - 0.240, pocket_y + pocket_h / 2 + 0.210, 0.258 + 0.004), (pocket_w, pocket_h, 0.018))
    edge = door.modifiers.new("Door edge bevel", "BEVEL")
    edge.width = 0.002
    edge.segments = 2
    edge.limit_method = "ANGLE"
    bpy.context.view_layer.objects.active = door
    bpy.ops.object.modifier_apply(modifier=edge.name)
    door.location = (-0.240, 0.210, 0.258)
    door.data.materials.clear()
    door.data.materials.append(painted)
    door["pivot_description"] = "Origin is the left hinge edge at floor-level door bottom."

    vent_parts = []
    for sy in slot_ys:
        # Louvers sit inside the cut slots, 7 mm behind the outer door face.
        piece = box_piece("Louvre", (slot_w - 0.010, 0.010, 0.008),
                          (slot_x + slot_w / 2 - 0.240, sy + 0.210, 0.258 + 0.001), painted, 0.002)
        vent_parts.append(piece)
    vents = join_pieces("DoorVents", vent_parts, door)
    pocket = box_piece("HandlePocket", (pocket_w - 0.008, pocket_h - 0.012, 0.003),
                       (pocket_x + pocket_w / 2 - 0.240, pocket_y + pocket_h / 2 + 0.210, 0.258 - 0.006), dark, 0.001)
    pocket.parent = door
    pocket.matrix_parent_inverse = door.matrix_world.inverted()
    lever = box_piece("Handle", (0.040, 0.008, 0.008),
                      (pocket_x + pocket_w / 2 - 0.240, pocket_y + 0.012 + 0.210, 0.258 + 0.002), bare, 0.002)
    lever.parent = door
    lever.matrix_parent_inverse = door.matrix_world.inverted()

    hinge_parts = []
    for y in (0.355, 2.085):
        hinge_parts.append(box_piece("Hinge knuckle", (0.010, 0.085, 0.012), (-0.251, y, 0.282), bare, 0.002))
        hinge_parts.append(box_piece("Hinge pin", (0.004, 0.090, 0.004), (-0.251, y, 0.282), bare, 0.0015))
    hinges = join_pieces("Hinges", hinge_parts, carcass)

    rivet_parts = []
    for y in [0.290 + i * 0.182 for i in range(12)]:
        for x in (-0.295, 0.295):
            bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=4, radius=1, location=(x, y, 0.282))
            r = bpy.context.object
            r.name = "Rivet"
            r.scale = (0.0045, 0.0045, 0.0025)
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            r.data.materials.append(bare)
            rivet_parts.append(r)
    for x in (-0.212, 0.0, 0.212):
        for y in (0.180, 2.389):
            bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=4, radius=1, location=(x, y, 0.2975))
            r = bpy.context.object
            r.name = "Rivet"
            r.scale = (0.0045, 0.0045, 0.0025)
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            r.data.materials.append(bare)
            rivet_parts.append(r)
    rivets = join_pieces("Rivets", rivet_parts, carcass)

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
    light.location = (2.8, 4.0, 4.2)
    light_data.energy = 450
    light_data.shape = "DISK"
    light_data.size = 4
    key = setup_camera("HeroCamera", (3.0, 2.65, 4.1), (0, 1.2, 0), 3.15, 768)
    scene.render.filepath = str(render_dir / "locker-render.png")
    bpy.ops.render.render(write_still=True)
    setup_camera("FrontCamera", (0, 1.2, 4.5), (0, 1.2, 0), 2.75, 768)
    scene.render.filepath = str(render_dir / "compare-front.png")
    bpy.ops.render.render(write_still=True)
    for index, angle in enumerate((30, 120, 210, 300)):
        rad = math.radians(angle)
        setup_camera("TurntableCamera", (4.0 * math.sin(rad), 1.2, 4.0 * math.cos(rad)), (0, 1.2, 0), 3.15, 512)
        scene.render.filepath = str(render_dir / f"turn-{angle}.png")
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
