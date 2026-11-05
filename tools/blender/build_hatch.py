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
from bpy_extras.mesh_utils import mesh_linked_uv_islands
import numpy as np
from mathutils import Matrix, Vector
from mathutils.geometry import tessellate_polygon

C = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
CINV = C.inverted()
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


def extrusion(contour, depth, bevel=0.0, pocket_depth=0.0):
    vertices, faces = [], []
    sx = max(p[0] for p in contour) - min(p[0] for p in contour)
    sy = max(p[1] for p in contour) - min(p[1] for p in contour)
    bevel = min(bevel, depth * .22, sx * .10, sy * .10)
    if bevel:
        rings = [(-depth / 2, bevel), (-depth / 2 + bevel, 0),
                 (depth / 2 - bevel, 0), (depth / 2, bevel)]
        if pocket_depth:
            rings.insert(0, (-depth / 2 + pocket_depth, bevel + pocket_depth * 2))
    else:
        rings = [(-depth / 2, 0), (depth / 2, 0)]
    count = len(contour)
    for z, inset in rings:
        for x, y in contour:
            vertices.append((x * (1 - 2 * inset / sx),
                             y * (1 - 2 * inset / sy), z))
    for ring in range(len(rings) - 1):
        for i in range(count):
            j = (i + 1) % count
            faces.append((ring * count + i, ring * count + j,
                          (ring + 1) * count + j, (ring + 1) * count + i))
    for start in (0, (len(rings) - 1) * count):
        points = [Vector(v) for v in vertices[start:start + count]]
        for tri in tessellate_polygon([points]):
            triangle = tuple(start + i for i in tri)
            faces.insert(0 if start == 0 else len(faces), tuple(reversed(triangle)) if start == 0 else triangle)
    return vertices, faces


def rounded_outline(size, radius, segments=8):
    radius = min(radius, size[0] / 2, size[1] / 2)
    result = []
    for corner in range(4):
        center = ((size[0] / 2 - radius) * (1 if corner in (0, 3) else -1),
                  (size[1] / 2 - radius) * (1 if corner < 2 else -1))
        for step in range(segments + 1):
            angle = (corner + step / segments) * math.pi / 2
            result.append((center[0] + math.cos(angle) * radius,
                           center[1] + math.sin(angle) * radius))
    return result


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


def seal_pocket(size, radius, recess, side):
    inner = rounded_outline(size, radius)
    inner = [(x * .98, y * .99) for x, y in inner]
    outer = []
    for corner in range(4):
        base = corner * 9
        tip = Vector((size[0] / 2 * (1 if corner in (0, 3) else -1),
                      size[1] / 2 * (1 if corner < 2 else -1)))
        start = Vector((tip.x, inner[base][1]) if corner % 2 == 0 else (inner[base][0], tip.y))
        end = Vector((inner[base+8][0], tip.y) if corner % 2 == 0 else (tip.x, inner[base+8][1]))
        for step in range(9):
            point = start.lerp(tip, step / 4) if step <= 4 else tip.lerp(end, (step-4) / 4)
            outer.append(tuple(point))
    # Meter-long wall triangles against a millimetre recess lose their tangent
    # basis through cancellation. Split corresponding runs before making rings,
    # retaining the same curves and exact square perimeter.
    inner_run, outer_run = [], []
    for index in range(len(inner)):
        following = (index + 1) % len(inner)
        a, b = Vector(inner[index]), Vector(inner[following])
        c, d = Vector(outer[index]), Vector(outer[following])
        steps = math.ceil(max((b-a).length, (d-c).length) / (recess * 128))
        for step in range(steps):
            inner_run.append(tuple(a.lerp(b, step / steps)))
            outer_run.append(tuple(c.lerp(d, step / steps)))
    inner, outer = inner_run, outer_run
    sign = -1 if side == 0 else 1
    front = sign * size[2] / 2
    count = len(inner)
    rings = [(outer, -front), (outer, front), (inner, front)]
    # Roll the pocket mouth instead of dropping directly from the square
    # flange to the recessed plate. One cove spans the source recess: stacking
    # two small fillets here produces subpixel slivers with undefined tangents.
    roll = min(recess, min(size[:2]) * .006)
    profile = []
    for step in range(1, 6):
        angle = step * math.pi / 10
        profile.append((roll * math.sin(angle), recess * (1 - math.cos(angle))))
    for inset, depth in profile:
        contour = [(x * (1 - 2 * inset / size[0]), y * (1 - 2 * inset / size[1])) for x, y in inner]
        rings.append((contour, front - sign * depth))
    vertices = [(x, y, z) for contour, z in rings for x, y in contour]
    faces = [(ring*count+i, ring*count+(i+1)%count,
              (ring+1)*count+(i+1)%count, (ring+1)*count+i)
             for ring in range(len(rings) - 1) for i in range(count)]
    center = len(vertices)
    vertices.append((0, 0, -front))
    faces.extend((center, (i+1) % count, i) for i in range(count))
    floor_center = len(vertices)
    vertices.append((0, 0, rings[-1][1]))
    start = (len(rings)-1) * count
    faces.extend((floor_center, start+i, start+(i+1) % count) for i in range(count))
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


def collar_geometry(solid):
    # Round the exposed collar/stop edges without clipping their reservation or
    # replacing the source's sloped returns with a different silhouette layer.
    bm = bmesh.new()
    vertices = [bm.verts.new(point) for point in solid["vertices"]]
    for face in solid["faces"]:
        bm.faces.new([vertices[index] for index in face])
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    # Exported caps are triangulated for transport. Their internal diagonals
    # are not physical edges and must not acquire bevels and needle triangles.
    bmesh.ops.dissolve_limit(bm, angle_limit=1e-5, verts=list(bm.verts), edges=list(bm.edges))
    # Stop roundovers must stay smaller than the 2.5 mm sealing lap.
    roundover = .03 if solid["id"].startswith("FRAME/STOP-") else .10
    # The clipped coaming has short arc segments. A size-only offset makes
    # overlap clamping collapse their fillets into almost-square corners.
    offset = min(min(solid["size"]) * roundover, min(edge.calc_length() for edge in bm.edges) * .25)
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=offset,
                    segments=3, affect="EDGES", clamp_overlap=True)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=min(solid["size"]) * .01)
    bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=min(solid["size"]) * .01)
    # Long jamb fillets otherwise triangulate into metre-long needles beside
    # millimetre roundovers. Slice the existing skin, without internal caps.
    for axis in range(3):
        lo = min(v.co[axis] for v in bm.verts)
        hi = max(v.co[axis] for v in bm.verts)
        cuts = math.ceil((hi - lo) / .20)
        normal = Vector(tuple(1 if i == axis else 0 for i in range(3)))
        for cut in range(1, cuts):
            plane = Vector((0, 0, 0))
            plane[axis] = lo + (hi - lo) * cut / cuts
            bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
                                   dist=1e-7, plane_co=plane, plane_no=normal)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=min(solid["size"]) * .01)
    bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=min(solid["size"]) * .01)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bm.normal_update()
    # Preserve the bevel facets and sealing planes. Rotating their shared
    # edges makes sliver faces across the roundover rather than improving it.
    edges = [edge for edge in bm.edges
             if len(edge.link_faces) == 2 and edge.calc_face_angle() < 1e-5]
    bmesh.ops.beautify_fill(bm, faces=list(bm.faces), edges=edges, method="AREA")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.verts.index_update()
    points = [tuple(vertex.co) for vertex in bm.verts]
    faces = [tuple(vertex.index for vertex in face.verts) for face in bm.faces]
    bm.free()
    # Sloped source boxes attain some extrema only at their old sharp edges.
    # Recover those exact extents from the source, keeping the whole roundover
    # inside the collision box rather than silently shrinking the collar.
    for axis in range(3):
        lo, hi = min(p[axis] for p in points), max(p[axis] for p in points)
        source_lo = min(p[axis] for p in solid["vertices"])
        source_hi = max(p[axis] for p in solid["vertices"])
        points = [tuple(source_lo + (p[i] - lo) * (source_hi - source_lo) / (hi - lo)
                        if i == axis else p[i] for i in range(3)) for p in points]
    return points, faces


def annular_geometry(solid):
    # Contract across band width only. Radial cell boundaries remain shared and
    # have no internal walls, bevel gaps, or independent cap normals to bake.
    section = [Vector(point) for point in solid["section"]]
    a, b, c, d = section
    tangent = (b - a).normalized()
    width = abs(tangent.x * (d-a).y - tangent.y * (d-a).x)
    depth = solid["size"][2]
    bevel = min(width * .45, depth * .45) if "/RING/" in solid["id"] else 0
    profile = []
    if bevel:
        for step in range(4):
            angle = step * math.pi / 6
            profile.append((-depth / 2 + bevel * (1 - math.cos(angle)), bevel * (1 - math.sin(angle))))
        profile.extend((-z, inset) for z, inset in reversed(profile[:]))
    else:
        profile = [(-depth / 2, 0), (depth / 2, 0)]
    vertices = []
    for z, inset in profile:
        fraction = inset / width
        vertices.extend([a.to_tuple() + (z,), b.to_tuple() + (z,),
                         (c + (b-c) * fraction).to_tuple() + (z,),
                         (d + (a-d) * fraction).to_tuple() + (z,)])
    faces = [(0, 1, 2, 3), tuple(reversed(range((len(profile)-1)*4, len(profile)*4)))]
    for ring in range(len(profile) - 1):
        for i, j in ((0, 1), (2, 3)):
            faces.append((ring*4+i, (ring+1)*4+i, (ring+1)*4+j, ring*4+j))
    return vertices, faces


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


def construct(document, mat):
    nodes, objects, max_error = {}, [], 0.0
    for variant in document["variants"]:
        vi = variant["index"]
        root = empty(f"Variant{vi}")
        # Separated only for geometry-context baking, restored before export.
        root.location.x = vi * 5.0
        leaf = empty("Leaf" + str(vi), root, transform(variant["hinge_transform"]))
        frame = empty("Frame" + str(vi), root)
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
            if annular:
                verts, source_faces = annular_geometry(solid)
            elif solid["id"].startswith("FRAME/") or solid["id"] == "COAMING":
                verts, source_faces = collar_geometry(solid)
            else:
                verts, source_faces = solid["vertices"], solid["faces"]
            sets = {0: [], 1: []}
            godot_basis = Matrix(solid["transform"]["basis"]).transposed()
            for face in source_faces:
                a, b, c = (Vector(verts[i]) for i in face[:3])
                normal = godot_basis @ (b - a).cross(c - a).normalized()
                side = (0 if normal.z < 0 else 1) if abs(normal.z) > .5 else (0 if variant["hinge_sign"] > 0 else 1)
                sets[side].append(face)
            for side, faces in sets.items():
                if not faces:
                    continue
                # Do not keep unused vertices: per-side bounds must describe only its actual geometry.
                used = sorted({i for face in faces for i in face})
                remap = {old: new for new, old in enumerate(used)}
                name = f"v{vi}_f{solid['index']:03d}_s{side}"
                obj = mesh_object(name, [verts[i] for i in used],
                                  [tuple(remap[i] for i in f) for f in faces], frame, pose, mat, recalc=False)
                if annular:
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
            verts, faces = radial(rivet["size"], rivet["radius"], rivet["id"])
            obj = mesh_object(name, verts, faces, frame, transform(rivet["transform"]), mat)
            max_error = max(max_error, exact_bounds(obj, rivet["size"]))
            radial_normals(obj, rivet["size"])
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


def painted_coordinates(objects, nodes, document):
    frame_bounds = {}
    for variant in document["variants"]:
        points = [CINV @ (obj.matrix_world @ vertex.co).to_4d()
                  for obj in objects if nodes[obj.name]["kind"] == "frame"
                  and nodes[obj.name]["variant"] == variant["index"] for vertex in obj.data.vertices]
        frame_bounds[variant["index"]] = (min(p.x for p in points), max(p.x for p in points),
                                           min(p.y for p in points), max(p.y for p in points))
    for obj in objects:
        row = nodes[obj.name]
        leaf = row["kind"] == "leaf" and row["id"].endswith("Steel/plate")
        frame = row["kind"] == "frame"
        colour = obj.data.color_attributes.new(name="PaintOwnership", type="BYTE_COLOR", domain="CORNER")
        uv = obj.data.uv_layers.new(name="PaintProjection")
        if leaf:
            part = document["variants"][row["variant"]]["groups"][row["group"]]["parts"][row["part"]]
        for polygon in obj.data.polygons:
            normal = polygon.normal if leaf else obj.matrix_world.to_3x3().inverted().transposed() @ polygon.normal
            normal = CINV.to_3x3() @ normal
            axis = max(range(3), key=lambda i: abs(normal[i]))
            for index in polygon.loop_indices:
                loop = obj.data.loops[index]
                # The solid slab's edge is machined steel; only its broad caps carry paint.
                colour.data[index].color = (float(leaf and axis == 2), float(row["side"]), float(frame), 1)
                if not (leaf or frame):
                    continue
                point = obj.data.vertices[loop.vertex_index].co
                point = CINV @ (point.to_4d() if leaf else (obj.matrix_world @ point).to_4d())
                if leaf:
                    xspan, yspan = part["size"][:2]
                    u, v = point.x / xspan + .5, point.y / yspan + .5
                else:
                    xlo, xhi, ylo, yhi = frame_bounds[row["variant"]]
                    xspan, yspan = xhi - xlo, yhi - ylo
                    u, v = (point.x - xlo) / xspan, (point.y - ylo) / yspan
                # The face projection must include depth on returns. Dropping Z
                # collapses their UVs and turns alpha relief into clamped bands.
                if axis == 0:
                    u = .5 + point.z / xspan
                elif axis == 1:
                    v = .5 + point.z / yspan
                uv.data[index].uv = (u, v)
        obj.data.color_attributes.active_color = colour
        obj.data.uv_layers.active_index = 0


def atlas(objects, resolution):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=2 / resolution,
                             area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    # Smart projection allocates subpixel cross-sections to narrow contour
    # islands. Give both principal axes two texels before the shared pack.
    for obj in objects:
        uv = obj.data.uv_layers.active.data
        for island in mesh_linked_uv_islands(obj.data):
            indices = [i for face in island for i in obj.data.polygons[face].loop_indices]
            points = np.array([uv[i].uv[:] for i in indices], dtype=np.float64)
            centre = points.mean(axis=0)
            _, axes = np.linalg.eigh(np.cov(points.T))
            projected = (points - centre) @ axes
            span = np.ptp(projected, axis=0)
            if min(span) <= 0:
                raise ValueError(f"collapsed UV island: {obj.name}")
            scale = np.maximum(1, 2 / resolution / span)
            for i, point in zip(indices, (projected * scale) @ axes.T + centre):
                uv[i].uv = point
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.uv.pack_islands(rotate=True, scale=True, margin=2 / resolution)
    bpy.ops.object.mode_set(mode="OBJECT")
    print("ATLAS unwrapped", len(objects), "objects", flush=True)


def bake_mesh(objects):
    # Join a copy, keeping per-part mesh/pose ownership untouched in the asset.
    bpy.ops.object.select_all(action="DESELECT")
    copies = []
    for obj in objects:
        copy = bpy.data.objects.new("Bake_" + obj.name, obj.data.copy())
        bpy.context.scene.collection.objects.link(copy)
        normal_matrix = obj.matrix_world.to_3x3().inverted().transposed()
        normals = {(polygon.index, obj.data.loops[index].vertex_index):
                   (normal_matrix @ obj.data.corner_normals[index].vector).normalized()
                   for polygon in obj.data.polygons for index in polygon.loop_indices}
        copy.data.transform(obj.matrix_world)
        # Joining mirrored faces otherwise reverses their winding but loses the
        # object reflection that told Cycles which side was outside the steel.
        if obj.matrix_world.determinant() < 0:
            copy.data.flip_normals()
        copy.data.normals_split_custom_set([
            normals[(polygon.index, copy.data.loops[index].vertex_index)]
            for polygon in copy.data.polygons for index in polygon.loop_indices])
        copy.select_set(True)
        copies.append(copy)
        obj.hide_render = True
        obj.hide_set(True)
    bpy.context.view_layer.objects.active = copies[0]
    bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.name = "HatchBakeContext"
    return joined


def bake_footprints(joined, resolution):
    """Give subpixel triangles a Cycles sample without changing delivered UVs."""
    source = joined.data.uv_layers["UVMap"]
    target = joined.data.uv_layers.new(name="BakeCoverage")
    repaired = 0
    for polygon in joined.data.polygons:
        loops = list(polygon.loop_indices)
        points = np.array([source.data[index].uv[:] for index in loops], dtype=np.float64)
        edges = np.roll(points, -1, axis=0) - points
        lengths = np.linalg.norm(edges, axis=1)
        area = abs(float(np.linalg.det(np.stack((edges[0], -edges[2])))))
        inradius = area / lengths.sum()
        if inradius * resolution < .75:
            # A bake margin needs an initial shaded pixel. Skinny bevels often
            # contain none. Rasterize their material onto a minimum footprint,
            # centred on the runtime centroid's texel, then let Cycles dilate.
            centre = points.mean(axis=0)
            axis = edges[int(np.argmax(lengths))] / max(lengths)
            across = np.array([-axis[1], axis[0]])
            local = np.stack(((points - centre) @ axis, (points - centre) @ across), axis=1)
            spans = np.ptp(local, axis=0)
            local *= np.maximum(1, (3 / resolution) / spans)
            centre = (np.floor(centre * resolution) + .5) / resolution
            points = centre + local[:, :1] * axis + local[:, 1:] * across
            repaired += 1
        for index, point in zip(loops, points):
            target.data[index].uv = point
    joined.data.uv_layers.active_index = 0
    print("BAKE_FOOTPRINTS", repaired, "subpixel triangles", flush=True)
    return repaired


def verify_bake_coverage(joined, coverage, resolution):
    pixels = np.empty(resolution * resolution * 4, dtype=np.float32)
    coverage.pixels.foreach_get(pixels)
    pixels = pixels.reshape(resolution, resolution, 4)
    uv = joined.data.uv_layers["UVMap"].data
    missing = []
    for polygon in joined.data.polygons:
        centre = np.mean([uv[index].uv[:] for index in polygon.loop_indices], axis=0)
        x, y = np.floor(centre * resolution).astype(int)
        if not (0 <= x < resolution and 0 <= y < resolution) or pixels[y, x, 0] == 0:
            missing.append(polygon.index)
    print("BAKE_COVERAGE triangles=%d uncovered=%d" % (len(joined.data.polygons), len(missing)), flush=True)
    if missing:
        raise RuntimeError("unbaked triangle centroids: " + str(missing[:8]))


def new_image(name, resolution, color=False):
    image = bpy.data.images.new(name, resolution, resolution, alpha=False, float_buffer=False)
    image.colorspace_settings.name = "sRGB" if color else "Non-Color"
    return image


def node_tree(mat):
    nt = mat.node_tree
    nt.nodes.clear()
    return nt, nt.nodes, nt.links


def weather_context(objects, nodes, document):
    # Fastener blooms and drips follow exported poses, including reflected faces.
    # This authoring field is baked away; it is not another runtime texture.
    xlo = min((obj.matrix_world @ v.co).x for obj in objects for v in obj.data.vertices)
    xhi = max((obj.matrix_world @ v.co).x for obj in objects for v in obj.data.vertices)
    height = max(v["aperture"][1] for v in document["variants"])
    width, rows = 2048, 1024
    x = np.linspace(xlo, xhi, width, dtype=np.float32)[None, :]
    z = np.linspace(0, height * 1.2, rows, dtype=np.float32)[:, None]
    contact = np.zeros((rows, width), dtype=np.float32)
    drips = np.zeros_like(contact)
    for obj in objects:
        row = nodes[obj.name]
        if row["kind"] == "frame":
            continue
        if row["kind"] == "leaf":
            part = document["variants"][row["variant"]]["groups"][row["group"]]["parts"][row["part"]]
            if part["shape"] != "cylinder" or not any(
                    key in row["id"] for key in ("Rivets/", "/bolt-", "/pivot-", "/barrel-")):
                continue
            radius = part["radius"]
        else:
            radius = document["variants"][row["variant"]]["frame_rivets"][row["part"]]["radius"]
        center = obj.matrix_world.translation
        dx = x - center.x
        drop = center.z - z
        halo = np.exp(-(dx * dx + drop * drop) / (radius * 2.0) ** 2)
        trail = np.exp(-(dx / (radius * .55)) ** 2) * np.exp(-np.maximum(drop, 0) / (height * .32)) * (drop >= 0)
        np.maximum(contact, halo, out=contact)
        np.maximum(drips, trail, out=drips)
    pixels = np.ones((rows, width, 4), dtype=np.float32)
    pixels[:, :, 0] = contact
    pixels[:, :, 1] = drips
    pixels[:, :, 2] = np.clip((height * .18 - z) / (height * .18), 0, 1)
    image = bpy.data.images.new("SourceFastenerWeather", width, rows, alpha=True, float_buffer=True)
    image.colorspace_settings.name = "Non-Color"
    image.pixels.foreach_set(pixels.ravel())
    return image, (xlo, xhi - xlo, height * 1.2)


def finish_recipe():
    spec = importlib.util.spec_from_file_location("hatch_scan_finish", Path(__file__).with_name("hatch_scan_finish.py"))
    finish = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(finish)
    return finish


def build_weather(mat, baked_ao=None, context=None):
    return finish_recipe().build(mat, baked_ao, context)


def save_image(image, path):
    image.filepath_raw = str(path)
    image.file_format = "PNG"
    image.save()
    return dict(file=path.name, width=image.size[0], height=image.size[1], bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def bake(joined, mat, output_dir, resolution, samples, context):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.seed = 7308
    scene.cycles.use_animated_seed = False
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 8
    scene.render.bake.margin = 8
    scene.render.bake.use_clear = True
    scene.render.bake.use_selected_to_active = False
    bpy.ops.object.select_all(action="DESELECT")
    joined.select_set(True)
    bpy.context.view_layer.objects.active = joined
    fields = build_weather(mat, context=context)
    nt = mat.node_tree
    target = nt.nodes.new("ShaderNodeTexImage")
    emission = nt.nodes.new("ShaderNodeEmission")
    images, rows = {}, []
    def execute(name, bake_type, socket=None, color=False):
        image = new_image("hatch_" + name, resolution, color)
        target.image = image
        nt.nodes.active = target
        if socket is not None:
            nt.links.new(socket, emission.inputs["Color"])
            nt.links.new(emission.outputs[0], fields["output"].inputs["Surface"])
        else:
            nt.links.new(fields["bsdf"].outputs[0], fields["output"].inputs["Surface"])
        print("BAKE", name, resolution, samples, flush=True)
        bpy.ops.object.bake(type=bake_type, uv_layer="BakeCoverage")
        images[name] = image
        rows.append(save_image(image, output_dir / ("hatch_" + name + ".png")))
        return image
    white = nt.nodes.new("ShaderNodeRGB")
    white.outputs[0].default_value = (1, 1, 1, 1)
    coverage = execute("coverage", "EMIT", white.outputs[0])
    verify_bake_coverage(joined, coverage, resolution)
    ao = execute("ao", "AO")
    pixels = np.empty(resolution * resolution * 4, dtype=np.float32)
    ao.pixels.foreach_get(pixels)
    ao_min, ao_max = float(pixels[0::4].min()), float(pixels[0::4].max())
    if ao_max - ao_min < .01:
        raise RuntimeError("geometry AO bake has no variation")
    fields = build_weather(mat, ao, context)
    target = nt.nodes.new("ShaderNodeTexImage")
    emission = nt.nodes.new("ShaderNodeEmission")
    albedo = execute("albedo", "EMIT", fields["layer_masks"], True)
    colors = np.empty(resolution * resolution * 4, dtype=np.float32)
    albedo.pixels.foreach_get(colors)
    occupied = np.any(colors.reshape(-1, 4)[:, :3] > 1 / 255, axis=1)
    geometry_ao = pixels.reshape(-1, 4)[occupied, 0]
    if not len(geometry_ao) or float(geometry_ao.std()) < .001:
        raise RuntimeError("AO has no variation on occupied geometry texels")
    nt.links.new(fields["geometry_normal"], fields["bsdf"].inputs["Normal"])
    execute("normal", "NORMAL")
    execute("height", "EMIT", fields["height"])
    execute("curvature", "EMIT", fields["curvature"])
    weather = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(fields["weather_masks"], weather.inputs[0])
    combine = nt.nodes.new("ShaderNodeCombineColor")
    ao_node = nt.nodes.new("ShaderNodeTexImage"); ao_node.image = ao
    separate = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(ao_node.outputs["Color"], separate.inputs[0])
    nt.links.new(separate.outputs[0], combine.inputs[0])
    nt.links.new(weather.outputs[0], combine.inputs[1])
    nt.links.new(weather.outputs[1], combine.inputs[2])
    execute("orm", "EMIT", combine.outputs[0])
    return images, rows, {"bake_coverage": "cycles_emit_conservative_subpixel_footprints", "uncovered_triangle_centroids": 0,
                          "ao_method": "cycles_geometry_ao", "ao_min": float(geometry_ao.min()),
                          "ao_max": float(geometry_ao.max()), "ao_mean": float(geometry_ao.mean()),
                          "ao_stdev": float(geometry_ao.std()), "atlas_occupied_fraction": float(occupied.mean()),
                          "bake_samples": samples, "bake_seed": 7308}


def final_material(mat, images):
    # Godot extracts GLB image names as hatch_<name>.png, matching the shared
    # external atlas files instead of allocating a second set of textures.
    for name, texture in images.items():
        texture.pack()
        texture.name = name
        texture.filepath_raw = "//" + name + ".png"
    nt, nodes, links = node_tree(mat)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    output = nodes.new("ShaderNodeOutputMaterial")
    links.new(bsdf.outputs[0], output.inputs["Surface"])
    def image(name):
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = images[name]
        tex.label = "Hatch shared " + name
        return tex.outputs["Color"]
    links.new(image("albedo"), bsdf.inputs["Base Color"])
    orm = image("orm")
    sep = nodes.new("ShaderNodeSeparateColor")
    links.new(orm, sep.inputs[0])
    links.new(sep.outputs[1], bsdf.inputs["Roughness"])
    links.new(sep.outputs[2], bsdf.inputs["Metallic"])
    normal = nodes.new("ShaderNodeNormalMap")
    links.new(image("normal"), normal.inputs["Color"])
    links.new(normal.outputs[0], bsdf.inputs["Normal"])
    # glTF exporter recognizes this named group for the occlusion channel.
    group = bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
    group.interface.new_socket(name="Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
    group.nodes.new("NodeGroupInput")
    occlusion = nodes.new("ShaderNodeGroup"); occlusion.node_tree = group
    links.new(sep.outputs[0], occlusion.inputs["Occlusion"])


def detail_textures(output_dir):
    rows = []
    for role, paths in finish_recipe().SCANS.items():
        for kind, path in zip(("albedo", "normal", "orm"), paths):
            image = bpy.data.images.load(str(path), check_existing=True).copy()
            image.colorspace_settings.name = "sRGB" if kind == "albedo" else "Non-Color"
            image.scale(512, 512)
            rows.append(save_image(image, output_dir / f"hatch_detail_{role}_{kind}.png"))
            bpy.data.images.remove(image)
    return rows


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
    recipe_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    finish_hash = hashlib.sha256(Path(__file__).with_name("hatch_scan_finish.py").read_bytes()).hexdigest()
    finish = finish_recipe()
    scan_inputs = {str(path.relative_to(finish.ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                   for paths in finish.SCANS.values() for path in paths}
    document = json.loads(raw)
    if document["schema_version"] != 1 or [v["hinge_sign"] for v in document["variants"]] != [1, -1]:
        raise ValueError("expected hatch schema 1, both ordered hinge signs")
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
    mat = material()
    objects, nodes, error = construct(document, mat)
    context = weather_context(objects, nodes, document)
    atlas(objects, args.resolution)
    painted_coordinates(objects, nodes, document)
    joined = bake_mesh(objects)
    bake_footprints(joined, args.resolution)
    if args.reuse_bakes:
        old = json.loads((output.parent / "parts.json").read_text())
        if (old["source_sha256"] != hashlib.sha256(raw).hexdigest() or
                old["build_recipe_sha256"] != recipe_hash or
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
                    build_recipe_sha256=recipe_hash, finish_recipe_sha256=finish_hash, scan_inputs=scan_inputs,
                    nodes=nodes, textures=textures, measurements=measures)
    (output.parent / "parts.json").write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
    print("HATCH_BUILD", json.dumps(measures, sort_keys=True), flush=True)
    print("EXPORT", output, output.stat().st_size, flush=True)


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
