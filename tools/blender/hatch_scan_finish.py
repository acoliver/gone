"""Offline scan-layer material. All model masks disappear into the shared atlas."""
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[2]
SCAN_ROOT = ROOT / "assets/surfaces/steel"
SCANS = {
    "steel": (ROOT / "art-source/steel/rusty_metal_04_albedo.jpg", SCAN_ROOT / "rusty_metal_04_normal.jpg", SCAN_ROOT / "rusty_metal_04_orm.jpg"),
    "paint": (ROOT / "art-source/steel/green_metal_rust_albedo.jpg", SCAN_ROOT / "green_metal_rust_normal.jpg", SCAN_ROOT / "green_metal_rust_orm.jpg"),
    "oxide": (SCAN_ROOT / "r3-rust_coarse_01-albedo.jpg", SCAN_ROOT / "r3-rust_coarse_01-normal.jpg", SCAN_ROOT / "rusty_painted_metal_orm.jpg"),
}


def build(mat, baked_ao=None, context=None):
    nt = mat.node_tree
    nt.nodes.clear()
    n, l = nt.nodes, nt.links

    def node(kind, **values):
        item = n.new(kind)
        for key, value in values.items():
            setattr(item, key, value)
        return item

    def math(op, a, b=None):
        item = node("ShaderNodeMath", operation=op)
        for i, value in enumerate((a, b)):
            if value is None:
                continue
            if isinstance(value, (float, int)):
                item.inputs[i].default_value = value
            else:
                l.new(value, item.inputs[i])
        return item.outputs[0]

    def mix(factor, a, b):
        item = node("ShaderNodeMixRGB", blend_type="MIX")
        for index, (socket, value) in enumerate(zip(item.inputs, (factor, a, b))):
            if isinstance(value, tuple):
                socket.default_value = (*value, 1)
            elif isinstance(value, (float, int)):
                socket.default_value = value if index == 0 else (value, value, value, 1)
            else:
                l.new(value, socket)
        return item.outputs[0]

    def vector(op, a, b=None):
        item = node("ShaderNodeVectorMath", operation=op)
        for i, value in enumerate((a, b)):
            if value is None:
                continue
            if isinstance(value, tuple):
                item.inputs[i].default_value = value
            else:
                l.new(value, item.inputs[i])
        return item.outputs[0]

    def attr(name):
        return node("ShaderNodeAttribute", attribute_name=name).outputs["Fac"]

    def channels(value):
        item = node("ShaderNodeSeparateColor")
        l.new(value, item.inputs[0])
        return item.outputs[:3]

    def texture(path, coords=None, color=False):
        item = node("ShaderNodeTexImage", label=path.name)
        item.image = bpy.data.images.load(str(path), check_existing=True)
        item.image.colorspace_settings.name = "sRGB" if color else "Non-Color"
        if coords is not None:
            l.new(coords, item.inputs["Vector"])
        return item.outputs["Color"]

    geometry = node("ShaderNodeNewGeometry")
    position = geometry.outputs["Position"]
    xyz = node("ShaderNodeSeparateXYZ")
    l.new(position, xyz.inputs[0])
    coords = node("ShaderNodeCombineXYZ")
    l.new(math("MULTIPLY", xyz.outputs["X"], .38), coords.inputs[0])
    l.new(math("MULTIPLY", xyz.outputs["Z"], .38), coords.inputs[1])
    uv = coords.outputs[0]
    scans = {}
    for role, paths in SCANS.items():
        scans[role] = (texture(paths[0], uv, True), texture(paths[1], uv), channels(texture(paths[2], uv)))

    contact, drips, bottom = 0, 0, 0
    if context is not None:
        image, (xlo, xspan, zspan) = context
        weather_uv = node("ShaderNodeCombineXYZ")
        l.new(math("DIVIDE", math("SUBTRACT", xyz.outputs["X"], xlo), xspan), weather_uv.inputs[0])
        l.new(math("DIVIDE", xyz.outputs["Z"], zspan), weather_uv.inputs[1])
        item = node("ShaderNodeTexImage", label="Exported fastener contact / downward trails / bottom grime")
        item.image = image
        item.extension = "EXTEND"
        l.new(weather_uv.outputs[0], item.inputs["Vector"])
        contact, drips, bottom = channels(item.outputs["Color"])
    occluded = 0
    if baked_ao is not None:
        item = node("ShaderNodeTexImage", label="Baked geometric crevices")
        item.image = baked_ao
        occluded = math("SUBTRACT", 1, item.outputs["Color"])
    curvature = geometry.outputs["Pointiness"]
    edge = math("MINIMUM", math("MULTIPLY", math("ABSOLUTE", math("SUBTRACT", curvature, .5)), 8), 1)
    relief = attr("relief")
    chip = attr("chip_edge")
    bloom = math("MAXIMUM", contact, math("MULTIPLY", drips, .8))
    oxide_mask = math("MINIMUM", math("ADD", math("MULTIPLY", bloom, .8), math("MAXIMUM", chip, math("MULTIPLY", edge, .4))), 1)
    oxide_mask = math("MAXIMUM", oxide_mask, math("MULTIPLY", attr("substrate"), .35))
    # Connected model sheets determine paint survival. The scans retain the
    # pits and grain without scattering separate high-contrast paint islands.
    paint_mask = math("MULTIPLY", attr("painted"), math("MAXIMUM", attr("flake"), math("MULTIPLY", edge, .13)))
    paint_mask = math("MULTIPLY", paint_mask, math("SUBTRACT", 1, oxide_mask))
    steel, paint, oxide = scans["steel"], scans["paint"], scans["oxide"]
    def weathered_scan(colour, saturation, value):
        toned = node("ShaderNodeHueSaturation")
        if isinstance(saturation, (float, int)):
            toned.inputs["Saturation"].default_value = saturation
        else:
            l.new(saturation, toned.inputs["Saturation"])
        toned.inputs["Value"].default_value = value
        l.new(colour, toned.inputs["Color"])
        # Compress the photographed pale peaks, preserving scan colour ratios.
        peak = node("ShaderNodeRGBToBW")
        l.new(toned.outputs[0], peak.inputs[0])
        gain = math("DIVIDE", math("MINIMUM", peak.outputs[0], .105), math("MAXIMUM", peak.outputs[0], .0001))
        product = node("ShaderNodeMixRGB", blend_type="MULTIPLY")
        product.inputs[0].default_value = 1
        l.new(toned.outputs[0], product.inputs[1]); l.new(gain, product.inputs[2])
        return product.outputs[0]
    substrate_chroma = math("ADD", 1.12, math("MULTIPLY", attr("substrate"), 1.1))
    base_scan = weathered_scan(steel[0], substrate_chroma, .78)
    old_paint = mix(.45, base_scan, weathered_scan(paint[0], .65, .70))
    colour = mix(oxide_mask, base_scan, weathered_scan(oxide[0], 1.0, .70))
    colour = mix(paint_mask, colour, old_paint)
    # A small neutral substrate contribution comes from the photographed steel,
    # retaining its texture rather than flattening machined parts to one colour.
    substrate = node("ShaderNodeHueSaturation")
    substrate.inputs["Saturation"].default_value = .20
    l.new(steel[0], substrate.inputs["Color"])
    wear = math("MULTIPLY", attr("machined"), math("MAXIMUM", edge, .55))
    colour = mix(wear, colour, substrate.outputs[0])
    # Worn yellow is a translucent paint over the same scan, with breaks from
    # source texture and model edges. It never reaches the carrier's outer edge.
    scan_luma = node("ShaderNodeRGBToBW")
    l.new(steel[0], scan_luma.inputs[0])
    wave = node("ShaderNodeTexWave", wave_type="BANDS", bands_direction="DIAGONAL")
    l.new(position, wave.inputs["Vector"])
    wave.inputs["Scale"].default_value = 13
    stripe = math("GREATER_THAN", wave.outputs["Fac"], .65)
    tint = mix(stripe, (.035, .030, .020), (.90, .60, .10))
    multiply = node("ShaderNodeMixRGB", blend_type="MULTIPLY")
    multiply.inputs[0].default_value = 1
    l.new(steel[0], multiply.inputs[1]); l.new(tint, multiply.inputs[2])
    band_edge = math("ABSOLUTE", attr("band_coordinate"))
    width = math("LESS_THAN", band_edge, .52)
    intact = math("GREATER_THAN", scan_luma.outputs[0], .18)
    intact = math("MULTIPLY", intact, math("SUBTRACT", 1, bloom))
    carrier = mix(bloom, substrate.outputs[0], oxide[0])
    failed_paint = mix(width, carrier, oxide[0])
    tape = mix(math("MULTIPLY", width, intact), failed_paint, multiply.outputs[0])
    colour = mix(attr("hazard"), colour, tape)
    grime = math("MINIMUM", math("ADD", math("MULTIPLY", occluded, .65), math("ADD", math("MULTIPLY", bottom, .65), math("MULTIPLY", drips, .30))), .80)
    dirt = node("ShaderNodeMixRGB", blend_type="MULTIPLY")
    dirt.inputs[0].default_value = 1
    l.new(colour, dirt.inputs[1]); l.new(math("SUBTRACT", 1, grime), dirt.inputs[2])
    colour = dirt.outputs[0]
    rough = mix(oxide_mask, steel[2][1], oxide[2][1])
    rough = mix(paint_mask, rough, paint[2][1])
    wet = math("MULTIPLY", oxide_mask, math("MULTIPLY", relief, .7))
    rough = math("MAXIMUM", math("SUBTRACT", rough, math("MULTIPLY", wet, .4)), .24)
    metallic = mix(oxide_mask, math("MULTIPLY", steel[2][2], .55), 0)
    normal_colour = mix(oxide_mask, steel[1], oxide[1])
    normal_colour = mix(paint_mask, normal_colour, paint[1])
    nx, ny, nz = channels(normal_colour)
    continuous = mix(attr("frame_smooth"), geometry.outputs["Normal"], node("ShaderNodeAttribute", attribute_name="frame_normal").outputs["Vector"])
    normal = vector("NORMALIZE", continuous)
    normal_xyz = node("ShaderNodeSeparateXYZ"); l.new(normal, normal_xyz.inputs[0])
    horizontal = math("GREATER_THAN", math("ABSOLUTE", normal_xyz.outputs["Z"]), .95)
    up = mix(horizontal, (0, 0, 1), (1, 0, 0))
    tangent = vector("NORMALIZE", vector("CROSS_PRODUCT", up, normal))
    bitangent = vector("CROSS_PRODUCT", normal, tangent)

    def scale(v, factor):
        item = node("ShaderNodeVectorMath", operation="SCALE")
        l.new(v, item.inputs[0]); l.new(factor, item.inputs[3])
        return item.outputs[0]

    normal = vector("NORMALIZE", vector("ADD", scale(normal, math("MAXIMUM", math("SUBTRACT", math("MULTIPLY", nz, 2), 1), .1)),
                     vector("ADD", scale(tangent, math("SUBTRACT", math("MULTIPLY", nx, 2), 1)), scale(bitangent, math("SUBTRACT", math("MULTIPLY", ny, 2), 1)))))
    bump = node("ShaderNodeBump")
    bump.inputs["Distance"].default_value = .0012
    bump.inputs["Strength"].default_value = .5
    height = math("ADD", math("MULTIPLY", relief, .7), math("MULTIPLY", scan_luma.outputs[0], .3))
    l.new(height, bump.inputs["Height"]); l.new(normal, bump.inputs["Normal"])
    bsdf = node("ShaderNodeBsdfPrincipled")
    l.new(colour, bsdf.inputs["Base Color"]); l.new(rough, bsdf.inputs["Roughness"])
    l.new(metallic, bsdf.inputs["Metallic"]); l.new(bump.outputs[0], bsdf.inputs["Normal"])
    output = node("ShaderNodeOutputMaterial")
    l.new(bsdf.outputs[0], output.inputs["Surface"])
    # Runtime colour and grain stay in tiled scans. The atlas stores only
    # geometry-owned layer weights, weather accumulation and continuous relief.
    masks = node("ShaderNodeCombineColor")
    for socket, value in zip(masks.inputs, (paint_mask, oxide_mask, wear)):
        l.new(value, socket)
    weather = node("ShaderNodeCombineColor")
    for socket, value in zip(weather.inputs, (grime, math("MULTIPLY", attr("hazard"), width), attr("band_coordinate"))):
        l.new(value, socket)
    geometry_bump = node("ShaderNodeBump")
    geometry_bump.inputs["Distance"].default_value = .0012
    geometry_bump.inputs["Strength"].default_value = .5
    l.new(math("MULTIPLY", relief, .7), geometry_bump.inputs["Height"])
    l.new(continuous, geometry_bump.inputs["Normal"])
    return {"albedo": colour, "roughness": rough, "metallic": metallic,
            "height": height, "curvature": curvature, "bsdf": bsdf, "output": output,
            "layer_masks": masks.outputs[0], "weather_masks": weather.outputs[0],
            "geometry_normal": geometry_bump.outputs[0]}
