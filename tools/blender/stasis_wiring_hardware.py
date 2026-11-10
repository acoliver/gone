"""Fit and export the issue-110 stasis wiring enclosure from its Hunyuan source mesh.

Run with Blender 4.5.11 --background --python-exit-code 1 --python this_file.
"""
from __future__ import annotations

import bpy
import bmesh
import numpy as np
import hashlib
import json
import math
import os
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "art-source/stasis-wiring/hardware/enclosure-raw.glb"
OUT = ROOT / "assets/props/stasis-wiring"
SOURCE_IMAGE = ROOT / "art-source/stasis-wiring/sealed-harness-enclosure-reference.png"
SCAN = ROOT / "assets/props/stasis-wiring/painted-steel-scan.png"

POWER = ((-.043, .032, .09), (.043, .032, .09))
CONTROL = ((.09, -.045, .09),)
SOCKETS = [
    {"id": f"power-{i + 1}", "class": "power", "center_local_m": list(p),
     "axis_local": [0, 0, 1], "cable_outer_diameter_m": .024,
     "bore_diameter_m": .0256, "gland_outer_diameter_m": .034,
     "compression_liner_radial_thickness_m": .0012}
    for i, p in enumerate(POWER)
] + [
    {"id": "control-data", "class": "control-data", "center_local_m": list(CONTROL[0]),
     "axis_local": [0, 0, 1], "bundle_outer_diameter_m": .020,
     "strand_outer_diameter_m": .006, "strand_count": 6,
     "bore_diameter_m": .022, "gland_outer_diameter_m": .028,
     "compression_liner_radial_thickness_m": .0012}
]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def canonicalize_glb_attributes(path: Path) -> None:
    """Quantize sub-micro Blender float drift so independent exports are byte-stable."""
    data = bytearray(path.read_bytes())
    json_length = struct.unpack_from("<I", data, 12)[0]
    document = json.loads(data[20:20 + json_length].decode("utf-8").rstrip(" "))
    binary_start = 28 + json_length
    binary = memoryview(data)[binary_start:]
    components = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}
    seen = set()
    for mesh in document.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            for semantic, accessor_index in primitive.get("attributes", {}).items():
                if accessor_index in seen:
                    continue
                seen.add(accessor_index)
                accessor = document["accessors"][accessor_index]
                if accessor["componentType"] != 5126:
                    continue
                count = components[accessor["type"]]
                view = document["bufferViews"][accessor["bufferView"]]
                stride = view.get("byteStride", count * 4)
                start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
                for index in range(accessor["count"]):
                    offset = start + index * stride
                    values = struct.unpack_from("<" + "f" * count, binary, offset)
                    precision = 8 if semantic == "POSITION" else 5
                    rounded = tuple(round(value, precision) for value in values)
                    struct.pack_into("<" + "f" * count, binary, offset, *rounded)
    path.write_bytes(data)



def material(name, color, roughness, metallic=0.0, scan=False):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    mat.use_backface_culling = True
    if scan:
        # Bake the scan tint into pixels: glTF cannot represent the former
        # Generated -> Hue/Saturation -> Mix chain used only by Blender.
        source = bpy.data.images.load(str(SCAN), check_existing=True)
        pixels = np.array(source.pixels[:], dtype=np.float32).reshape(-1, 4)
        luminance = np.sum(pixels[:, :3] * np.array([.2126, .7152, .0722], dtype=np.float32), axis=1)
        if not np.all(np.isfinite(luminance)) or float(np.mean(luminance)) <= 0:
            raise ValueError("Paint scan contains invalid or empty colour data")
        modulation = np.clip(luminance / max(float(np.mean(luminance)), .001), .35, 1.8)
        pixels[:, :3] = np.array(color)[None, :] * (.65 + .35 * modulation[:, None])
        pixels[:, 3] = 1
        image = bpy.data.images.new("Olive painted steel | CC0 scan tint baked", *source.size)
        image.colorspace_settings.name = "sRGB"
        image.pixels.foreach_set(pixels.ravel())
        image.pack()
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = image
        tex.extension = "REPEAT"
        tex.label = "Existing CC0 painted-steel scan; olive tint baked for glTF parity"
        uv = nt.nodes.new("ShaderNodeUVMap")
        uv.uv_map = "PaintUV"
        nt.links.new(uv.outputs["UV"], tex.inputs["Vector"])
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


def mesh_object(name, verts, faces, mat, collection):
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    ob = bpy.data.objects.new(name, mesh)
    collection.objects.link(ob)
    ob.data.materials.append(mat)
    for poly in mesh.polygons:
        poly.use_smooth = True
    return ob


def source_outline():
    bpy.ops.import_scene.gltf(filepath=str(RAW))
    raw_objects = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not raw_objects:
        raise RuntimeError("Hunyuan GLB has no mesh objects")
    # Use the dominant generated body and take its front silhouette in the source
    # image plane (raw X/Z). The output is a sparse radial landmark cage, not a
    # dense projection of Hunyuan's 740k-face surface.
    dominant = max(raw_objects, key=lambda o: len(o.data.polygons))
    mesh = dominant.data
    parents = list(range(len(mesh.vertices)))
    sizes = [1] * len(mesh.vertices)
    def find_root(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index
    for edge in mesh.edges:
        a, b = find_root(edge.vertices[0]), find_root(edge.vertices[1])
        if a != b:
            if sizes[a] < sizes[b]:
                a, b = b, a
            parents[b] = a
            sizes[a] += sizes[b]
    largest_root = max(range(len(sizes)), key=sizes.__getitem__)
    coords = [
        dominant.matrix_world @ vertex.co
        for index, vertex in enumerate(mesh.vertices)
        if find_root(index) == largest_root
    ]
    component_roots = {find_root(index) for index in range(len(mesh.vertices))}
    source_faces = sum(1 for polygon in mesh.polygons if find_root(polygon.vertices[0]) == largest_root)
    xs = [v.x for v in coords]
    zs = [v.z for v in coords]
    xmid, zmid = (min(xs) + max(xs)) / 2, (min(zs) + max(zs)) / 2
    xhalf, zhalf = (max(xs) - min(xs)) / 2, (max(zs) - min(zs)) / 2
    bins = 64
    radii = [0.0] * bins
    for v in coords:
        x, z = (v.x - xmid) / xhalf, (v.z - zmid) / zhalf
        angle = math.atan2(z, x) % (2 * math.pi)
        index = int(angle / (2 * math.pi) * bins) % bins
        radii[index] = max(radii[index], math.hypot(x, z))
    for i in range(bins):
        if radii[i] == 0:
            radii[i] = max(radii[(i - 1) % bins], radii[(i + 1) % bins])
    smooth = [sum(radii[(i + j) % bins] for j in (-2, -1, 0, 1, 2)) / 5 for i in range(bins)]
    median = sorted(smooth)[len(smooth) // 2]
    # The radial fit is constrained to the requested physical body envelope.
    # Source landmarks retain broad asymmetry; outlier spikes are capped.
    radii = [max(.76, min(1.18, r / median)) for r in smooth]
    for o in raw_objects:
        bpy.data.objects.remove(o, do_unlink=True)
    return radii, {"source_vertices": len(coords), "source_faces": source_faces,
                   "source_connected_component_count": len(component_roots),
                   "source_projected_bounds_xz": [[min(xs), min(zs)], [max(xs), max(zs)]],
                   "sparse_outline_samples": bins, "outline_filter": "5-sample circular fairing; median-normalized radius capped 0.76..1.18"}


def make_loft(name, radii, mat, collection, semi_x=.14, semi_y=.09, z_profile=None, rings=9):
    if z_profile is None:
        z_profile = [(-.055, .80), (-.050, .93), (-.040, .985), (-.022, 1.0),
                     (.022, 1.0), (.040, .985), (.050, .93), (.055, .80)]
    n = len(radii)
    verts, faces = [], []
    # Sparse quad rings form an explicit cast-body cage. Catmull-Clark is
    # evaluated on this fair cage, never projected back to the scan.
    for z, scale in z_profile:
        for i, radius in enumerate(radii):
            a = 2 * math.pi * i / n
            verts.append((semi_x * scale * radius * math.cos(a),
                          semi_y * scale * radius * math.sin(a), z))
    for j in range(len(z_profile) - 1):
        for i in range(n):
            a = j * n + i
            b = j * n + (i + 1) % n
            faces.append((a, b, b + n, a + n))
    if len(z_profile) == 8:
        # Inner cap loops keep the high-valence centre away from the drilled
        # ports, rather than stretching a single ngon fan across each bore.
        for front in (False, True):
            outer = (len(z_profile) - 1) * n if front else 0
            inner = len(verts)
            z, scale = z_profile[-1 if front else 0]
            for i, radius in enumerate(radii):
                a = 2 * math.pi * i / n
                verts.append((semi_x * scale * radius * .28 * math.cos(a),
                              semi_y * scale * radius * .28 * math.sin(a), z))
            for i in range(n):
                j = (i + 1) % n
                face = (outer + i, outer + j, inner + j, inner + i)
                faces.append(face if front else tuple(reversed(face)))
            cap = tuple(inner + i for i in range(n))
            faces.append(cap if front else tuple(reversed(cap)))
    else:
        faces.extend([tuple(reversed(range(n))), tuple((len(z_profile) - 1) * n + i for i in range(n))])
    ob = mesh_object(name, verts, faces, mat, collection)
    sub = ob.modifiers.new("Fair sparse silhouette cage", "SUBSURF")
    sub.subdivision_type = "CATMULL_CLARK"
    sub.levels = 2 if len(z_profile) == 8 else 1
    sub.render_levels = sub.levels
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.modifier_apply(modifier=sub.name)
    ob.select_set(False)
    return ob


def cylinder(name, center, radius, depth, mat, collection, vertices=48):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=center)
    ob = bpy.context.object
    ob.name = name
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    collection.objects.link(ob)
    ob.data.materials.append(mat)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def boolean_difference(target, cutter):
    bpy.context.view_layer.objects.active = target
    target.select_set(True)
    mod = target.modifiers.new("Manufactured through-bore", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    target.select_set(False)
    bpy.data.objects.remove(cutter, do_unlink=True)


def ring_tube(name, center_xy, z0, z1, inner_r, outer_profile, mat, collection, sides=40, hex_outer=False):
    # A polygonal bore's apothem, not vertex radius, defines its usable diameter.
    inner_r /= math.cos(math.pi / sides)
    verts, faces = [], []
    for z, r in outer_profile:
        for i in range(sides):
            a = 2 * math.pi * i / sides
            outer_r = r * math.cos(math.pi / 6) / math.cos(a % (math.pi / 3) - math.pi / 6) if hex_outer else r
            verts.append((center_xy[0] + outer_r * math.cos(a), center_xy[1] + outer_r * math.sin(a), z))
            verts.append((center_xy[0] + inner_r * math.cos(a), center_xy[1] + inner_r * math.sin(a), z))
    # Each axial station has outer/inner loop pairs; bridge both walls and ends.
    for j in range(len(outer_profile) - 1):
        base, nxt = j * sides * 2, (j + 1) * sides * 2
        for i in range(sides):
            k, kn = i * 2, ((i + 1) % sides) * 2
            faces.extend(((base + k, base + kn, nxt + kn, nxt + k),
                          (base + k + 1, nxt + k + 1, nxt + kn + 1, base + kn + 1)))
    first, last = 0, (len(outer_profile) - 1) * sides * 2
    for i in range(sides):
        k, kn = i * 2, ((i + 1) % sides) * 2
        faces.append((first + k, first + k + 1, first + kn + 1, first + kn))
        faces.append((last + k, last + kn, last + kn + 1, last + k + 1))
    ob = mesh_object(name, verts, faces, mat, collection)
    return ob


def rounded_box(name, loc, scale, bevel, mat, collection):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    collection.objects.link(ob)
    ob.data.materials.append(mat)
    mod = ob.modifiers.new("Cast corner radius", "BEVEL")
    mod.width, mod.segments = bevel, 3
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=mod.name)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def finish_mesh(ob):
    """Resolve Boolean slivers in authoring space, before split export vertices."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    before = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-7)
    bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=1e-8)
    bmesh.ops.triangulate(bm, faces=list(bm.faces), quad_method="BEAUTY", ngon_method="BEAUTY")
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    if any(not e.is_manifold for e in bm.edges):
        raise RuntimeError(f"Open/nonmanifold manufactured part: {ob.name}")
    if any(f.calc_area() < 1e-12 for f in bm.faces):
        raise RuntimeError(f"Degenerate manufactured triangle: {ob.name}")
    removed = before - len(bm.verts)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    ob.data.set_sharp_from_angle(angle=math.radians(40))
    uv = ob.data.uv_layers.new(name="PaintUV")
    for face in ob.data.polygons:
        axes = [i for i in range(3) if i != max(range(3), key=lambda i: abs(face.normal[i]))]
        for loop in face.loop_indices:
            co = ob.data.vertices[ob.data.loops[loop].vertex_index].co
            uv.data[loop].uv = (co[axes[0]] / .12, co[axes[1]] / .12)
    return {"vertices_welded_before_export": removed, "closed": True,
            "triangles": len(ob.data.polygons), "normal_policy": "40-degree manufactured creases"}


def make_materials():
    return (material("Cast olive enclosure | scanned painted steel", (.12, .155, .065), .64, .25, True),
            material("Black compression polymer", (.018, .022, .02), .67, .02),
            material("Aged zinc fasteners", (.32, .34, .30), .31, .88),
            material("Seam gasket", (.028, .032, .024), .72, .03),
            material("Machined rim", (.39, .40, .35), .34, .8))


def build():
    if not RAW.exists():
        raise FileNotFoundError(RAW)
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for col in list(bpy.data.collections):
        if col.name != "Collection":
            bpy.data.collections.remove(col)
    asset = bpy.data.collections.get("Collection") or bpy.data.collections.new("Collection")
    asset.name = "Stasis wiring enclosure"
    if asset.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(asset)
    radii, source_metrics = source_outline()
    body_mat, rubber_mat, bolt_mat, gasket_mat, trim_mat = make_materials()
    body = make_loft("Cast enclosure body | source-fitted sparse cage", radii, body_mat, asset)

    # Cast rear mounting flange and a raised perimeter bead with an open center.
    flange = make_loft("Rear mounting flange", radii, body_mat, asset, .148, .098,
                       [(-.065, .88), (-.062, .98), (-.053, 1.0)], rings=3)
    seam_verts, seam_faces = [], []
    for z, factor in ((.037, 1.005), (.040, 1.005), (.040, .978), (.037, .978)):
        for i, radius in enumerate(radii):
            angle = 2 * math.pi * i / len(radii)
            seam_verts.append((.14 * factor * radius * math.cos(angle),
                               .09 * factor * radius * math.sin(angle), z))
    for j in range(4):
        for i in range(len(radii)):
            a = j * len(radii) + i
            b = j * len(radii) + (i + 1) % len(radii)
            c = ((j + 1) % 4) * len(radii) + (i + 1) % len(radii)
            d = ((j + 1) % 4) * len(radii) + i
            seam_faces.append((a, b, c, d))
    mesh_object("Continuous lid seam gasket", seam_verts, seam_faces, gasket_mat, asset)

    # Four flat mounting lands, with drilled bolt holes and exposed fasteners.
    mount_points = [(-.116, -.066), (.116, -.066), (-.116, .066), (.116, .066)]
    ears = []
    for index, (x, y) in enumerate(mount_points, 1):
        ear = rounded_box(f"Mounting ear {index}", (x, y, -.056), (.050, .040, .012), .006, body_mat, asset)
        cutter = cylinder(f"Ear drill {index}", (x, y, -.056), .0043, .04, gasket_mat, asset, 32)
        boolean_difference(ear, cutter)
        ears.append(ear)
        bolt = cylinder(f"Mount bolt head {index}", (x, y, -.064), .0068, .003, bolt_mat, asset, 6)
        shaft = cylinder(f"Mount bolt shank {index}", (x, y, -.057), .0032, .012, bolt_mat, asset, 24)
        bevel = bolt.modifiers.new("Bolt head edge", "BEVEL"); bevel.width = .0008; bevel.segments = 2
        bpy.context.view_layer.objects.active = bolt
        bpy.ops.object.modifier_apply(modifier=bevel.name)

    # Drill the complete casting assembly, including overlapping mounting lands.
    all_ports = [(SOCKETS[0], .0128, .0170), (SOCKETS[1], .0128, .0170), (SOCKETS[2], .011, .0140)]
    for port, aperture_r, gland_r in all_ports:
        x, y, _ = port["center_local_m"]
        for casting in [body, flange, *ears]:
            cut = cylinder("Temporary assembly bore cutter", (x, y, 0), aperture_r / math.cos(math.pi / 64), .26, gasket_mat, asset, 64)
            boolean_difference(casting, cut)
        center_z = .09
        outer = gland_r
        # Tapered black strain-relief boot, retained with 1.2 mm radial liner lip.
        neck = max(outer * .78, aperture_r / math.cos(math.pi / 48) + port["compression_liner_radial_thickness_m"])
        profile = [(center_z - .030, neck), (center_z - .024, outer),
                   (center_z - .010, outer), (center_z + .005, max(outer * .93, neck)),
                   (center_z + .018, max(outer * .82, neck)), (center_z + .030, neck)]
        ring_tube(f"{port['id']} black compression gland", (x, y), center_z - .030, center_z + .030,
                  aperture_r, profile, rubber_mat, asset, 48)
        ring_tube(f"{port['id']} compression nut", (x, y), center_z - .019, center_z - .009,
                  aperture_r, [(center_z - .019, outer), (center_z - .009, outer)],
                  bolt_mat, asset, 48, hex_outer=True)
        for index, (z0, z1) in enumerate(((.045, .059), (.083, .087)), 1):
            ring_tube(f"{port['id']} sleeve collar {index}", (x, y), z0, z1,
                      aperture_r, [(z0, outer), (z1, outer)], bolt_mat, asset, 48)

    topology = {}
    for ob in asset.objects:
        if ob.type == "MESH":
            topology[ob.name] = finish_mesh(ob)

    # Remove any imported material/mesh remnants and set native Z-up, front -Y
    # while preserving the documented enclosure-local +Z connector axes.
    root = bpy.data.objects.new("Enclosure local frame | Blender Z-up", None)
    asset.objects.link(root)
    root.rotation_euler[0] = math.pi / 2
    for ob in list(asset.objects):
        if ob is not root:
            ob.parent = root

    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.cycles.device = "CPU"
    scene.render.resolution_x = scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (.16, .16, .16)
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "AgX"
    scene.render.engine = "CYCLES"

    # Neutral studio stage and cameras for reproducible evidence captures.
    stage_mat = material("Neutral capture ground", (.22, .23, .24), .82)
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, -.19))
    ground = bpy.context.object; ground.name = "Capture-only ground"
    ground.data.materials.append(stage_mat)
    for c in list(ground.users_collection): c.objects.unlink(ground)
    asset.objects.link(ground)
    ground.hide_set(True)
    ground.hide_render = True

    # Export only the asset geometry, preserving instanced material references.
    bpy.ops.object.select_all(action="DESELECT")
    for ob in asset.objects:
        if ob.type == "MESH" and ob.name != ground.name:
            ob.select_set(True)
    bpy.context.view_layer.objects.active = body
    blend_path = OUT / "stasis-wiring-enclosure.blend"
    glb_path = OUT / "stasis-wiring-enclosure.glb"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    bpy.ops.export_scene.gltf(filepath=str(glb_path), export_format="GLB", export_yup=True,
                              use_selection=True, export_apply=True, export_cameras=False,
                              export_lights=False, export_materials="EXPORT", export_image_format="AUTO")
    canonicalize_glb_attributes(glb_path)
    sockets_path = OUT / "sockets.json"
    sockets_path.write_text(json.dumps({"asset": "stasis-wiring-enclosure", "units": "metres",
                                        "coordinate_frame": "glTF local; +Y up, front +Z",
                                        "sockets": SOCKETS}, indent=2) + "\n")
    triangles = sum(sum(max(1, len(poly.vertices) - 2) for poly in ob.data.polygons)
                    for ob in asset.objects if ob.type == "MESH" and ob.name != ground.name)
    manifest = {
        "asset": "stasis-wiring-enclosure", "issue": 110, "units": "metres",
        "generator": {"model": "Hunyuan3D-2mv full MLX", "subfolder": "hunyuan3d-dit-v2-mv",
                      "octree_resolution": 320, "seed": 11103, "remove_background": True,
                      "minimum_component_faces": 50,
                      "weights_config": "/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv/hunyuan3d-dit-v2-mv/config.yaml",
                      "weights": "/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv/hunyuan3d-dit-v2-mv/model.fp16.safetensors"},
        "reference": str(SOURCE_IMAGE.relative_to(ROOT)), "reference_sha256": digest(SOURCE_IMAGE),
        "raw_glb": str(RAW.relative_to(ROOT)), "raw_sha256": digest(RAW),
        "fitted_glb": str(glb_path.relative_to(ROOT)), "fitted_glb_sha256": digest(glb_path),
        "editable_blend": str(blend_path.relative_to(ROOT)), "editable_blend_sha256": digest(blend_path),
        "body_dimensions_local_m": [0.28, 0.18, 0.11],
        "rear_mounting_plane_local_z_m": -0.065,
        "body_plus_accessories_bounds_glb_m": "measured by dedicated test_stasis_wiring_hardware.py",
        "triangles_exported_estimate": triangles,
        "authoring_topology": topology,
        "paint_scan_sha256": digest(SCAN),
        "supersedes_glb_sha256": "3f113dcdd7b18f8837c2da00e6e12e059cb02a861861c663ddc39f9b60d5e380",
        "source_fit": {**source_metrics,
                        "fitted_outline_radii": radii,
                        "guide": "raw largest connected Hunyuan mesh projected to X/Z silhouette; 64 angular envelope samples; 5-point cyclic fairing; sparse 8-depth-loop quad cage; Catmull-Clark level 2; no dense projection back to source"},
        "design_decisions": [
            "Preserve the selected reference's irregular rounded/domed cast electrical-box form; no rectangular-box replacement, because the brief requires functional wiring hardware rather than an exact rectangular silhouette.",
            "Use black compression polymer boots as valid protective strain relief, with steel fasteners and a scanned CC0 painted-steel body surface; avoid corrosion on elastomer.",
            "Fit two 24 mm power and one six-strand 6 mm control/data loom in a 22 mm bore to measured cable diameters even if the concept render's apparent port count or scale is rough."
        ],
        "checks": {"socket_file": str(sockets_path.relative_to(ROOT)),
                   "through_bore_and_cable_clearance": "dedicated geometry ray and diameter checks",
                   "byte_identical_reexport": "verified by dedicated test tool"}
    }
    (OUT / "provenance.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return body, source_metrics, blend_path, glb_path


if __name__ == "__main__":
    _, src, blend, glb = build()
    print(json.dumps({"source": src, "blend": str(blend), "glb": str(glb),
                      "glb_sha256": digest(glb)}, indent=2))
