#!/usr/bin/env python3
"""Build hatch geometry and a geometry-baked shared atlas from Godot reservations.

Blender 4.5: --background --factory-startup --python tools/blender/build_hatch.py
-- --input tmp/hatch-model/parts-source.json --output assets/props/hatch/hatch.glb
No gameplay dimensions are authored here. Art offsets are fractions of each
reservation. Mesh coordinates remain part-local; transforms remain separate.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.geometry import tessellate_polygon

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hatch_bake import C, CINV, painted_coordinates, atlas, bake_mesh, bake_footprints, verify_bake_coverage, new_image, node_tree, weather_context, finish_recipe, build_weather, save_image, bake, final_material, detail_textures
from hatch_interfaces import extrusion, rounded_outline, seal_pocket, collar_geometry, annular_geometry
TAU = math.tau


def transform(row):
    basis = row["basis"]
    return C @ Matrix(tuple(tuple(basis[j][i] for j in range(3)) +
                            (row["origin"][i],) for i in range(3)) +
                      ((0, 0, 0, 1),)) @ CINV


def empty(name, parent=None, pose=None):
    obj = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    if pose is not None:
        obj.matrix_basis = pose
    return obj


def mesh_object(name, vertices, faces, parent, pose, material, recalc=True):
    mesh = bpy.data.meshes.new(name + "_mesh")
    triangles = []
    for face in faces:
        if len(face) == 3:
            triangles.append(face)
        else:
            for tri in tessellate_polygon([[Vector(vertices[i]) for i in face]]):
                triangles.append(tuple(face[i] for i in tri))
    mesh.from_pydata([tuple((C @ Vector((*v, 1)))[:3]) for v in vertices], [], triangles)
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    if recalc:
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    # Flat caps and seal faces must never inherit sidewall normals.
    for face in bm.faces:
        face.smooth = False
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    obj.matrix_basis = pose
    mesh.materials.append(material)
    return obj


def radial(size, radius, part_id):
    # Layered shoulders are machined inside the original cylindrical envelope.
    if "barrel" in part_id:
        profile = [(-.5, .70), (-.47, .70), (-.45, .94), (-.42, 1),
                   (-.20, 1), (-.18, .70), (-.15, .70), (-.13, 1),
                   (.13, 1), (.15, .70), (.18, .70), (.20, 1),
                   (.42, 1), (.45, .94), (.47, .70), (.5, .70)]
    elif "hub" in part_id:
        profile = [(-.5, .32), (-.38, .32), (-.38, .72), (-.30, .72),
                   (-.30, 1), (.30, 1), (.5, .94)]
    elif part_id.endswith("/cap"):
        profile = [(-.5, .86), (-.30, 1), (.30, 1), (.5, .86)]
    elif any(key in part_id for key in ("pivot", "shaft")):
        profile = [(-.5, .63), (-.46, .70), (-.28, .70), (-.28, .96),
                   (-.23, 1), (.10, 1), (.14, .94), (.14, .68),
                   (.35, .68), (.35, .48), (.46, .48), (.5, .42)]
    elif "/cap-" in part_id:
        # A pin head seats on a narrower neck inside the knuckle and rounds off outward.
        profile = [(-.5, .50), (-.34, .50), (-.30, 1), (.20, 1), (.36, .84), (.5, .42)]
    else:
        profile = [(-.5, .86), (0, 1), (.5, .64)]
    # The atlas normal carries pitting; eight radial stations retain exact
    # axis bounds and the machined shoulders without spending rings on pixels.
    segments = 6 if part_id.endswith("/cap") else (32 if "hub" in part_id else 8)
    zscale = 1 / math.sin(math.pi / 3) if segments == 6 else 1
    vertices = [(radius * scale * math.cos(TAU * i / segments), y * size[1],
                 radius * scale * math.sin(TAU * i / segments) * zscale)
                for y, scale in profile for i in range(segments)]
    faces = []
    for ring in range(len(profile) - 1):
        for i in range(segments):
            j = (i + 1) % segments
            faces.append((ring * segments + i, ring * segments + j,
                          (ring + 1) * segments + j, (ring + 1) * segments + i))
    faces.append(tuple(range(segments - 1, -1, -1)))
    faces.append(tuple((len(profile) - 1) * segments + i for i in range(segments)))
    return vertices, faces


def torus(size, outer, inner):
    major, minor = (outer + inner) / 2, (outer - inner) / 2
    segments, tube = 44, 8
    vertices = []
    for i in range(segments):
        angle = TAU * i / segments
        for j in range(tube):
            phi = TAU * j / tube
            r = major + minor * math.cos(phi)
            vertices.append((r * math.cos(angle), size[1] / 2 * math.sin(phi), r * math.sin(angle)))
    faces = []
    for i in range(segments):
        for j in range(tube):
            faces.append((i * tube + j, ((i + 1) % segments) * tube + j,
                          ((i + 1) % segments) * tube + (j + 1) % tube,
                          i * tube + (j + 1) % tube))
    return vertices, faces


def flakes(vertices, faces, size, radius, layer):
    # Tiles share their edges within two connected sheets. Only the broken
    # perimeter lifts; isolated diagonal prisms were reading as warning strips.
    front = -size[2] / 2
    width, height = min(size[:2]) * .046, min(size[:2]) * .092
    for sheet in range(2):
        def point(column, row):
            x = (sheet * .40 - .30) * size[0] + column * width
            y = (-.37 + sheet * .13) * size[1] + row * height
            x += math.sin(row * 1.9 + sheet) * width * .12
            y += math.sin(column * 2.3 + sheet) * height * .07
            return x, y
        for row in range(11):
            for column in range(4):
                start = len(vertices)
                contour = [point(column, row), point(column + 1, row),
                           point(column + 1, row + 1), point(column, row + 1)]
                vertices.extend((x, y, front + layer) for x, y in contour)
                vertices.extend((x, y, front + layer * .10) for x, y in contour)
                faces.extend([(start + 3, start + 2, start + 1, start),
                              (start + 4, start + 5, start + 6, start + 7)])
                for j, exposed in enumerate((row == 0, column == 3, row == 10, column == 0)):
                    if exposed:
                        k = (j + 1) % 4
                        faces.append((start + j, start + k, start + k + 4, start + j + 4))


def spoke(size):
    segments = 12
    profile = [(-.5, .74), (-.47, 1), (.47, 1), (.5, .74)]
    vertices = [(size[0] / 2 * scale * math.cos(TAU * i / segments), y * size[1],
                 size[2] / 2 * scale * math.sin(TAU * i / segments))
                for y, scale in profile for i in range(segments)]
    faces = [(ring * segments + i, ring * segments + (i + 1) % segments,
              (ring + 1) * segments + (i + 1) % segments, (ring + 1) * segments + i)
             for ring in range(len(profile) - 1) for i in range(segments)]
    faces.extend([tuple(range(segments - 1, -1, -1)),
                  tuple((len(profile) - 1) * segments + i for i in range(segments))])
    return vertices, faces


def layered_plate(size, radius):
    contour = rounded_outline(size, radius, segments=4)
    count = len(contour)
    profile = [(-.5, .16), (-.38, .08), (-.25, .08), (-.22, 0), (.38, 0), (.5, .06)]
    vertices = [(x * (1 - inset), y * (1 - inset), z * size[2])
                for z, inset in profile for x, y in contour]
    faces = [(ring * count + i, ring * count + (i + 1) % count,
              (ring + 1) * count + (i + 1) % count, (ring + 1) * count + i)
             for ring in range(len(profile) - 1) for i in range(count)]
    faces.extend([tuple(range(count - 1, -1, -1)),
                  tuple((len(profile) - 1) * count + i for i in range(count))])
    return vertices, faces


def forged_bar(size):
    # Flat-faced arm in its round reservation box: an octagonal section reads as forged steel, not a rod.
    half_x, half_z = size[0] / 2, size[2] / 2
    radius = min(half_x, half_z) * .2
    section = []
    for corner, (sx, sz) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
        centre = (sx * (half_x - radius), sz * (half_z - radius))
        for step in range(2):
            angle = corner * math.pi / 2 + step * math.pi / 4
            section.append((centre[0] + math.cos(angle) * radius, centre[1] + math.sin(angle) * radius))
    profile = [(-.5, .84), (-.44, 1), (.44, 1), (.5, .84)]
    vertices = [(x * scale, y * size[1], z * scale) for y, scale in profile for x, z in section]
    count = len(section)
    faces = [(ring * count + i, ring * count + (i + 1) % count,
              (ring + 1) * count + (i + 1) % count, (ring + 1) * count + i)
             for ring in range(len(profile) - 1) for i in range(count)]
    faces.append(tuple(range(count - 1, -1, -1)))
    faces.append(tuple((len(profile) - 1) * count + i for i in range(count)))
    return vertices, faces


def geometry(part, steel=False):
    shape, size = part["shape"], part["size"]
    if "visual_recess" in part:
        return seal_pocket(size, part["visual_radius"], part["visual_recess"], part["visual_side"])
    if shape == "cylinder" and "/arm-" in part["id"]:
        return forged_bar(size)
    if shape == "cylinder":
        return radial(size, part["radius"], part["id"])
    if shape == "torus":
        inner = part["inner_radius"]
        if part["id"].endswith("/flange"):
            inner = max(inner, part["radius"] - size[1] * 1.8)
        return torus(size, part["radius"], inner)
    if shape == "band":
        return extrusion(part["contour"], size[2])
    if shape == "box":
        if "/spoke-" in part["id"]:
            return spoke(size)
        contour = [(-size[0]/2, -size[1]/2), (size[0]/2, -size[1]/2),
                   (size[0]/2, size[1]/2), (-size[0]/2, size[1]/2)]
        # All simulation box seals retain square, flat corners without bevels.
        return extrusion(contour, size[2], 0 if steel else min(size) * .14)
    if shape == "rounded":
        if "/strap-" in part["id"] or "/plate-" in part["id"] or "/grip-" in part["id"]:
            return layered_plate(size, part["radius"])
        slab = steel and part["id"].endswith("/plate")
        layer = part["paint_layer_depth"] if slab else 0.0
        bevel = part["edge_bevel"] if slab else min(size) * .12
        vertices, faces = extrusion(part["contour"] or rounded_outline(size, part["radius"]), size[2], bevel, layer)
        if layer:
            flakes(vertices, faces, size, part["radius"], layer)
        return vertices, faces
    raise ValueError("unknown exported shape " + shape)


def bounds(obj):
    source = [CINV @ v.co.to_4d() for v in obj.data.vertices]
    lo = [min(v[i] for v in source) for i in range(3)]
    hi = [max(v[i] for v in source) for i in range(3)]
    return {"position": lo, "size": [hi[i] - lo[i] for i in range(3)]}


def exact_bounds(obj, size):
    actual = bounds(obj)
    error = max(abs(actual["position"][i] + size[i] / 2) for i in range(3))
    error = max(error, max(abs(actual["size"][i] - size[i]) for i in range(3)))
    if error > 1e-6:
        raise ValueError(f"reservation mismatch {obj.name}: {actual} != {size}, error={error}")
    return error


def attr(obj, name, value, domain="POINT"):
    attribute = obj.data.attributes.new(name, "FLOAT", domain)
    count = len(obj.data.vertices) if domain == "POINT" else len(obj.data.polygons)
    values = np.full(count, value, dtype=np.float32) if np.isscalar(value) else np.asarray(value, dtype=np.float32)
    attribute.data.foreach_set("value", values)


def radial_normals(obj, size):
    # Smooth around a machined circumference, never across an axial shoulder.
    normals = []
    for polygon in obj.data.polygons:
        normal = (CINV.to_3x3() @ polygon.normal).normalized()
        for index in polygon.loop_indices:
            point = CINV @ obj.data.vertices[obj.data.loops[index].vertex_index].co.to_4d()
            radial = Vector((point.x / (size[0] / 2) ** 2, 0, point.z / (size[2] / 2) ** 2)).normalized()
            result = radial * math.hypot(normal.x, normal.z) + Vector((0, normal.y, 0))
            normals.append(tuple(C.to_3x3() @ result.normalized()))
        polygon.use_smooth = True
    obj.data.normals_split_custom_set(normals)


def leaf_attributes(obj, part, steel):
    part_id = part["id"]
    attr(obj, "painted", 0.0 if part_id.endswith("/face-return") else (1.0 if steel or "/strap-" in part_id or "/plate-" in part_id else .35))
    attr(obj, "hazard", 1.0 if part["shape"] == "band" else 0.0)
    if part["shape"] == "band":
        attr(obj, "band_coordinate", [(CINV @ vertex.co.to_4d()).y * 2 / part["size"][1]
                                      for vertex in obj.data.vertices])
    attr(obj, "rivet_finish", 1.0 if "Rivets/" in part_id else 0.0)
    attr(obj, "frame_ring", 0.0)
    machined = []
    flake, chip_edge, substrate, relief = [], [], [], []
    chipped = steel and part_id.endswith("/plate")
    base_count = len(rounded_outline(part["size"], part["radius"])) * 5 if chipped else 0
    front, layer = -part["size"][2] / 2, part["paint_layer_depth"]
    for polygon in obj.data.polygons:
        indices = list(polygon.vertices)
        points = [CINV @ obj.data.vertices[i].co.to_4d() for i in indices]
        normal = CINV.to_3x3() @ polygon.normal
        island = chipped and min(indices) >= base_count
        edge = island and abs(normal.z) < .85
        recessed = chipped and not island and abs(sum(p.z for p in points) / len(points) - (front + layer)) < 1e-6
        flake.append(float(island and not edge))
        chip_edge.append(float(edge))
        substrate.append(float(recessed))
        relief.append(max(0, min(1, (front + layer - min(p.z for p in points)) / layer)) if chipped else 0)
        if part["shape"] == "cylinder":
            machined.append(1.0 if abs(normal.y) > .65 else .15)
        else:
            machined.append(1.0 if any(key in part_id for key in ("/strap-", "/plate-", "/grip-", "Steel/plate")) and abs(normal.z) < .95 else 0)
    for name, values in (("flake", flake), ("chip_edge", chip_edge), ("substrate", substrate),
                         ("relief", relief), ("machined", machined)):
        attr(obj, name, values, "FACE")


def annular_normals(obj, solid):
    # Keep the fixed mesh's flat geometric-normal contract. Bake its continuous
    # perimeter normals into the tangent map through a separate corner field.
    section = [Vector(point) for point in solid["section"]]
    across = [(section[3]-section[0]).normalized(), (section[2]-section[1]).normalized()]
    tangent = (section[1]-section[0]).normalized()
    width = abs(tangent.x * (section[3]-section[0]).y - tangent.y * (section[3]-section[0]).x)
    depth = solid["size"][2]
    bevel = min(width * .45, depth * .45)
    normals = []
    for polygon in obj.data.polygons:
        for loop in polygon.loop_indices:
            vertex = obj.data.loops[loop].vertex_index
            point = CINV @ obj.data.vertices[vertex].co.to_4d()
            corner = min(range(4), key=lambda i: (Vector((point.x, point.y))-section[i]).length)
            outward = across[0 if corner in (0, 3) else 1] * (-1 if corner < 2 else 1)
            cap_distance = depth / 2 - abs(point.z)
            face_normal = CINV.to_3x3() @ polygon.normal
            if abs(face_normal.z) > .999999:
                axial = 1.0
            elif corner < 2 or "/RING/" not in solid["id"]:
                axial = 0.0
            else:
                axial = max(0, min(1, 1 - cap_distance / bevel))
            radial = math.sqrt(max(0, 1 - axial * axial))
            result = Vector((outward.x * radial, outward.y * radial, math.copysign(axial, point.z)))
            normals.append(tuple(obj.matrix_basis.to_3x3() @ (C.to_3x3() @ result.normalized())))
    attribute = obj.data.attributes.new("frame_normal", "FLOAT_VECTOR", "CORNER")
    attribute.data.foreach_set("vector", np.asarray(normals, dtype=np.float32).ravel())
    attr(obj, "frame_smooth", 1.0)


def material():
    mat = bpy.data.materials.new("HatchWeatheredSteel")
    mat.use_nodes = True
    mat.use_backface_culling = True
    return mat


def construct(document, mat, frames=None, high_sources=None):
    nodes, objects, max_error = {}, [], 0.0
    if high_sources is None:
        high_sources = {}
    for variant in document["variants"]:
        vi = variant["index"]
        root = empty(f"Variant{vi}")
        # Separated only for geometry-context baking, restored before export.
        root.location.x = vi * 5.0
        leaf = empty("Leaf" + str(vi), root, transform(variant["hinge_transform"]))
        frame = empty("Frame" + str(vi), root)
        if frames is not None:
            from hatch_generated_frame import reduce_ring
            low_ring = reduce_ring(frames[vi], variant, mesh_object, mat)
        plates = {group["side"]: part for group in variant["groups"] for part in group["parts"]
                  if group["steel"] and part["id"].endswith("/plate")}
        for group in variant["groups"]:
            gi = group["index"]
            parent = empty(f"v{vi}_g{gi:02d}", leaf, transform(group["transform"]))
            for part in group["parts"]:
                pi = part["index"]
                name = f"v{vi}_g{gi:02d}_p{pi:03d}"
                visual = part
                if part["id"].endswith("/face-return"):
                    plate = plates[group["side"]]
                    layer = plate["paint_layer_depth"]
                    plate_face = abs(plate["transform"]["origin"][2]) + plate["size"][2] / 2
                    seal_face = abs(group["transform"]["origin"][2]) + part["size"][2] / 2
                    visual = dict(part, visual_recess=seal_face - plate_face + layer * 1.1,
                                  visual_radius=plate["radius"], visual_side=group["side"])
                verts, faces = geometry(visual, group["steel"])
                obj = mesh_object(name, verts, faces, parent, transform(part["transform"]), mat)
                if part["shape"] == "torus":
                    for face in obj.data.polygons:
                        face.use_smooth = True
                elif (part["shape"] == "cylinder" and "/arm-" not in part["id"] and not part["id"].endswith("/cap")) or "/spoke-" in part["id"]:
                    radial_normals(obj, part["size"])
                max_error = max(max_error, exact_bounds(obj, part["size"]))
                leaf_attributes(obj, part, group["steel"])
                nodes[name] = dict(variant=vi, kind="leaf", group=gi, part=pi,
                                   id=part["id"], side=group["side"], transform=part["transform"], bounds=bounds(obj))
                objects.append(obj)
        for solid in variant["frame_solids"]:
            pose = transform(solid["transform"])
            annular = bool(solid["section"]) and solid["id"].startswith("SURROUND/")
            generated = frames is not None and (solid["id"] in frames[vi].ring or solid["id"] in frames[vi].hardware)
            high = None
            if generated:
                from hatch_generated_frame import local_region, reduce_region
                if solid["id"] in frames[vi].ring:
                    verts, source_faces = local_region(low_ring[solid["id"]], solid["transform"])
                    high_vertices, high_faces = local_region(frames[vi].ring[solid["id"]], solid["transform"])
                    high = mesh_object("High_" + solid["id"].replace("/", "_"), high_vertices, high_faces, frame, pose, mat, recalc=False)
                    for polygon in high.data.polygons:
                        polygon.use_smooth = True
                    high.hide_render = True
                    high.hide_set(True)
                else:
                    region = frames[vi].hardware[solid["id"]]
                    verts, source_faces, high = reduce_region(region, solid["transform"], 120, mesh_object, frame, mat)
                    high.matrix_basis = pose
            elif annular:
                verts, source_faces = annular_geometry(solid)
            elif solid["id"].startswith("FRAME/") or solid["id"] == "COAMING":
                from hatch_fit import rendered_solid
                verts, source_faces = collar_geometry(rendered_solid(variant, solid))
            else:
                verts, source_faces = solid["vertices"], solid["faces"]
            sets = {0: [], 1: []}
            godot_basis = Matrix(solid["transform"]["basis"]).transposed()
            for face in source_faces:
                a, b, c = (Vector(verts[i]) for i in face[:3])
                normal = godot_basis @ (b - a).cross(c - a).normalized()
                side = (0 if normal.z < 0 else 1) if abs(normal.z) > .5 else (0 if variant["hinge_sign"] > 0 else 1)
                sets[side].append(face)
            if any(not faces for faces in sets.values()):
                raise ValueError(f"fixed reservation lacks a positive-area face batch: {solid['id']}")
            for side, faces in sets.items():
                # Do not keep unused vertices: per-side bounds must describe only its actual geometry.
                used = sorted({i for face in faces for i in face})
                remap = {old: new for new, old in enumerate(used)}
                name = f"v{vi}_f{solid['index']:03d}_s{side}"
                obj = mesh_object(name, [verts[i] for i in used],
                                  [tuple(remap[i] for i in f) for f in faces], frame, pose, mat, recalc=False)
                # Blender's polygon-normal accumulator loses precision on
                # small clipped facets. The delivered fixed normals must be
                # the cross product of the actual exported triangle edges.
                normals = []
                for polygon in obj.data.polygons:
                    a, b, c = [obj.data.vertices[i].co for i in polygon.vertices]
                    normal = (b - a).cross(c - a).normalized()
                    normals.extend([normal] * len(polygon.loop_indices))
                obj.data.normals_split_custom_set(normals)
                if generated:
                    high_sources[name] = high
                elif annular:
                    annular_normals(obj, solid)
                ring = "/RING/" in solid["id"]
                attr(obj, "painted", 1 if ring else 0)
                attr(obj, "frame_ring", 1 if ring else 0)
                attr(obj, "machined", .7 if "/LIP/" in solid["id"] else .10, "FACE")
                attr(obj, "hazard", 0)
                attr(obj, "rivet_finish", 0)
                nodes[name] = dict(variant=vi, kind="frame", part=solid["index"],
                                   id=solid["id"], side=side, transform=solid["transform"], bounds=bounds(obj))
                objects.append(obj)
        for rivet in variant["frame_rivets"]:
            name = f"v{vi}_r{rivet['side']}_{rivet['index']:03d}"
            if frames is not None:
                from hatch_generated_frame import reduce_region
                verts, faces, high = reduce_region(frames[vi].rivets[rivet["index"]], rivet["transform"], 48, mesh_object, frame, mat)
                high.matrix_basis = transform(rivet["transform"])
                high_sources[name] = high
            else:
                verts, faces = radial(rivet["size"], rivet["radius"], rivet["id"])
            obj = mesh_object(name, verts, faces, frame, transform(rivet["transform"]), mat)
            max_error = max(max_error, exact_bounds(obj, rivet["size"]))
            if frames is None:
                radial_normals(obj, rivet["size"])
            else:
                for polygon in obj.data.polygons:
                    polygon.use_smooth = True
            attr(obj, "painted", 0)
            attr(obj, "hazard", 0)
            attr(obj, "frame_ring", 0)
            attr(obj, "rivet_finish", 1)
            attr(obj, "machined", .8, "FACE")
            nodes[name] = dict(variant=vi, kind="rivet", part=rivet["index"], id=rivet["id"],
                               side=rivet["side"], transform=rivet["transform"], bounds=bounds(obj))
            objects.append(obj)
    bpy.context.view_layer.update()
    return objects, nodes, max_error


def build_dependencies():
    directory = Path(__file__).resolve().parent
    return {name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
            for name in ("build_hatch.py", "hatch_bake.py", "hatch_interfaces.py", "hatch_fit.py", "hatch_generated_frame.py")}


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--resolution", type=int, default=2048)
    parser.add_argument("--samples", type=int, default=8)
    parser.add_argument("--reuse-bakes", action="store_true", help="geometry iteration only; reuse matching atlas")
    args = parser.parse_args(argv)
    source_path = Path(args.input).resolve()
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    raw = source_path.read_bytes()
    dependencies = build_dependencies()
    recipe_hash = hashlib.sha256(json.dumps(dependencies, sort_keys=True).encode()).hexdigest()
    finish_hash = hashlib.sha256(Path(__file__).with_name("hatch_scan_finish.py").read_bytes()).hexdigest()
    finish = finish_recipe()
    scan_inputs = {str(path.relative_to(finish.ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                   for paths in finish.SCANS.values() for path in paths}
    document = json.loads(raw)
    if document["schema_version"] != 1 or [v["hinge_sign"] for v in document["variants"]] != [1, -1]:
        raise ValueError("expected hatch schema 1, both ordered hinge signs")
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
    mat = material()
    from hatch_generated_frame import load_frames
    frames = load_frames(document)
    high_sources = {}
    objects, nodes, error = construct(document, mat, frames, high_sources)
    for variant in document["variants"]:
        count = sum(len(obj.data.polygons) for obj in objects if nodes[obj.name]["variant"] == variant["index"])
        print("CANDIDATE_TRIANGLES", variant["index"], count, flush=True)
        if count > 40000:
            raise ValueError(f"generated frame exceeds complete-hatch triangle budget: {count}")
    context = weather_context(objects, nodes, document)
    atlas(objects, args.resolution)
    from hatch_bake import validate_mesh_attributes
    validate_mesh_attributes(objects, nodes, args.resolution)
    painted_coordinates(objects, nodes, document)
    joined = bake_mesh(objects)
    bake_footprints(joined, args.resolution)
    if args.reuse_bakes:
        old = json.loads((output.parent / "parts.json").read_text())
        if (old["source_sha256"] != hashlib.sha256(raw).hexdigest() or
                old["build_recipe_sha256"] != recipe_hash or
                old.get("generated_sources") != document["generated_sources"] or
                old.get("fit_recipe") != document["fit_recipe"] or
                old.get("finish_recipe_sha256") != finish_hash or old.get("scan_inputs") != scan_inputs or
                old["measurements"]["atlas_resolution"] != args.resolution or
                old["measurements"]["bake_samples"] != args.samples):
            raise ValueError("cannot reuse textures after source, recipe or bake settings change")
        images = {name: bpy.data.images.load(str(output.parent / f"hatch_{name}.png"))
                  for name in ("albedo", "ao", "normal", "orm", "height", "curvature", "coverage")}
        for name, image in images.items():
            image.colorspace_settings.name = "sRGB" if name == "albedo" else "Non-Color"
        textures, measures = old["textures"], old["measurements"]
    else:
        images, textures, measures = bake(joined, mat, output.parent, args.resolution, args.samples, context)
        from hatch_generated_frame import transfer_normals
        images["normal"], normal_row = transfer_normals(objects, high_sources, mat, output.parent, args.resolution)
        textures = [row for row in textures if row["file"] != "hatch_normal.png"] + [normal_row]
        measures["normal_method"] = "cycles_selected_to_active_part_isolated_fitted_source"
    for high in set(high_sources.values()):
        bpy.data.objects.remove(high, do_unlink=True)
    for name in high_sources:
        nodes[name]["generated_source"] = document["generated_sources"]["source_sha256"]
    textures = [row for row in textures if not row["file"].startswith("hatch_detail_")]
    textures.extend(detail_textures(output.parent))
    painted_path = output.parent / "hatch_painted.png"
    painted = bpy.data.images.load(str(painted_path), check_existing=True)
    textures = [row for row in textures if row["file"] != painted_path.name]
    textures.append(dict(file=painted_path.name, width=painted.size[0], height=painted.size[1],
                         bytes=painted_path.stat().st_size, sha256=hashlib.sha256(painted_path.read_bytes()).hexdigest()))
    bpy.data.objects.remove(joined, do_unlink=True)
    final_material(mat, images)
    for vi in range(2):
        bpy.data.objects[f"Variant{vi}"].location = (0, 0, 0)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.context.scene.objects:
        obj.hide_set(False); obj.hide_render = False; obj.select_set(True)
    bpy.context.view_layer.update()
    triangles = {str(i): 0 for i in range(2)}
    for obj in objects:
        obj.data.calc_loop_triangles()
        triangles[str(nodes[obj.name]["variant"])] += len(obj.data.loop_triangles)
    physical_finish = {}
    for obj in objects:
        row = nodes[obj.name]
        if row["kind"] != "leaf" or not row["id"].endswith("Steel/plate"):
            continue
        part = document["variants"][row["variant"]]["groups"][row["group"]]["parts"][row["part"]]
        base_count = len(rounded_outline(part["size"], part["radius"])) * 5
        points = [CINV @ vertex.co.to_4d() for vertex in obj.data.vertices[base_count:]]
        islands = [points[i:i+8] for i in range(0, len(points), 8)]
        spans = [max(v.x for v in island) - min(v.x for v in island) for island in islands]
        lifts = [max(v.z for v in island[:4]) - min(v.z for v in island[4:]) for island in islands]
        physical_finish[obj.name] = dict(islands=len(islands), width_min_m=min(spans), width_max_m=max(spans),
                                          lifted_edge_min_m=min(lifts), lifted_edge_max_m=max(lifts),
                                          substrate_recess_m=part["paint_layer_depth"])
    levels = range(int(math.log2(args.resolution)) + 1)
    compressed_map_bytes = sum(max(1, ((args.resolution >> level) + 3) // 4) ** 2 * 16 for level in levels)
    measures.update(physical_finish=physical_finish, triangles_per_variant=triangles, mesh_nodes=len(objects),
                    mesh_nodes_per_variant={str(i): sum(n["variant"] == i for n in nodes.values()) for i in range(2)},
                    max_reservation_error_m=error, atlas_resolution=args.resolution,
                    draw_calls_unbatched_per_variant={str(i): sum(n["variant"] == i for n in nodes.values()) for i in range(2)},
                    texture_gpu_bc7_bc5_mips_bytes=3 * compressed_map_bytes + 9 * sum(max(1, ((512 >> level) + 3) // 4) ** 2 * 16 for level in range(10))
                    + sum(max(1, ((painted.size[0] >> level) + 3) // 4) * max(1, ((painted.size[1] >> level) + 3) // 4) * 16 for level in range(int(math.log2(max(painted.size))) + 1)),
                    painted_atlas_resolution=list(painted.size), painted_leaf_cell=[painted.size[0] // 2, round(painted.size[1] * .53125)], painted_height_m=.0015,
                    detail_resolution=512, detail_pitch_m=.20, atlas_content="low_frequency_layer_weather_masks_and_geometric_normal",
                    texture_gpu_auxiliary_mips_bytes=4 * compressed_map_bytes,
                    texture_png_disk_bytes=sum(row["bytes"] for row in textures),
                    render_texture_png_disk_bytes=sum(row["bytes"] for row in textures if row["file"] in ("hatch_albedo.png", "hatch_orm.png", "hatch_normal.png")))
    bpy.ops.export_scene.gltf(filepath=str(output), export_format="GLB", use_selection=True,
                              export_apply=False, export_yup=True, export_cameras=False,
                              export_lights=False, export_skins=False, export_animations=False,
                              export_texcoords=True, export_normals=True, export_tangents=True,
                              export_attributes=False, export_extras=False,
                              export_vertex_color="ACTIVE", export_all_vertex_colors=True,
                              export_materials="EXPORT", export_image_format="AUTO")
    # The exporter welds coincident loop vertices and omits collapsed triangles.
    # Budget the delivered index buffers, not the pre-export authoring topology.
    glb = output.read_bytes()
    json_size = struct.unpack_from("<I", glb, 12)[0]
    encoded = json.loads(glb[20:20 + json_size])
    delivered = {str(i): 0 for i in range(2)}
    for row in encoded["nodes"]:
        if "mesh" not in row:
            continue
        variant = str(nodes[row["name"]]["variant"])
        delivered[variant] += sum(encoded["accessors"][p["indices"]]["count"] // 3
                                  for p in encoded["meshes"][row["mesh"]]["primitives"])
    measures["authoring_triangles_per_variant"] = triangles
    measures["triangles_per_variant"] = delivered
    document.update(asset="hatch.glb", source_sha256=hashlib.sha256(raw).hexdigest(),
                    build_recipe_sha256=recipe_hash, build_dependencies=dependencies,
                    finish_recipe_sha256=finish_hash, scan_inputs=scan_inputs,
                    nodes=nodes, textures=textures, measurements=measures)
    (output.parent / "parts.json").write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
    print("HATCH_BUILD", json.dumps(measures, sort_keys=True), flush=True)
    print("EXPORT", output, output.stat().st_size, flush=True)


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
