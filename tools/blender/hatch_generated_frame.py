"""Blender reduction and selected-to-active transfer for the frozen frame source."""
from pathlib import Path
import json
import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

import hatch_fit
from hatch_bake import C, CINV


def load_frames(document):
    root = Path(__file__).resolve().parents[2] / "art-source/hatch/hunyuan"
    manifest = json.loads((root / "provenance.json").read_text())
    hatch_fit.validate_manifest(root, manifest)
    name = manifest["selected"]
    recipe = json.loads((root / (name + "-selection.json")).read_text())
    vertices, faces = hatch_fit.read_source_glb(root / (name + ".glb"))
    frames = hatch_fit.fit_frame(document, vertices, faces, recipe)
    document["generated_sources"] = dict(schema_version=1, selected=name,
                                          source_sha256=recipe["source_sha256"],
                                          selection_sha256=hatch_fit.sha256(root / (name + "-selection.json")),
                                          provenance_sha256=hatch_fit.sha256(root / "provenance.json"))
    document["fit_recipe"] = dict(schema_version=1, slice="fitted_frame_existing_leaf_wheels",
                                   ring_depth_scales=[row.depth_scale for row in frames],
                                   source_front_cut_planes=[row.source_relief_plane for row in frames],
                                   front_relief_depth_scale_ratios=[row.depth_scale_ratio for row in frames],
                                   operations=recipe["operations"][:-1] + [
                                       "Discard the hidden tube behind the source flank equator; close the annular cut and fit visible front relief between exported front and rear planes.",
                                       "Repair the original fused hinge attachment using the source's clean opposite ring half before relocating the extracted mount to two stations.",
                                       "Seat the last 1 mm of the source flanks on the exact exported loops, retaining the generated crown; reduce the open crown independently and re-tessellate that functional seating cut.",
                                       "Extract the straight exposed source barrel between its rounded end cap and plate attachment before fitting knuckle reservations; retain ancestry.",
                                       "Trim rendered post/top/stop interfaces inside unchanged collision reservations; retain the full floor bridge."])
    return frames


def local_region(region, pose):
    basis = np.asarray(pose["basis"])
    vertices = np.einsum("ij,kj->ik", region.vertices - pose["origin"], basis)
    faces = region.faces[:, ::-1] if np.linalg.det(basis) < 0 else region.faces
    return vertices, faces


def reduce_region(region, pose, triangle_budget, create, parent, material):
    vertices, faces = local_region(region, pose)
    high = create("High_" + region.id.replace("/", "_"), vertices, faces, parent, Matrix.Identity(4), material, recalc=False)
    # Welding below Blender's float epsilon misses even identical coordinates.
    # Index exact float32 positions instead of moving nearby source vertices.
    coordinates = np.asarray([vertex.co[:] for vertex in high.data.vertices], dtype=np.float32)
    unique, inverse = np.unique(coordinates, axis=0, return_inverse=True)
    indexed = [tuple(int(inverse[i]) for i in polygon.vertices) for polygon in high.data.polygons]
    high.data.clear_geometry()
    high.data.from_pydata(unique.tolist(), [], indexed)
    high.data.update()
    for polygon in high.data.polygons:
        polygon.use_smooth = True
    low = bpy.data.objects.new("Low_" + high.name, high.data.copy())
    bpy.context.scene.collection.objects.link(low)
    low.parent = parent
    low.matrix_basis = high.matrix_basis
    bm = bmesh.new()
    bm.from_mesh(low.data)
    bm.verts.ensure_lookup_table()
    coordinates = np.asarray([vertex.co[:] for vertex in bm.verts])
    pins = {vertex.index for edge in bm.edges if edge.is_boundary for vertex in edge.verts}
    for axis in range(3):
        pins.add(int(coordinates[:, axis].argmin()))
        pins.add(int(coordinates[:, axis].argmax()))
    bm.free()
    weights = low.vertex_groups.new(name="PinnedInterfaces")
    weights.add(sorted(pins), 1, "REPLACE")
    modifier = low.modifiers.new("BoundedSourceReduction", "DECIMATE")
    modifier.ratio = min(1, triangle_budget / len(low.data.polygons))
    modifier.use_collapse_triangulate = True
    modifier.vertex_group = weights.name
    modifier.invert_vertex_group = True
    modifier.vertex_group_factor = 1000
    bpy.context.view_layer.objects.active = low
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    points = np.asarray([tuple((CINV @ vertex.co.to_4d())[:3]) for vertex in low.data.vertices])
    triangles = np.asarray([tuple(face.vertices) for face in low.data.polygons])
    # Pinned extrema do not stop another collapse vertex overshooting them.
    # Project the reduction back onto the source component's local bounds.
    points = np.clip(points, vertices.min(axis=0), vertices.max(axis=0))
    points, remap = np.unique(points, axis=0, return_inverse=True)
    triangles = remap[triangles]
    tri = points[triangles]
    positive = np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1) > 0
    triangles = triangles[positive]
    used, remap = np.unique(triangles, return_inverse=True)
    points, triangles = points[used].tolist(), remap.reshape(-1, 3).tolist()
    high.hide_render = True
    high.hide_set(True)
    bpy.data.objects.remove(low, do_unlink=True)
    return points, triangles, high


def transfer_normals(objects, high_sources, material, output_dir, resolution):
    """Bake isolated matching high/low pairs into the existing normal atlas."""
    from hatch_bake import bake_mesh, save_image
    lows, highs = [], []
    source_material = bpy.data.materials.new("SourceGeometricNormals")
    source_material.use_nodes = True
    existing_material = material.copy()
    bsdf = next(node for node in existing_material.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
    output = next(node for node in existing_material.node_tree.nodes if node.type == "OUTPUT_MATERIAL")
    existing_material.node_tree.links.new(bsdf.outputs[0], output.inputs["Surface"])
    for index, obj in enumerate(objects):
        shift = Vector(((index % 40) * 4, (index // 40) * 4, 0))
        for source, destination in ((obj, lows), (high_sources.get(obj.name, obj), highs)):
            copy = bpy.data.objects.new("Transfer_" + source.name, source.data.copy())
            bpy.context.scene.collection.objects.link(copy)
            copy.matrix_world = source.matrix_world.copy()
            copy.location += shift
            if destination is highs:
                copy.data.materials.clear()
                copy.data.materials.append(source_material if obj.name in high_sources else existing_material)
                for polygon in copy.data.polygons:
                    polygon.material_index = 0
            destination.append(copy)
    low = bake_mesh(lows)
    high = bake_mesh(highs)
    for obj in lows + highs:
        bpy.data.objects.remove(obj, do_unlink=True)
    low.hide_render = False
    low.hide_set(False)
    high.hide_render = False
    high.hide_set(False)
    low.data.materials.clear()
    low.data.materials.append(material)
    for polygon in low.data.polygons:
        polygon.material_index = 0
    image = bpy.data.images.new("hatch_high_to_low_normal", resolution, resolution, alpha=True)
    image.colorspace_settings.name = "Non-Color"
    target = material.node_tree.nodes.new("ShaderNodeTexImage")
    target.image = image
    material.node_tree.nodes.active = target
    scene = bpy.context.scene
    scene.render.bake.use_selected_to_active = True
    scene.render.bake.use_clear = True
    scene.render.bake.cage_extrusion = .005
    scene.render.bake.max_ray_distance = .03
    bpy.ops.object.select_all(action="DESELECT")
    high.select_set(True)
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    print("BAKE selected_to_active isolated source pairs", len(objects), flush=True)
    bpy.ops.object.bake(type="NORMAL", uv_layer="UVMap")
    row = save_image(image, output_dir / "hatch_normal.png")
    scene.render.bake.use_selected_to_active = False
    bpy.data.objects.remove(high, do_unlink=True)
    bpy.data.objects.remove(low, do_unlink=True)
    return image, row


def reduce_ring(frame, variant, create, material, triangle_budget=1200):
    """Reduce the connected bead before partitioning its semantic reservations."""
    regions = list(frame.ring.values())
    points = np.concatenate([region.vertices for region in regions])
    offsets = np.cumsum([0] + [len(region.vertices) for region in regions[:-1]])
    faces = np.concatenate([region.faces + offset for region, offset in zip(regions, offsets)])
    # Shared cut coordinates differ only by arithmetic roundoff. A 0.1 um
    # reduction grid joins them, below the 1 um exact-interface requirement.
    unique, inverse = np.unique(np.round(points, 7), axis=0, return_inverse=True)
    faces = inverse[faces]
    area = np.linalg.norm(np.cross(unique[faces[:, 1]] - unique[faces[:, 0]], unique[faces[:, 2]] - unique[faces[:, 0]]), axis=1)
    faces = faces[area > 0]
    ring_solid = next(s for s in variant["frame_solids"] if s["id"] in frame.ring)
    rear_plane = ring_solid["transform"]["origin"][2] + variant["hinge_sign"] * ring_solid["size"][2] / 2
    land_top = rear_plane - variant["hinge_sign"] * .001
    # Reduce the open crown only. Letting the decimator merge its rear cap
    # across the thin seat folds the cap up through the mouth-side flank.
    unique, faces, _ = hatch_fit.clip_source_plane(
        unique, faces, np.arange(len(faces)), 2, land_top, -variant["hinge_sign"])
    obj = create("ConnectedRingReduction", unique, faces, None, Matrix.Identity(4), material, recalc=False)
    group = obj.vertex_groups.new(name="SilhouetteLandmarks")
    coordinates = np.asarray([tuple((CINV @ vertex.co.to_4d())[:3]) for vertex in obj.data.vertices])
    pins = set()
    ring_solid = next(s for s in variant["frame_solids"] if s["id"] in frame.ring)
    rear_plane = ring_solid["transform"]["origin"][2] + variant["hinge_sign"] * ring_solid["size"][2] / 2
    land_top = rear_plane - variant["hinge_sign"] * .001
    for target in variant["fit"]["ring"]["inner"] + variant["fit"]["ring"]["outer"]:
        distances = np.linalg.norm(coordinates[:, :2] - target[:2], axis=1)
        nearest = int(distances.argmin())
        if distances[nearest] > 1e-6:
            raise hatch_fit.FitError("reduction ring: missing exact loop landmark")
        aligned = np.flatnonzero(distances <= 1e-6)
        pins.add(int(aligned[coordinates[aligned, 2].argmin()]))
        pins.add(int(aligned[coordinates[aligned, 2].argmax()]))
        seating = int(aligned[abs(coordinates[aligned, 2] - land_top).argmin()])
        if abs(coordinates[seating, 2] - land_top) > 1e-6:
            raise hatch_fit.FitError("reduction ring: missing square seating-land landmark")
        pins.add(seating)
    pins.update([int(coordinates[:, 2].argmin()), int(coordinates[:, 2].argmax())])
    group.add(sorted(pins), 1, "REPLACE")
    modifier = obj.modifiers.new("ConnectedBeadReduction", "DECIMATE")
    modifier.ratio = triangle_budget / len(obj.data.polygons)
    modifier.use_collapse_triangulate = True
    modifier.vertex_group = group.name
    modifier.invert_vertex_group = True
    modifier.vertex_group_factor = 1000
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    vertices = np.asarray([tuple((CINV @ vertex.co.to_4d())[:3]) for vertex in obj.data.vertices])
    triangles = np.asarray([tuple(polygon.vertices) for polygon in obj.data.polygons])
    bpy.data.objects.remove(obj, do_unlink=True)
    depth = ring_solid["transform"]["origin"][2]
    vertices[:, 2] = np.clip(vertices[:, 2], depth - ring_solid["size"][2] / 2, depth + ring_solid["size"][2] / 2)
    inner = np.asarray(variant["fit"]["ring"]["inner"])[:, :2]
    outer = np.asarray(variant["fit"]["ring"]["outer"])[:, :2]
    outline_a = np.concatenate([inner, outer])
    outline_b = np.concatenate([np.roll(inner, -1, axis=0), np.roll(outer, -1, axis=0)])
    outline_edges = outline_b - outline_a
    def nearest_outline(point):
        fraction = np.clip(np.einsum("ij,ij->i", point - outline_a, outline_edges) / np.einsum("ij,ij->i", outline_edges, outline_edges), 0, 1)
        projected = outline_a + outline_edges * fraction[:, None]
        distances = np.linalg.norm(projected - point, axis=1)
        index = int(distances.argmin())
        return float(distances[index]), projected[index]
    # Decimation may move a seating-rim point inward. Restore the square
    # source-cut land before clipping or float32 storage can expose its cap.
    rear = depth + variant["hinge_sign"] * ring_solid["size"][2] / 2
    for point in vertices:
        if abs(point[2] - rear) <= .001:
            distance, projected = nearest_outline(point[:2])
            if distance <= .001:
                point[:2] = projected
        if abs(point[2] - rear) <= 1e-6:
            point[2] = rear
    # Decimation can fold a millimetre-high land into its annular cap even
    # while preserving the loop landmarks. Re-tessellate only that functional
    # cut surface; the generated crown above it remains the reduced source.
    land_top = rear - variant["hinge_sign"] * .001
    vertices, triangles, _ = hatch_fit.clip_source_plane(
        vertices, triangles, np.arange(len(triangles)), 2, land_top, -variant["hinge_sign"])
    for point in vertices:
        if abs(point[2] - land_top) < 1e-7:
            distance, projected = nearest_outline(point[:2])
            if distance > .001:
                raise hatch_fit.FitError("reduced crown no longer meets its seating outline")
            point[:2] = projected
            point[2] = land_top
    vertices, triangles = vertices.tolist(), triangles.tolist()
    def seat_quad(corners, outward):
        base = len(vertices)
        vertices.extend(corners)
        for face in [[base, base + 1, base + 2], [base, base + 2, base + 3]]:
            a, b, c = np.asarray([vertices[i] for i in face])
            if np.dot(np.cross(b - a, c - a), outward) < 0:
                face.reverse()
            triangles.append(face)
    for index in range(len(inner)):
        following = (index + 1) % len(inner)
        inside = [[*inner[i], z] for i, z in [(index, rear), (following, rear), (following, land_top), (index, land_top)]]
        outside = [[*outer[i], z] for i, z in [(index, rear), (following, rear), (following, land_top), (index, land_top)]]
        middle = (inner[index] + inner[following]) / 2
        centre = inner.mean(axis=0)
        seat_quad(inside, [*(centre - middle), 0])
        seat_quad(outside, [*(middle - centre), 0])
        seat_quad([inside[0], outside[0], outside[1], inside[1]], [0, 0, variant["hinge_sign"]])
    vertices, triangles = np.asarray(vertices), np.asarray(triangles)
    # Retain the source face used for high-poly projection, not a new face ID
    # from the decimator's transient topology.
    from mathutils.kdtree import KDTree
    tree = KDTree(len(points))
    for index, point in enumerate(points):
        tree.insert(tuple(point), index)
    tree.balance()
    source_at_vertex = np.concatenate([np.repeat(region.source_faces, 3) for region in regions])
    projected = [source_at_vertex[tree.find(tuple(center))[1]] for center in vertices[triangles].mean(axis=1)]
    bm = bmesh.new()
    ancestry = bm.faces.layers.int.new("SourceFace")
    reservation = bm.faces.layers.int.new("Reservation")
    for solid_index, solid in enumerate(variant["frame_solids"]):
        if solid["id"] not in frame.ring:
            continue
        section = np.asarray(solid["section"]) + solid["transform"]["origin"][:2]
        a, b = section[1] - section[0], section[2] - section[1]
        if a[0] * b[1] - a[1] * b[0] < 0:
            section = section[::-1]
        lo, hi = section.min(axis=0), section.max(axis=0)
        bounds_lo = vertices[triangles, :2].min(axis=1)
        bounds_hi = vertices[triangles, :2].max(axis=1)
        candidates = np.flatnonzero(((bounds_hi >= lo) & (bounds_lo <= hi)).all(axis=1))
        output_points, output_faces, output_source = [], [], []
        for index in candidates:
            polygon = list(vertices[triangles[index]])
            for a, b in zip(section, np.roll(section, -1, axis=0)):
                if not polygon:
                    break
                normal = np.array([a[1] - b[1], b[0] - a[0]])
                clipped = []
                previous = polygon[-1]
                before = (previous[:2] - a) @ normal
                for current in polygon:
                    after = (current[:2] - a) @ normal
                    if (before < 0) != (after < 0):
                        clipped.append(previous + (current - previous) * before / (before - after))
                    if after >= 0:
                        clipped.append(current)
                    previous, before = current, after
                polygon = clipped
            for corner in range(1, len(polygon) - 1):
                tri = [polygon[0], polygon[corner], polygon[corner + 1]]
                if np.linalg.norm(np.cross(tri[1] - tri[0], tri[2] - tri[0])) == 0:
                    continue
                start = len(output_points)
                output_points.extend(tri)
                output_faces.append([start, start + 1, start + 2])
                output_source.append(projected[index])
        cut_vertices = [bm.verts.new(point) for point in output_points]
        for face, source in zip(output_faces, output_source):
            polygon = bm.faces.new([cut_vertices[index] for index in face])
            polygon[ancestry] = int(source)
            polygon[reservation] = solid_index
    # Clean cut slivers on the welded assembly. Cleaning each semantic cell
    # independently moves their shared skin differently and opens ray-sized
    # cracks. Face tags survive the shared cleanup and restore the batches.
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-7)
    # Keep the shallow land's real faces well-conditioned by subdividing its
    # long skin, rather than collapsing the millimetre-high seat itself.
    for axis in range(2):
        low = min(v.co[axis] for v in bm.verts)
        high = max(v.co[axis] for v in bm.verts)
        cuts = math.ceil((high - low) / .2)
        for cut in range(1, cuts):
            point = Vector((0, 0, 0))
            point[axis] = low + (high - low) * cut / cuts
            normal = Vector((1, 0, 0) if axis == 0 else (0, 1, 0))
            bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), dist=1e-7, plane_co=point, plane_no=normal)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    landmarks = np.asarray(variant["fit"]["ring"]["inner"] + variant["fit"]["ring"]["outer"])
    while True:
        bad = None
        for face in bm.faces:
            p = np.asarray([v.co[:] for v in face.verts])
            edges = np.roll(p, -1, axis=0) - p
            lengths = np.linalg.norm(edges, axis=1)
            area = np.linalg.norm(np.cross(edges[0], edges[1]))
            if area < 1e-10 or area / max(lengths * np.roll(lengths, 1)) < .002:
                bad = face
                break
        if bad is None:
            break
        def crosses_seating_land(edge):
            a, b = (np.asarray(v.co[:]) for v in edge.verts)
            planes = [rear, rear - variant["hinge_sign"] * .001]
            levels = [next((i for i, plane in enumerate(planes) if abs(p[2] - plane) < 1e-7), None) for p in [a, b]]
            return (None not in levels and levels[0] != levels[1]
                    and nearest_outline(a[:2])[0] < 1e-6
                    and nearest_outline(b[:2])[0] < 1e-6)
        # A short vertical seating edge is a thickness constraint, not a cut
        # sliver. Collapse along the outline instead, retaining both land planes.
        def owners(vertex):
            return {face[reservation] for face in vertex.link_faces}
        def preserves_partitions(edge):
            a, b = (owners(vertex) for vertex in edge.verts)
            return a <= b or b <= a
        eligible = [edge for edge in bad.edges if not crosses_seating_land(edge) and preserves_partitions(edge)]
        if not eligible:
            raise hatch_fit.FitError("ring cleanup cannot preserve its seating land and semantic boundaries")
        edge = min(eligible, key=lambda e: e.calc_length())
        a, b = edge.verts
        ap, bp = np.asarray(a.co[:]), np.asarray(b.co[:])
        pin_a = 2 if np.linalg.norm(landmarks[:, :2] - ap[:2], axis=1).min() < 1e-6 else int(nearest_outline(ap[:2])[0] < 1e-6)
        pin_b = 2 if np.linalg.norm(landmarks[:, :2] - bp[:2], axis=1).min() < 1e-6 else int(nearest_outline(bp[:2])[0] < 1e-6)
        # Shared semantic boundaries constrain the collapse location too.
        # Moving their vertex into one cell leaks a neighbour's tagged faces
        # beyond its reservation even though the overall ring stays closed.
        if owners(a) < owners(b):
            destination = b.co.copy()
        elif owners(b) < owners(a):
            destination = a.co.copy()
        else:
            destination = a.co.copy() if pin_a and pin_a >= pin_b else b.co.copy() if pin_b else (a.co + b.co) / 2
        if pin_a and pin_b:
            for point in [a.co, b.co]:
                if any(abs(point.z - plane) < 1e-7 for plane in [rear, rear - variant["hinge_sign"] * .001]):
                    destination.z = point.z
                    break
        bmesh.ops.pointmerge(bm, verts=[a, b], merge_co=destination)
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    bm.verts.index_update()
    result = {}
    for solid_index, solid in enumerate(variant["frame_solids"]):
        if solid["id"] not in frame.ring:
            continue
        selected = [face for face in bm.faces if face[reservation] == solid_index]
        section = np.asarray(solid["section"]) + solid["transform"]["origin"][:2]
        def internal_radial_wall(face):
            points = np.asarray([v.co[:] for v in face.verts])
            if np.ptp(points[:, 2]) < 1e-6:
                return False
            for start, end in [(0, 3), (1, 2)]:
                a, b = section[start], section[end]
                edge = b - a
                distances = abs(edge[0] * (points[:, 1] - a[1]) - edge[1] * (points[:, 0] - a[0])) / np.linalg.norm(edge)
                if distances.max() < 1e-6:
                    return True
            return False
        # A collapse onto a shared cut may leave a folded zero-width skin
        # between the two cells. It is an internal wall, not bead surface.
        selected = [face for face in selected if not internal_radial_wall(face)]
        used = sorted({v for face in selected for v in face.verts}, key=lambda v: v.index)
        indices = {v: i for i, v in enumerate(used)}
        result[solid["id"]] = hatch_fit.FittedRegion(
            solid["id"], [v.co[:] for v in used],
            [[indices[v] for v in face.verts] for face in selected],
            [face[ancestry] for face in selected])
    bm.free()
    print("CONNECTED_RING_REDUCTION", len(faces), "->", len(triangles), "partitioned", sum(len(region.faces) for region in result.values()), flush=True)
    return result
