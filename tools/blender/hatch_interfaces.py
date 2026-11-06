"""Explicit simulation-owned sealing, collar and pocket interface construction."""
import math
import bmesh
from mathutils import Vector
from mathutils.geometry import tessellate_polygon


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
