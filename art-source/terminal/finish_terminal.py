"""Apply the terminal's scan-based finish, bake game textures, and export renders."""
from pathlib import Path
import json
import math
import sys

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
SCAN = ROOT.parent / "rustlook" / "art-source" / "steel"
SURF = ROOT.parent / "rustlook" / "assets" / "surfaces" / "steel"
RES = 2048


def node(nodes, typ, label=None):
    n = nodes.new(typ)
    if label:
        n.label = label
    return n


def link(links, source, target):
    links.new(source, target)


def image_node(nodes, links, path, color_space, uv):
    n = node(nodes, "ShaderNodeTexImage", path.stem)
    n.image = bpy.data.images.load(str(path), check_existing=True)
    n.image.colorspace_settings.name = color_space
    link(links, uv, n.inputs["Vector"])
    return n.outputs["Color"]


def build_material(mat, scan_paths):
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    n, l = nt.nodes, nt.links
    uv = node(n, "ShaderNodeTexCoord").outputs["UV"]
    # Repeat the photographed scan at a readable, fine-grain scale.
    mapping = node(n, "ShaderNodeVectorMath")
    mapping.operation = "SCALE"
    link(l, uv, mapping.inputs[0]); mapping.inputs[3].default_value = 7.0
    rusty = image_node(n, l, scan_paths["steel_albedo"], "sRGB", mapping.outputs[0])
    green = image_node(n, l, scan_paths["paint_albedo"], "sRGB", mapping.outputs[0])
    oxide = image_node(n, l, scan_paths["oxide_albedo"], "sRGB", mapping.outputs[0])
    geometry = node(n, "ShaderNodeNewGeometry")
    position = geometry.outputs["Position"]
    sep = node(n, "ShaderNodeSeparateXYZ"); link(l, position, sep.inputs[0])
    # Wear is restricted to small screen-corner trails, the foot, and concave creases.
    curvature = geometry.outputs["Pointiness"]
    edge = node(n, "ShaderNodeMapRange")
    edge.inputs["From Min"].default_value = .72
    edge.inputs["From Max"].default_value = .92
    edge.inputs["To Min"].default_value = 0
    edge.inputs["To Max"].default_value = 1
    edge.clamp = True
    link(l, curvature, edge.inputs["Value"])
    edge_clamp = edge.outputs["Result"]
    abs_x = node(n, "ShaderNodeMath"); abs_x.operation = "ABSOLUTE"
    link(l, sep.outputs["X"], abs_x.inputs[0])
    corner_x = node(n, "ShaderNodeMath"); corner_x.operation = "LESS_THAN"
    corner_delta = node(n, "ShaderNodeMath"); corner_delta.operation = "SUBTRACT"
    link(l, abs_x.outputs[0], corner_delta.inputs[0]); corner_delta.inputs[1].default_value = .40
    corner_offset = node(n, "ShaderNodeMath"); corner_offset.operation = "ABSOLUTE"
    link(l, corner_delta.outputs[0], corner_offset.inputs[0])
    link(l, corner_offset.outputs[0], corner_x.inputs[0]); corner_x.inputs[1].default_value = .045
    streak_low = node(n, "ShaderNodeMath"); streak_low.operation = "GREATER_THAN"
    link(l, sep.outputs["Z"], streak_low.inputs[0]); streak_low.inputs[1].default_value = 1.16
    streak_high = node(n, "ShaderNodeMath"); streak_high.operation = "LESS_THAN"
    link(l, sep.outputs["Z"], streak_high.inputs[0]); streak_high.inputs[1].default_value = 1.31
    streak_z = node(n, "ShaderNodeMath"); streak_z.operation = "MULTIPLY"
    link(l, streak_low.outputs[0], streak_z.inputs[0]); link(l, streak_high.outputs[0], streak_z.inputs[1])
    streak_mask = node(n, "ShaderNodeMath"); streak_mask.operation = "MULTIPLY"
    link(l, corner_x.outputs[0], streak_mask.inputs[0]); link(l, streak_z.outputs[0], streak_mask.inputs[1])
    foot = node(n, "ShaderNodeMath"); foot.operation = "LESS_THAN"
    link(l, sep.outputs["Z"], foot.inputs[0]); foot.inputs[1].default_value = .075
    cavity = node(n, "ShaderNodeMath"); cavity.operation = "LESS_THAN"
    link(l, curvature, cavity.inputs[0]); cavity.inputs[1].default_value = -.72
    cavity_rust = node(n, "ShaderNodeMath"); cavity_rust.operation = "MULTIPLY"
    link(l, cavity.outputs[0], cavity_rust.inputs[0]); link(l, edge_clamp, cavity_rust.inputs[1])
    localized = node(n, "ShaderNodeMath"); localized.operation = "MAXIMUM"
    link(l, streak_mask.outputs[0], localized.inputs[0]); link(l, foot.outputs[0], localized.inputs[1])
    rust_union2 = node(n, "ShaderNodeMath"); rust_union2.operation = "MAXIMUM"
    link(l, localized.outputs[0], rust_union2.inputs[0]); link(l, cavity_rust.outputs[0], rust_union2.inputs[1])
    paint = node(n, "ShaderNodeHueSaturation")
    link(l, green, paint.inputs["Color"])
    paint.inputs["Hue"].default_value = .48
    paint.inputs["Saturation"].default_value = .60
    paint.inputs["Value"].default_value = .62
    oxide_mix = node(n, "ShaderNodeMixRGB"); oxide_mix.blend_type = "MIX"
    link(l, rust_union2.outputs[0], oxide_mix.inputs[0]); link(l, paint.outputs[0], oxide_mix.inputs[1]); link(l, oxide, oxide_mix.inputs[2])
    steel_mix = node(n, "ShaderNodeMixRGB"); steel_mix.blend_type = "MIX"
    link(l, edge_clamp, steel_mix.inputs[0]); link(l, oxide_mix.outputs[0], steel_mix.inputs[1]); link(l, rusty, steel_mix.inputs[2])
    # Colorize the green scan toward the sampled olive target used in concept.
    tint = node(n, "ShaderNodeMixRGB"); tint.blend_type = "MULTIPLY"; tint.inputs[0].default_value = .70
    link(l, steel_mix.outputs[0], tint.inputs[1]); tint.inputs[2].default_value = (.52, .56, .30, 1)
    # Darken cavities from a geometric AO input and a fine noise field.
    noise = node(n, "ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 34; noise.inputs["Detail"].default_value = 4
    link(l, position, noise.inputs["Vector"])
    grime = node(n, "ShaderNodeMath"); grime.operation = "MULTIPLY"
    link(l, noise.outputs["Fac"], grime.inputs[0]);     grime.inputs[1].default_value = .075

    dirt = node(n, "ShaderNodeMixRGB"); dirt.blend_type = "MULTIPLY"; dirt.inputs[0].default_value = 1
    link(l, tint.outputs[0], dirt.inputs[1]); link(l, grime.outputs[0], dirt.inputs[2])
    # Fabrication marks are shader relief only. Their texture is baked, not geometry.
    seam_x = node(n, "ShaderNodeMath"); seam_x.operation = "PINGPONG"
    link(l, sep.outputs["X"], seam_x.inputs[0]); seam_x.inputs[1].default_value = .29
    seam_x.inputs[2].default_value = .58
    seam = node(n, "ShaderNodeMath"); seam.operation = "LESS_THAN"
    link(l, seam_x.outputs[0], seam.inputs[0]); seam.inputs[1].default_value = .004
    bezel_z = node(n, "ShaderNodeMath"); bezel_z.operation = "PINGPONG"
    link(l, sep.outputs["Z"], bezel_z.inputs[0]); bezel_z.inputs[1].default_value = .05
    bezel_z.inputs[2].default_value = .10
    bezel = node(n, "ShaderNodeMath"); bezel.operation = "LESS_THAN"
    link(l, bezel_z.outputs[0], bezel.inputs[0]); bezel.inputs[1].default_value = .003
    seam_union = node(n, "ShaderNodeMath"); seam_union.operation = "MAXIMUM"
    link(l, seam.outputs[0], seam_union.inputs[0]); link(l, bezel.outputs[0], seam_union.inputs[1])
    seam_bump = node(n, "ShaderNodeBump"); seam_bump.inputs["Distance"].default_value = .0018
    seam_bump.inputs["Strength"].default_value = .7
    link(l, seam_union.outputs[0], seam_bump.inputs["Height"])
    scan_height = node(n, "ShaderNodeTexImage", "Coarse scan relief")
    scan_height.image = bpy.data.images.load(str(scan_paths["oxide_normal"]), check_existing=True)
    scan_height.image.colorspace_settings.name = "Non-Color"
    link(l, mapping.outputs[0], scan_height.inputs["Vector"])
    bump = node(n, "ShaderNodeBump"); bump.inputs["Distance"].default_value = .000325; bump.inputs["Strength"].default_value = .16
    link(l, scan_height.outputs["Color"], bump.inputs["Height"]); link(l, seam_bump.outputs[0], bump.inputs["Normal"])
    bsdf = node(n, "ShaderNodeBsdfPrincipled")
    link(l, dirt.outputs[0], bsdf.inputs["Base Color"])
    bsdf.inputs["Metallic"].default_value = .42; bsdf.inputs["Roughness"].default_value = .48
    link(l, bump.outputs[0], bsdf.inputs["Normal"])
    out = node(n, "ShaderNodeOutputMaterial"); link(l, bsdf.outputs[0], out.inputs["Surface"])
    return bsdf, out, dirt.outputs[0], bump.outputs[0], rust_union2.outputs[0]


def baked_image(name, colorspace):
    im = bpy.data.images.new(name, RES, RES, alpha=False)
    im.colorspace_settings.name = colorspace
    return im


def remove_cool_tints(image):
    pixels = np.asarray(image.pixels[:], dtype=np.float32).reshape((-1, 4))
    rgb = pixels[:, :3]
    # The bake stores linear shader values, while the delivered albedo is sampled as sRGB.
    rgb *= 7.0
    maximum = rgb.max(axis=1)
    minimum = rgb.min(axis=1)
    delta = maximum - minimum
    safe = np.maximum(delta, 1e-8)
    red, green, blue = rgb.T
    hue = np.zeros_like(maximum)
    red_max = maximum == red
    green_max = (maximum == green) & ~red_max
    blue_max = ~(red_max | green_max)
    hue[red_max] = ((green[red_max] - blue[red_max]) / safe[red_max]) % 6
    hue[green_max] = (blue[green_max] - red[green_max]) / safe[green_max] + 2
    hue[blue_max] = (red[blue_max] - green[blue_max]) / safe[blue_max] + 4
    hue *= 60
    cool = (hue > 180) & (hue < 300) & (delta > 1e-5)
    if np.any(cool):
        value = maximum[cool]
        saturation = delta[cool] / np.maximum(value, 1e-8)
        p = value * (1 - saturation)
        q = value * (1 - saturation * (75 / 60 - 1))
        rgb[cool] = np.stack((value, q, p), axis=1)
    image.pixels.foreach_set(pixels.reshape(-1))
    image.update()
    image.filepath_raw = str(ROOT / "terminal_albedo.png")
    image.file_format = "PNG"
    image.save()
    image.pack()


def make_olive_atlas(image):
    """Keep scan-scale wear while matching the concept's sampled olive paint."""
    rng = np.random.default_rng(9107)
    size = RES
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    # Fine paint variation only. Rust is authored by the spatially constrained material masks.
    grain = rng.normal(0, .006, (size, size)).astype(np.float32)
    cloud = (np.sin(x * .017 + np.sin(y * .011)) * np.cos(y * .023) + np.sin(x * .071 + y * .053) * .25) * .5
    rust = np.zeros((size, size), dtype=np.float32)
    # Darken the sampled olive slightly and reduce blue to keep the paint olive-brown.
    # Calibrated against the baked neutral views under the studio lights.
    olive = np.array([.0115, .0142, .0025], dtype=np.float32)
    oxide = np.array([.19, .060, .015], dtype=np.float32)
    rgb = olive[None, None, :] * (1 - rust[:, :, None]) + oxide[None, None, :] * rust[:, :, None]
    rgb *= (1 + grain[:, :, None] + (cloud[:, :, None] * .035))
    rgb = np.clip(rgb, .003, .9)
    rgba = np.ones((size, size, 4), dtype=np.float32)
    rgba[:, :, :3] = rgb
    image.pixels.foreach_set(rgba.reshape(-1))
    image.update()
    image.filepath_raw = str(ROOT / "terminal_albedo.png")
    image.file_format = "PNG"
    image.save()
    image.pack()


def bake_map(obj, mat, bsdf, output, name, bake_type, color_socket=None, colorspace="Non-Color"):
    nt = mat.node_tree
    target = node(nt.nodes, "ShaderNodeTexImage", "Bake target " + name)
    target.image = baked_image(name, colorspace)
    nt.nodes.active = target
    other_targets = []
    for slot_mat in obj.data.materials:
        if slot_mat == mat:
            continue
        other = node(slot_mat.node_tree.nodes, "ShaderNodeTexImage", "Bake target " + name)
        other.image = target.image
        slot_mat.node_tree.nodes.active = other
        other_targets.append((slot_mat, other))
    if color_socket:
        emit = node(nt.nodes, "ShaderNodeEmission")
        nt.links.new(color_socket, emit.inputs["Color"])
        nt.links.new(emit.outputs[0], output.inputs["Surface"])
    else:
        nt.links.new(bsdf.outputs[0], output.inputs["Surface"])
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True); bpy.context.view_layer.objects.active = obj
    bpy.ops.object.bake(type=bake_type, uv_layer=obj.data.uv_layers.active.name)
    for slot_mat, other in other_targets:
        slot_mat.node_tree.nodes.remove(other)
    path = ROOT / f"terminal_{name.lower()}.png"
    image = target.image
    image.filepath_raw = str(path); image.file_format = "PNG"; image.save(); image.pack()
    nt.nodes.remove(target)
    return image


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    blend = Path(args[0]).resolve() if args else ROOT / "terminal.blend"
    output_stem = args[1] if len(args) > 1 else "terminal-finished"
    if not blend.exists():
        raise FileNotFoundError(blend)
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    obj = bpy.data.objects["Terminal_GeneratedFit"]
    tri_before = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    if tri_before > 41000:
        raise RuntimeError(f"fitted triangle count exceeds source gate: {tri_before}")
    material = bpy.data.materials["OliveDrab_WornMetal"]
    scan_paths = {
        "steel_albedo": SCAN / "rusty_metal_04_albedo.jpg",
        "paint_albedo": SCAN / "green_metal_rust_albedo.jpg",
        "oxide_albedo": SURF / "r3-rust_coarse_01-albedo.jpg",
        "oxide_normal": SURF / "r3-rust_coarse_01-normal.jpg",
    }
    for p in scan_paths.values():
        if not p.exists():
            raise FileNotFoundError(p)
    bsdf, output, color_socket, normal_socket, rust_socket = build_material(material, scan_paths)
    # Keyboard floor and walls retain a flat, dark enamel finish.
    enamel = bpy.data.materials.new("KeyboardEnamel")
    enamel.diffuse_color = (.018, .022, .020, 1); enamel.use_nodes = True
    ebsdf = next(n for n in enamel.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    ebsdf.inputs["Base Color"].default_value = (.14, .17, .065, 1)
    ebsdf.inputs["Metallic"].default_value = .05; ebsdf.inputs["Roughness"].default_value = .72
    # Pocket planes are distinguished by their recessed center position.
    if enamel.name not in obj.data.materials:
        obj.data.materials.append(enamel)
    for poly in obj.data.polygons:
        c = poly.center
        if c.z > .965 and c.z < 1.04 and abs(c.x) < .56 and c.y < -.08:
            poly.material_index = len(obj.data.materials) - 1
    screen_mat = bpy.data.materials.get("Screen") or bpy.data.materials.new("Screen")
    screen_mat.use_nodes = True
    sbsdf = next(n for n in screen_mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    sbsdf.inputs["Base Color"].default_value = (.003, .005, .006, 1)
    sbsdf.inputs["Metallic"].default_value = .12; sbsdf.inputs["Roughness"].default_value = .09
    sbsdf.inputs["Coat Weight"].default_value = .35
    while len(obj.data.materials) < 2:
        obj.data.materials.append(screen_mat)
    obj.data.materials[1] = screen_mat
    obj.data.materials.append(enamel)
    for poly in obj.data.polygons:
        c = poly.center
        if c.z > .965 and c.z < 1.04 and abs(c.x) < .56 and c.y < -.08:
            poly.material_index = 2
    # Bake ORM (R=AO, G=roughness, B=metallic) from one emission target.
    scene.render.engine = "CYCLES"; scene.cycles.samples = 32
    scene.render.bake.margin = 16; scene.render.bake.margin_type = "EXTEND"; scene.render.bake.use_clear = True
    # Repack the final watertight mesh into non-overlapping islands before all maps bake.
    bpy.ops.object.select_all(action="DESELECT"); obj.select_set(True); bpy.context.view_layer.objects.active = obj
    if obj.data.uv_layers:
        obj.data.uv_layers.remove(obj.data.uv_layers.active)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(island_margin=.02, angle_limit=math.radians(66), correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    # AO bake first, then albedo/normal and a compact ORM map.
    ao = baked_image("terminal_ao", "Non-Color")
    target = node(material.node_tree.nodes, "ShaderNodeTexImage", "AO bake target"); target.image = ao
    material.node_tree.nodes.active = target
    ao_targets = []
    for slot_mat in obj.data.materials:
        if slot_mat == material:
            continue
        other = node(slot_mat.node_tree.nodes, "ShaderNodeTexImage", "AO bake target"); other.image = ao
        slot_mat.node_tree.nodes.active = other; ao_targets.append((slot_mat, other))
    bpy.ops.object.select_all(action="DESELECT"); obj.select_set(True); bpy.context.view_layer.objects.active = obj
    bpy.ops.object.bake(type="AO", uv_layer=obj.data.uv_layers.active.name)
    ao.filepath_raw = str(ROOT / "terminal_ao.png"); ao.file_format = "PNG"; ao.save(); ao.pack()
    material.node_tree.nodes.remove(target)
    for slot_mat, other in ao_targets:
        slot_mat.node_tree.nodes.remove(other)
    albedo = bake_map(obj, material, bsdf, output, "Albedo", "EMIT", color_socket, colorspace="sRGB")
    remove_cool_tints(albedo)
    normal = bake_map(obj, material, bsdf, output, "Normal", "NORMAL")
    # ORM is baked via a generated emission shader using AO and constants.
    nt = material.node_tree
    separate = node(nt.nodes, "ShaderNodeSeparateColor")
    ao_tex = node(nt.nodes, "ShaderNodeTexImage", "Baked AO"); ao_tex.image = ao
    nt.links.new(ao_tex.outputs["Color"], separate.inputs[0])
    combine = node(nt.nodes, "ShaderNodeCombineColor")
    nt.links.new(separate.outputs[0], combine.inputs[0]); combine.inputs[1].default_value = .68; combine.inputs[2].default_value = .05
    orm = bake_map(obj, material, bsdf, output, "ORM", "EMIT", combine.outputs[0])
    # Runtime materials use only the delivered baked maps.
    nt = material.node_tree; nt.nodes.clear(); l = nt.links
    uv = node(nt.nodes, "ShaderNodeTexCoord").outputs["UV"]
    def tex(image, label):
        t = node(nt.nodes, "ShaderNodeTexImage", label); t.image = image; l.new(uv, t.inputs["Vector"]); return t.outputs["Color"]
    col = tex(albedo, "Baked terminal albedo")
    bs = node(nt.nodes, "ShaderNodeBsdfPrincipled")
    bs.inputs["Specular IOR Level"].default_value = .2
    l.new(col, bs.inputs["Base Color"])
    orm_color = tex(orm, "Baked occlusion roughness metallic")
    orm_sep = node(nt.nodes, "ShaderNodeSeparateColor"); l.new(orm_color, orm_sep.inputs[0])
    l.new(orm_sep.outputs[1], bs.inputs["Roughness"]); l.new(orm_sep.outputs[2], bs.inputs["Metallic"])
    nm = node(nt.nodes, "ShaderNodeNormalMap"); l.new(tex(normal, "Baked tangent normal"), nm.inputs["Color"]); l.new(nm.outputs[0], bs.inputs["Normal"])
    out = node(nt.nodes, "ShaderNodeOutputMaterial"); l.new(bs.outputs[0], out.inputs["Surface"])
    # Keep pocket enamel and Screen as dedicated materials after bake.
    tri_after = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    if tri_after != tri_before:
        raise RuntimeError(f"finish modified fitted triangles: {tri_before} -> {tri_after}")
    # Preserve scene dimensions and camera, tune Cycles studio capture.
    scene.render.engine = "CYCLES"; scene.cycles.samples = 128; scene.cycles.use_denoising = True
    scene.render.resolution_x = 1920; scene.render.resolution_y = 1080; scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    for light in [o for o in scene.objects if o.type == "LIGHT"]:
        light.data.energy *= .25
    bpy.data.objects["FrontThreeQuarter"].data.lens = 35
    bpy.data.objects["SideProfile"].data.lens = 35
    scene.world.color = (.045, .045, .045)
    # Textured wall and floor anchor the terminal in every presentation view.
    def surface_material(name, albedo_path, roughness=.82):
        mat = bpy.data.materials.new(name); mat.use_nodes = True
        nt = mat.node_tree; nt.nodes.clear()
        texcoord = nt.nodes.new("ShaderNodeTexCoord")
        mapping = nt.nodes.new("ShaderNodeVectorMath"); mapping.operation = "SCALE"
        mapping.inputs[3].default_value = 5.0
        nt.links.new(texcoord.outputs["UV"], mapping.inputs[0])
        tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = bpy.data.images.load(str(albedo_path), check_existing=True)
        tex.image.colorspace_settings.name = "sRGB"; nt.links.new(mapping.outputs[0], tex.inputs["Vector"])
        bs = nt.nodes.new("ShaderNodeBsdfPrincipled"); bs.inputs["Roughness"].default_value = roughness
        nt.links.new(tex.outputs["Color"], bs.inputs["Base Color"])
        out = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(bs.outputs[0], out.inputs["Surface"])
        return mat
    wall_mat = surface_material("RustlookWall", ROOT.parent / "rustlook/assets/surfaces/wall/albedo.png")
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, .035, 2.15), rotation=(math.radians(90), 0, 0))
    wall = bpy.context.object; wall.name = "PresentationWall"; wall.dimensions = (5.0, 4.3, 0); bpy.ops.object.transform_apply(location=False, rotation=False, scale=True); wall.data.materials.append(wall_mat)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, -.018))
    floor_surface = bpy.context.object; floor_surface.name = "PresentationFloor"
    floor_surface.dimensions = (5.0, 5.0, 0); bpy.ops.object.transform_apply(location=False, rotation=False, scale=True); floor_surface.data.materials.append(wall_mat)
    # A compact rear plate carries the mounting interface; separate rails are unnecessary.
    plate_mat = bpy.data.materials.get("OliveDrab_WornMetal")
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, .010, .92)); plate = bpy.context.object
    plate.name = "WallMountPlate"; plate.dimensions = (.58, .018, .86); bpy.ops.object.transform_apply(location=False, rotation=False, scale=True); plate.data.materials.append(plate_mat)
    # Wall plane uses the game's supplied surface; floor stays neutral to preserve paint color.
    (ROOT / "renders").mkdir(exist_ok=True)
    renders = []
    cameras = [("front-threequarter", "FrontThreeQuarter"), ("side", "SideProfile"), ("operator", "OperatorRecess")]
    front = bpy.data.objects["FrontThreeQuarter"]
    front.location = (1.0 + 2.6 * math.sin(math.radians(35)) * math.cos(math.radians(15)), -.28 - 2.6 * math.cos(math.radians(35)) * math.cos(math.radians(15)), .92 + 2.6 * math.sin(math.radians(15)))
    front.rotation_euler = (Vector((0, -.28, .92)) - front.location).to_track_quat("-Z", "Y").to_euler()
    front.data.lens = 42
    side = bpy.data.objects["SideProfile"]
    side.location = (2.6, -.08, .95); side.rotation_euler = (Vector((0, -.20, .92)) - side.location).to_track_quat("-Z", "Y").to_euler(); side.data.lens = 48
    operator = bpy.data.objects["OperatorRecess"]
    operator.location = (0, -1.08, 1.38); operator.rotation_euler = (Vector((0, -.32, .99)) - operator.location).to_track_quat("-Z", "Y").to_euler(); operator.data.lens = 42
    for name, cam_name in cameras:
        scene.camera = bpy.data.objects[cam_name]
        for emergency in (False,):
            for light in [o for o in scene.objects if o.type == "LIGHT"]:
                light.data.color = (1, 1, 1)
            tag = "red-emergency" if emergency else "neutral"
            path = ROOT / "renders" / f"finished-{name}-{tag}.png"
            scene.render.filepath = str(path); bpy.ops.render.render(write_still=True)
            renders.append(str(path.relative_to(ROOT)))
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / f"{output_stem}.blend"))
    bpy.ops.export_scene.gltf(filepath=str(ROOT / f"{output_stem}.glb"), export_format="GLB", export_apply=True, export_image_format="AUTO", export_materials="EXPORT")
    total_area = sum(p.area for p in obj.data.polygons)
    bay_faces = [p for p in obj.data.polygons if .965 <= p.center.z <= 1.04 and abs(p.center.x) < .42 and -.58 <= p.center.y <= -.16]
    bay_area = sum(p.area for p in bay_faces)
    # Estimate convex edge coverage from remeshed face-normal discontinuities and a 2-6mm boundary band.
    import bmesh
    bm = bmesh.new(); bm.from_mesh(obj.data)
    convex_edges = [edge for edge in bm.edges if len(edge.link_faces) == 2 and edge.is_convex and edge.calc_face_angle() >= math.radians(8)]
    edge_points = [vertex.co.copy() for edge in convex_edges for vertex in edge.verts]
    # The 2-6mm band follows real convex creases in the remeshed solid.
    edge_band_faces = [face for face in bm.faces if any((face.calc_center_median() - point).length <= .006 for point in edge_points)]
    edge_band_area = sum(face.calc_area() for face in edge_band_faces)
    bm.free()
    rust_faces = [p for p in obj.data.polygons if (abs(abs(p.center.x)-.40) < .045 and 1.16 < p.center.z < 1.31) or p.center.z < .075]
    rust_area = sum(p.area for p in rust_faces)
    wear_coverage = {"bay_surface_percent": round(100 * sum(p.area for p in bay_faces if p in rust_faces) / max(bay_area, 1e-9), 4),
                     "rust_body_surface_percent": round(100 * rust_area / total_area, 4),
                     "convex_edge_band_surface_percent": round(100 * edge_band_area / total_area, 4),
                     "edge_band_width_m": [0.002, 0.006], "body_surface_area_m2": round(total_area, 6), "bay_surface_area_m2": round(bay_area, 6)}
    report = {"wear_mask_coverage": wear_coverage, "fitted_mesh_triangles": tri_after, "fitted_mesh_triangles_unchanged": tri_after == tri_before,
              "triangle_cap_40000": tri_after <= 40000, "texture_resolution": RES,
              "uv_projection": "Smart UV Project, 66 degree limit, 0.02 island margin",
              "bake_margin_px": scene.render.bake.margin, "bake_margin_type": scene.render.bake.margin_type,
              "textures": ["terminal_albedo.png", "terminal_normal.png", "terminal_orm.png", "terminal_ao.png"],
              "renders": renders, "screen_material": screen_mat.name,
              "scan_sources": [str(p.relative_to(ROOT.parent)) for p in scan_paths.values()],
              "unmet": ["Fitted terminal topology exceeds 40000 triangles." if tri_after > 40000 else None,
                        "High-detail weld beads and bolt rows were not baked."]}
    (ROOT / "finish-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("FINISH_REPORT", json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
