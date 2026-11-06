"""Offline generated-source validation and fitting. No simulation dimensions live here."""
import hashlib
import json
from pathlib import Path
import struct

import numpy as np


class FitError(ValueError):
    """A source or fitted region cannot meet its named exported contract."""


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def validate_manifest(root, manifest):
    if manifest.get("schema_version") != 1:
        raise FitError("provenance: unsupported schema")
    root = Path(root).resolve()
    for name, digest in sorted(manifest["files"].items()):
        path = (root / name).resolve()
        if not path.is_relative_to(root):
            raise FitError(f"provenance: path escapes source directory: {name}")
        if not path.is_file():
            raise FitError(f"provenance: missing source {name}")
        if sha256(path) != digest:
            raise FitError(f"provenance: source hash mismatch: {name}")


def read_source_glb(path):
    """Read raw indexed topology without importer welding or zero-area cleanup."""
    raw = Path(path).read_bytes()
    if len(raw) < 20 or struct.unpack_from("<III", raw) != (0x46546C67, 2, len(raw)):
        raise FitError(f"source {path}: invalid GLB header")
    chunks = {}
    offset = 12
    while offset < len(raw):
        size, kind = struct.unpack_from("<II", raw, offset)
        offset += 8
        if offset + size > len(raw):
            raise FitError(f"source {path}: truncated GLB chunk")
        chunks[kind] = raw[offset:offset + size]
        offset += size
    document = json.loads(chunks[0x4E4F534A])
    binary = chunks[0x004E4942]
    nodes = [node for node in document["nodes"] if "mesh" in node]
    if len(nodes) != 1 or any(key in nodes[0] for key in ("matrix", "translation", "rotation", "scale")):
        raise FitError(f"source {path}: expected one identity-frame source mesh")
    primitives = document["meshes"][nodes[0]["mesh"]]["primitives"]
    if len(primitives) != 1 or primitives[0].get("mode", 4) != 4:
        raise FitError(f"source {path}: expected one indexed triangle primitive")

    def accessor(index, width, dtype, component):
        record = document["accessors"][index]
        if record["componentType"] != component or "sparse" in record:
            raise FitError(f"source {path}: unsupported accessor encoding")
        view = document["bufferViews"][record["bufferView"]]
        if view.get("buffer", 0) != 0 or "byteStride" in view:
            raise FitError(f"source {path}: unsupported source buffer layout")
        offset = view.get("byteOffset", 0) + record.get("byteOffset", 0)
        return np.frombuffer(binary, dtype=dtype, count=record["count"] * width, offset=offset).reshape(-1, width).copy()

    primitive = primitives[0]
    vertices = accessor(primitive["attributes"]["POSITION"], 3, "<f4", 5126).astype(np.float64)
    record = document["accessors"][primitive["indices"]]
    component = record["componentType"]
    if component not in (5123, 5125):
        raise FitError(f"source {path}: unsupported source index type")
    indices = accessor(primitive["indices"], 1, "<u4" if component == 5125 else "<u2", component)
    if indices.size % 3:
        raise FitError(f"source {path}: incomplete triangle indices")
    return vertices, indices.reshape(-1, 3).astype(np.int64)


def _indices(values, length, context):
    indices = np.asarray(values)
    if indices.ndim != 1 or (indices.size and (indices.dtype.kind not in "iu" or indices.min() < 0 or indices.max() >= length)):
        raise FitError(f"{context}: invalid selection index")
    return indices.astype(np.int64)


def validate_source(vertices, faces, recipe, digest, reservations):
    context = f"source {digest}"
    if recipe.get("schema_version") != 1:
        raise FitError(f"{context}: unsupported fitting schema")
    if recipe["source_sha256"] != digest:
        raise FitError(f"{context}: source hash mismatch")
    vertices, faces = np.asarray(vertices), np.asarray(faces)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or not np.isfinite(vertices).all():
        raise FitError(f"{context}: vertices must be finite triples")
    if faces.ndim != 2 or faces.shape[1] != 3 or faces.dtype.kind not in "iu" or not faces.size or faces.min() < 0 or faces.max() >= len(vertices):
        raise FitError(f"{context}: invalid triangle index")
    registration = np.asarray(recipe["registration"], dtype=float)
    if registration.shape != (4, 4) or not np.isfinite(registration).all() or not np.array_equal(registration[3], [0, 0, 0, 1]) or abs(np.linalg.det(registration[:3, :3])) < 1e-12:
        raise FitError(f"{context}: invalid source registration")
    triangles = vertices[faces]
    areas = np.linalg.norm(np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]), axis=1)
    discarded = _indices(recipe["discarded_faces"], len(faces), context)
    if np.any(areas[discarded] != 0):
        raise FitError(f"{context}: cannot discard a positive-area source triangle")
    coverage = np.zeros(len(faces), dtype=np.int32)
    np.add.at(coverage, discarded, 1)
    assigned = 0
    for region in recipe["regions"]:
        part = f"{context} part {region['role']}"
        selection = _indices(region["faces"], len(faces), part)
        if not selection.size:
            raise FitError(f"{part}: empty region")
        if np.any(areas[selection] == 0):
            raise FitError(f"{part}: degenerate source triangle must be declared and removed")
        if region["role"] == "ring" and not all(region["landmarks"].get(key) for key in ("inner_loop", "outer_loop")):
            raise FitError(f"{part}: absent registration landmark")
        for name, values in region["landmarks"].items():
            _indices(values, len(vertices), f"{part} landmark {name}")
        if not region["target_reservations"] or not set(region["target_reservations"]).issubset(reservations):
            raise FitError(f"{part}: unknown target reservation")
        np.add.at(coverage, selection, 1)
        assigned += len(selection)
    if np.any(coverage > 1):
        raise FitError(f"{context}: overlapping source selections")
    if np.any(coverage == 0):
        raise FitError(f"{context}: unassigned source triangles")
    return {"assigned_triangles": assigned, "discarded_triangles": len(discarded),
            "surface_area": float(areas.sum() / 2)}


class FittedRegion:
    def __init__(self, part_id, vertices, faces, source_faces):
        self.id = part_id
        self.vertices = np.asarray(vertices, dtype=np.float64)
        self.faces = np.asarray(faces, dtype=np.int64)
        self.source_faces = np.asarray(source_faces, dtype=np.int64)
        triangles = self.vertices[self.faces]
        cross = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
        lengths = np.linalg.norm(cross, axis=1)
        if not np.isfinite(cross).all() or np.any(lengths == 0):
            raise FitError(f"fit part {part_id}: nonfinite or degenerate triangle")
        self.normals = cross / lengths[:, None]


def _clip_polygon(points, normal):
    result = []
    previous = points[-1]
    before = float(previous[:2] @ normal)
    for current in points:
        after = float(current[:2] @ normal)
        if (before < 0) != (after < 0):
            result.append(previous + (current - previous) * before / (before - after))
        if after >= 0:
            result.append(current)
        previous, before = current, after
    return result


def _source_slice(vertices, faces, angle):
    direction = np.array([np.cos(angle), np.sin(angle)])
    triangles = vertices[faces]
    signed = triangles[:, :, 0] * direction[1] - triangles[:, :, 1] * direction[0]
    crosses = (signed.min(axis=1) <= 0) & (signed.max(axis=1) >= 0)
    triangles, signed = triangles[crosses], signed[crosses]
    intersections = []
    for a, b in ((0, 1), (1, 2), (2, 0)):
        valid = (signed[:, a] * signed[:, b] <= 0) & (signed[:, a] != signed[:, b])
        values, points = signed[valid], triangles[valid]
        weight = values[:, a] / (values[:, a] - values[:, b])
        points = points[:, a] + weight[:, None] * (points[:, b] - points[:, a])
        radii = points[:, :2] @ direction
        intersections.extend(radii[radii > 0])
    if not intersections:
        raise FitError(f"separate ring: no positive ray intersections at {angle}")
    return min(intersections), max(intersections)


def fit_ring(variant, vertices, faces, recipe, depth_scale=None):
    """Split raw triangles at exported stations, then register both ring loops."""
    region = next(row for row in recipe["regions"] if row["role"] == "ring")
    selected = np.asarray(region["faces"], dtype=np.int64)
    inner = np.asarray(variant["fit"]["ring"]["inner"])
    outer = np.asarray(variant["fit"]["ring"]["outer"])
    centre = inner[:, :2].mean(axis=0)
    theta = np.unwrap(np.arctan2(inner[:, 1] - centre[1], inner[:, 0] - centre[0]))
    if theta[-1] < theta[0]:
        raise FitError("fit ring: exported loop must be counterclockwise")
    theta = np.append(theta, theta[0] + 2 * np.pi)
    # Bucket projected triangles only to accelerate exact source-silhouette rays.
    # Interpolating station radii across a long jamb misses its curved boundary.
    bin_count = 256
    angles = np.arctan2(vertices[faces[selected], 1], vertices[faces[selected], 0]) % (2 * np.pi)
    bins = np.floor(angles * bin_count / (2 * np.pi)).astype(int)
    buckets = [[] for _ in range(bin_count)]
    for face_index, row in zip(selected, bins):
        lo, hi = int(row.min()), int(row.max())
        spans = list(range(lo, hi + 1)) if hi - lo <= bin_count // 2 else list(range(hi, bin_count)) + list(range(lo + 1))
        for index in spans:
            buckets[index].append(face_index)
    buckets = [faces[np.asarray(bucket, dtype=np.int64)] for bucket in buckets]
    body_min, body_max = float(vertices[:, 2].min()), float(vertices[:, 2].max())
    rear_buckets = [bucket[(abs(vertices[bucket, 2] - body_min) < 1e-10).all(axis=1)] for bucket in buckets]
    radial_cache = {}

    def source_radii(point, rear=False):
        key = (rear, *point[:2])
        if key not in radial_cache:
            angle = np.arctan2(point[1], point[0]) % (2 * np.pi)
            bucket = min(bin_count - 1, int(angle * bin_count / (2 * np.pi)))
            radial_cache[key] = _source_slice(vertices, (rear_buckets if rear else buckets)[bucket], angle)
        return radial_cache[key]

    face_angles = np.arctan2(vertices[faces, 1], vertices[faces, 0])
    sectors = np.searchsorted(theta, (face_angles - theta[0]) % (2 * np.pi) + theta[0], side="right") - 1
    multi_sector = np.any(sectors != sectors[:, :1], axis=1)
    solids = {row["id"]: row for row in variant["frame_solids"]}
    result = {}
    for index, part_id in enumerate(variant["fit"]["ring"]["reservation_ids"]):
        following = (index + 1) % len(inner)
        start, end = theta[index:index + 2]
        normal_a = np.array([-np.sin(start), np.cos(start)])
        normal_b = np.array([np.sin(end), -np.cos(end)])
        candidates = np.any(sectors == index, axis=1) | multi_sector
        ids = selected[candidates[selected]]
        points, triangles, ancestry = [], [], []
        for face_index in ids:
            polygon = _clip_polygon(list(vertices[faces[face_index]]), normal_a)
            if polygon:
                polygon = _clip_polygon(polygon, normal_b)
            if len(polygon) < 3:
                continue
            mapped = []
            for point in polygon:
                angle = (np.arctan2(point[1], point[0]) - start) % (2 * np.pi)
                if angle > np.pi:
                    angle -= 2 * np.pi
                direction = point[:2] / np.linalg.norm(point[:2])
                edge = inner[following, :2] - inner[index, :2]
                origin = inner[index, :2] - centre
                cross = lambda a, b: a[0] * b[1] - a[1] * b[0]
                fraction = np.clip(-cross(origin, direction) / cross(edge, direction), 0, 1)
                low, high = source_radii(point)
                across = (np.linalg.norm(point[:2]) - low) / (high - low)
                if across < -0.01 or across > 1.01:
                    raise FitError(f"fit source {recipe['source_sha256']} part {part_id}: radial boundary exceeds registration by {across}")
                across = np.clip(across, 0, 1)
                # The cut seats against the unchanged square lip. Keep its
                # last millimetre on the exact loops, rather than letting the
                # source's equator noise expose the rear cap from the mouth.
                if depth_scale is not None and (point[2] - body_min) * depth_scale <= .001 + 1e-10:
                    if abs(point[2] - body_min) < 1e-10:
                        cut_low, cut_high = source_radii(point, rear=True)
                        across = np.clip((np.linalg.norm(point[:2]) - cut_low) / (cut_high - cut_low), 0, 1)
                    else:
                        across = 0 if across < .5 else 1
                inside = inner[index, :2] * (1 - fraction) + inner[following, :2] * fraction
                outside = outer[index, :2] * (1 - fraction) + outer[following, :2] * fraction
                xy = inside * (1 - across) + outside * across
                solid = solids[part_id]
                if depth_scale is None:
                    depth = solid["transform"]["origin"][2] + solid["size"][2] / 2
                    depth -= (point[2] - body_min) / (body_max - body_min) * solid["size"][2]
                else:
                    into = variant["hinge_sign"]
                    front = solid["transform"]["origin"][2] - into * solid["size"][2] / 2
                    depth = front + into * (body_max - point[2]) * depth_scale
                mapped.append(np.array([xy[0], xy[1], depth]))
            for corner in range(1, len(mapped) - 1):
                offset = len(points)
                triangle = [mapped[0], mapped[corner + 1], mapped[corner]]
                if depth_scale is not None and variant["hinge_sign"] < 0:
                    triangle.reverse()
                if np.linalg.norm(np.cross(triangle[1] - triangle[0], triangle[2] - triangle[0])) == 0:
                    continue
                points.extend(triangle)
                triangles.append([offset, offset + 1, offset + 2])
                ancestry.append(face_index)
        if not triangles:
            raise FitError(f"fit source {recipe['source_sha256']} part {part_id}: empty fitted ring region")
        result[part_id] = FittedRegion(part_id, points, triangles, ancestry)
    return result


def close_selection(vertices, faces, selected, part_id):
    """Close declared attachment cuts while retaining the indexed source skin."""
    selected = np.asarray(selected, dtype=np.int64)
    triangles = faces[selected]
    edges = np.concatenate([triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]]])
    _, inverse, counts = np.unique(np.sort(edges, axis=1), axis=0, return_inverse=True, return_counts=True)
    boundary = edges[counts[inverse] == 1]
    outgoing = {}
    for a, b in boundary:
        outgoing.setdefault(int(a), []).append(int(b))
    for values in outgoing.values():
        values.sort(reverse=True)
    points, repaired, ancestry = vertices.tolist(), triangles.tolist(), selected.tolist()
    while outgoing:
        start = min(outgoing)
        loop, current = [], start
        while True:
            loop.append(current)
            if current not in outgoing:
                raise FitError(f"separate {part_id}: open attachment boundary")
            following = outgoing[current].pop()
            if not outgoing[current]:
                del outgoing[current]
            current = following
            if current == start:
                break
        if len(loop) < 3:
            raise FitError(f"separate {part_id}: invalid cut loop")
        center = len(points)
        points.append(vertices[loop].mean(axis=0).tolist())
        for a, b in zip(loop, loop[1:] + loop[:1]):
            repaired.append([center, b, a])
            touching = np.flatnonzero(np.any(triangles == a, axis=1) & np.any(triangles == b, axis=1))
            ancestry.append(int(selected[touching[0]]))
    used, remap = np.unique(np.asarray(repaired), return_inverse=True)
    return np.asarray(points)[used], remap.reshape(-1, 3), np.asarray(ancestry)


def _local_fit(vertices, faces, ancestry, target):
    low, high = vertices.min(axis=0), vertices.max(axis=0)
    points = (vertices - (low + high) / 2) / (high - low) * np.asarray(target["size"])
    if target.get("section"):
        # Upper mounts follow the clipped corner outline, not its enclosing
        # box. Register each horizontal source run between that section's
        # actual left/right flanks while preserving its generated relief.
        section = np.asarray(target["section"])
        left = np.full(len(points), np.inf)
        right = np.full(len(points), -np.inf)
        for a, b in zip(section, np.roll(section, -1, axis=0)):
            if a[1] == b[1]:
                continue
            fraction = (points[:, 1] - a[1]) / (b[1] - a[1])
            valid = (fraction >= -1e-6) & (fraction <= 1 + 1e-6)
            x = a[0] + np.clip(fraction, 0, 1) * (b[0] - a[0])
            left[valid] = np.minimum(left[valid], x[valid])
            right[valid] = np.maximum(right[valid], x[valid])
        if not np.isfinite(left).all() or not np.isfinite(right).all():
            raise FitError(f"fit part {target['id']}: section does not span source registration")
        across = points[:, 0] / target["size"][0] + .5
        points[:, 0] = left * (1 - across) + right * across
    basis = np.asarray(target["transform"]["basis"]).T
    placed = np.einsum("ij,kj->ik", points, basis) + target["transform"]["origin"]
    return FittedRegion(target.get("id", target.get("reservation_id")), placed, faces, ancestry)


class FittedFrame:
    def __init__(self, ring, hinges, rivets, interfaces, hardware, depth_scale):
        self.ring, self.hinges, self.rivets = ring, hinges, rivets
        self.interfaces, self.hardware = interfaces, hardware
        self.depth_scale = depth_scale


def clip_source_plane(vertices, faces, selected, axis, plane, direction=1):
    """Retain a source half-space, including each clipped face's ancestry."""
    points, triangles, ancestry = [], [], []
    for index in selected:
        polygon = []
        previous = vertices[faces[index, -1]]
        for current in vertices[faces[index]]:
            before, after = direction * (previous[axis] - plane), direction * (current[axis] - plane)
            if (before < 0) != (after < 0):
                polygon.append(previous + (current - previous) * before / (before - after))
            if after >= 0:
                polygon.append(current)
            previous = current
        for corner in range(1, len(polygon) - 1):
            tri = [polygon[0], polygon[corner], polygon[corner + 1]]
            if np.linalg.norm(np.cross(tri[1] - tri[0], tri[2] - tri[0])) == 0:
                continue
            start = len(points)
            points.extend(tri)
            triangles.append([start, start + 1, start + 2])
            ancestry.append(index)
    points, remap = np.unique(np.round(points, 12), axis=0, return_inverse=True)
    return points, remap[np.asarray(triangles)], np.asarray(ancestry)


def front_relief(vertices, faces, selected, plane):
    """Close the flank-equator cut without reinstating the hidden rear tube."""
    points, triangles, ancestry = clip_source_plane(vertices, faces, selected, 2, plane)
    ancestry = np.asarray(ancestry)
    edges = np.concatenate([triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]]])
    edge_sources = np.tile(ancestry, 3)
    _, inverse, counts = np.unique(np.sort(edges, axis=1), axis=0, return_inverse=True, return_counts=True)
    boundary = counts[inverse] == 1
    outgoing = {int(a): int(b) for a, b in edges[boundary]}
    source_at_edge = {int(a): int(source) for (a, _), source in zip(edges[boundary], edge_sources[boundary])}
    if len(outgoing) != int(boundary.sum()):
        raise FitError("front relief: branched cut boundary")
    loops = []
    while outgoing:
        start = min(outgoing)
        loop, current = [], start
        while True:
            loop.append(current)
            if current not in outgoing:
                raise FitError("front relief: open cut boundary")
            current = outgoing.pop(current)
            if current == start:
                break
        if not np.allclose(points[loop, 2], plane, atol=1e-10, rtol=0):
            raise FitError("front relief: unexpected nonplanar boundary")
        loops.append(loop)
    if len(loops) != 2:
        raise FitError(f"front relief: expected an annular cut, got {len(loops)} loops")
    inner, outer = sorted(loops, key=lambda loop: np.linalg.norm(points[loop, :2], axis=1).mean())
    def ordered(loop):
        angles = np.arctan2(points[loop, 1], points[loop, 0]) % (2 * np.pi)
        order = np.argsort(angles, kind="stable")
        return np.asarray(loop)[order], angles[order]
    inner, inner_angles = ordered(inner)
    outer, outer_angles = ordered(outer)
    cap, cap_sources = [], []
    i = j = 0
    while i < len(outer) or j < len(inner):
        next_outer = outer_angles[(i + 1) % len(outer)] + (2 * np.pi if i + 1 >= len(outer) else 0) if i < len(outer) else np.inf
        next_inner = inner_angles[(j + 1) % len(inner)] + (2 * np.pi if j + 1 >= len(inner) else 0) if j < len(inner) else np.inf
        if next_outer < next_inner:
            triangle = [outer[i % len(outer)], outer[(i + 1) % len(outer)], inner[j % len(inner)]]
            source = source_at_edge[int(outer[i % len(outer)])]
            i += 1
        else:
            triangle = [outer[i % len(outer)], inner[(j + 1) % len(inner)], inner[j % len(inner)]]
            source = source_at_edge[int(inner[j % len(inner)])]
            j += 1
        a, b, c = points[triangle]
        normal = np.cross(b - a, c - a)[2]
        if normal == 0:
            continue
        cap.append(triangle[::-1] if normal > 0 else triangle)
        cap_sources.append(source)
    return points, np.concatenate([triangles, cap]), np.concatenate([ancestry, cap_sources])


def fit_frame(contract, vertices, faces, recipe):
    """Fit one frozen frame source to both exported portal-local variants."""
    reservations = {row["id"] for variant in contract["variants"] for row in variant["frame_solids"] + variant["frame_rivets"]}
    validate_source(vertices, faces, recipe, recipe["source_sha256"], reservations)
    selections = {row["role"]: row for row in recipe["regions"]}
    if set(selections) != {"ring", "rivets", "hinge_mount"}:
        raise FitError("separate frame: ring, rivets and hinge_mount selections are required")
    # The loop landmarks lie on the generated flanks' equator, where the
    # front crown joins the hidden rear tube. Cut here before scaling depth.
    plane = float(np.median(vertices[selections["ring"]["landmarks"]["outer_loop"], 2]))
    closed_v, closed_f, closed_source = close_selection(vertices, faces, selections["ring"]["faces"], "ring")
    ring_v, ring_f, cut_source = front_relief(closed_v, closed_f, np.arange(len(closed_f)), plane)
    ring_source = closed_source[cut_source]
    hinge_v, hinge_f, hinge_source = close_selection(vertices, faces, selections["hinge_mount"]["faces"], "hinge_mount")
    # Use a free barrel run between attachment ears. Compressing the whole
    # plate into a knuckle box puts its barrel off-axis and leaves a seal gap.
    landmarks = selections["hinge_mount"]["landmarks"]
    axis = vertices[landmarks["axis_bottom"] + landmarks["axis_top"]]
    tangent = 2 * float(axis[:, 0].mean()) - float(hinge_v[:, 0].max())
    # The selection separates the raised mount, but its fused attachment below
    # that cut still belongs to the ring. Repair with the source's clean opposite
    # half before relocating the extracted mount to the two exported stations.
    clean_v, clean_f, clean_source = clip_source_plane(
        ring_v, ring_f, np.arange(len(ring_f)), 0, 0, -int(np.sign(axis[:, 0].mean())))
    reflected = clean_v * [-1, 1, 1]
    combined = np.concatenate([clean_v, reflected])
    ring_f = np.concatenate([clean_f, clean_f[:, ::-1] + len(clean_v)])
    ring_source = np.tile(ring_source[clean_source], 2)
    ring_v, remap = np.unique(np.round(combined, 12), axis=0, return_inverse=True)
    ring_f = remap[ring_f]
    plate_v, plate_f, _ = clip_source_plane(vertices, faces, selections["hinge_mount"]["faces"], 0, tangent, -1)
    intervals = sorted(zip(plate_v[plate_f, 1].min(axis=1), plate_v[plate_f, 1].max(axis=1)))
    cursor, end = float(axis[:, 1].min()), float(axis[:, 1].max())
    free_runs = []
    for lo, hi in intervals:
        if hi <= cursor:
            continue
        if lo >= end:
            break
        if lo > cursor:
            free_runs.append((cursor, float(lo)))
        cursor = min(end, max(cursor, float(hi)))
        if cursor >= end:
            break
    if cursor < end:
        free_runs.append((cursor, end))
    if not free_runs:
        raise FitError("hinge barrel: no exposed run between plate attachments")
    barrel_bottom, barrel_top = max(free_runs, key=lambda run: run[1] - run[0])
    barrel_v, barrel_f, barrel_source = clip_source_plane(hinge_v, hinge_f, np.arange(len(hinge_f)), 1, barrel_bottom)
    barrel_v, barrel_f, upper_source = clip_source_plane(barrel_v, barrel_f, np.arange(len(barrel_f)), 1, barrel_top, -1)
    barrel_source = barrel_source[upper_source]
    barrel_v, barrel_f, cap_source = close_selection(barrel_v, barrel_f, np.arange(len(barrel_f)), "hinge_barrel")
    barrel_source = hinge_source[barrel_source[cap_source]]
    # Ear-tangent cuts can leave duplicate points differing below a nanometre
    # in raw units. Weld that arithmetic residue before the millimetre-scale
    # barrel fit turns it into zero-area triangles at portal coordinates.
    barrel_v, remap = np.unique(np.round(barrel_v, 9), axis=0, return_inverse=True)
    barrel_f = remap[barrel_f]
    tri = barrel_v[barrel_f]
    positive = np.linalg.norm(np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]), axis=1) > 0
    barrel_f, barrel_source = barrel_f[positive], barrel_source[positive]
    used, remap = np.unique(barrel_f, return_inverse=True)
    barrel_v, barrel_f = barrel_v[used], remap.reshape(-1, 3)
    rivet_faces = np.asarray(selections["rivets"]["faces"])
    landmark = vertices[selections["rivets"]["landmarks"]["template_centre"][0]]
    centroids = vertices[faces[rivet_faces]].mean(axis=1)
    template = rivet_faces[np.linalg.norm(centroids[:, :2] - landmark[:2], axis=1) < .05]
    rivet_v, rivet_f, rivet_source = close_selection(vertices, faces, template, "rivet_template")
    fitted = []
    for variant in contract["variants"]:
        target_span = np.ptp(np.asarray(variant["fit"]["ring"]["outer"])[:, :2], axis=0)
        source_span = np.ptp(ring_v[:, :2], axis=0)
        in_plane_scale = float(max(target_span / source_span))
        solid = next(row for row in variant["frame_solids"] if row["id"] in variant["fit"]["ring"]["reservation_ids"])
        depth_scale = solid["size"][2] / np.ptp(ring_v[:, 2])
        # Split, without adding caps, at the top of the 1 mm seating land.
        # An original source edge may otherwise span that entire shallow run,
        # so snapping only its existing endpoints cannot form a square seat.
        seat = float(ring_v[:, 2].min()) + .001 / depth_scale
        upper_v, upper_f, upper_source = clip_source_plane(ring_v, ring_f, np.arange(len(ring_f)), 2, seat)
        lower_v, lower_f, lower_source = clip_source_plane(ring_v, ring_f, np.arange(len(ring_f)), 2, seat, -1)
        seat_v = np.concatenate([upper_v, lower_v])
        seat_f = np.concatenate([upper_f, lower_f + len(upper_v)])
        seat_source = ring_source[np.concatenate([upper_source, lower_source])]
        ring_recipe = dict(recipe, regions=[dict(selections["ring"], faces=list(range(len(seat_f))))])
        ring = fit_ring(variant, seat_v, seat_f, ring_recipe, depth_scale)
        for region in ring.values():
            region.source_faces = seat_source[region.source_faces]
        solids = {row["id"]: row for row in variant["frame_solids"]}
        reflection = np.array([-1, 1, -variant["hinge_sign"]])
        hardware = {}
        for name, row in solids.items():
            if not name.startswith("HINGE/"):
                continue
            hv, hf, hs = (barrel_v, barrel_f, barrel_source) if name.startswith("HINGE/KNUCKLE-") else (hinge_v, hinge_f, hinge_source)
            reflected_faces = hf[:, ::-1] if np.prod(reflection) < 0 else hf
            hardware[name] = _local_fit(hv * reflection, reflected_faces, hs, row)
        hinges = [hardware[row["reservation_id"]] for row in variant["fit"]["hinge_stations"]]
        rivets = []
        for row in variant["frame_rivets"]:
            points = rivet_v[:, [0, 2, 1]].copy()
            triangles = rivet_f[:, [0, 2, 1]]
            if row["side"] == 0:
                points[:, 1] *= -1
                triangles = triangles[:, ::-1]
            rivets.append(_local_fit(points, triangles, rivet_source, row))
        interfaces = fit_interfaces(variant)
        result = FittedFrame(ring, hinges, rivets, interfaces, hardware, depth_scale)
        result.source_relief_plane = plane
        result.depth_scale_ratio = depth_scale / in_plane_scale
        measurements = validate_fit(result, variant)
        if measurements.seal_misses:
            raise FitError(f"interfaces: {measurements.seal_misses} closed-aperture ray misses")
        fitted.append(result)
    return fitted


def _triangles(polygons):
    return np.asarray([[face[0], face[i], face[i + 1]] for face in polygons for i in range(1, len(face) - 1)], dtype=np.int64)


def rendered_solid(variant, solid):
    """Trim presentation inside the unchanged reservation, exempting the floor."""
    if not solid["id"].startswith("FRAME/"):
        return solid
    into = variant["hinge_sign"]
    rings = [s for s in variant["frame_solids"] if "/RING/" in s["id"]]
    front = min(s["transform"]["origin"][2] - s["size"][2] / 2 for s in rings) if into > 0 else max(s["transform"]["origin"][2] + s["size"][2] / 2 for s in rings)
    points = np.array(solid["vertices"])
    world = points @ np.array(solid["transform"]["basis"]) + solid["transform"]["origin"]
    world[:, 2] = np.maximum(world[:, 2], front) if into > 0 else np.minimum(world[:, 2], front)
    local = (world - solid["transform"]["origin"]) @ np.array(solid["transform"]["basis"]).T
    return dict(solid, vertices=local.tolist())


def fit_interfaces(variant):
    """Construct only exported square sealing interfaces, in portal space."""
    required = set(variant["fit"]["required_seal_ids"])
    result = {}
    for solid in variant["frame_solids"]:
        if solid["id"] not in required:
            continue
        visual = rendered_solid(variant, solid)
        points = np.einsum("ij,jk->ik", np.asarray(visual["vertices"]), np.asarray(solid["transform"]["basis"])) + solid["transform"]["origin"]
        triangles = _triangles(solid["faces"])
        result[solid["id"]] = FittedRegion(solid["id"], points, triangles, np.full(len(triangles), -1))
    for group in variant["groups"]:
        for part in group["parts"]:
            if part["id"] not in required:
                continue
            if part["shape"] != "box":
                raise FitError(f"interface {part['id']}: expected exported square seal")
            points = np.asarray([[x, y, z] for z in [-.5, .5] for y in [-.5, .5] for x in [-.5, .5]]) * part["size"]
            for pose in (part["transform"], group["transform"], variant["hinge_transform"]):
                points = np.einsum("ij,jk->ik", points, np.asarray(pose["basis"])) + pose["origin"]
            polygons = [[0, 2, 3, 1], [4, 5, 7, 6], [0, 1, 5, 4], [2, 6, 7, 3], [0, 4, 6, 2], [1, 3, 7, 5]]
            triangles = _triangles(polygons)
            result[part["id"]] = FittedRegion(part["id"], points, triangles, np.full(len(triangles), -1))
    if set(result) != required:
        raise FitError("interfaces: missing required sealing region")
    return result


def measure_rivet_relief(frame, variant):
    """Ray-sample the actual surrounding band at each exported fastener axis."""
    triangles = np.concatenate([r.vertices[r.faces] for r in frame.ring.values()])
    a, b = triangles[:, 1, :2] - triangles[:, 0, :2], triangles[:, 2, :2] - triangles[:, 0, :2]
    area = a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]
    valid = abs(area) > 1e-12
    triangles, a, b, area = triangles[valid], a[valid], b[valid], area[valid]
    heights = []
    for row, rivet in zip(variant["frame_rivets"], frame.rivets):
        offset = np.asarray(row["transform"]["origin"][:2]) - triangles[:, 0, :2]
        u = (offset[:, 0] * b[:, 1] - offset[:, 1] * b[:, 0]) / area
        v = (a[:, 0] * offset[:, 1] - a[:, 1] * offset[:, 0]) / area
        inside = (u >= -1e-7) & (v >= -1e-7) & (u + v <= 1 + 1e-7)
        if not inside.any():
            raise FitError(f"rivet {row['id']}: no band under head")
        depths = triangles[:, 0, 2] + u * (triangles[:, 1, 2] - triangles[:, 0, 2]) + v * (triangles[:, 2, 2] - triangles[:, 0, 2])
        outward = -1 if row["side"] == 0 else 1
        heights.append(float((rivet.vertices[:, 2] * outward).max() - (depths[inside] * outward).max()))
    return heights


def measure_bead_profile(frame, variant):
    points = np.concatenate([r.vertices for r in frame.ring.values()])
    normals = np.concatenate([r.normals for r in frame.ring.values()])
    return dict(depth_levels=len(np.unique(np.round(points[:, 2], 6))),
                flank_normal_levels=len(np.unique(np.round(abs(normals[:, 2]), 2))),
                crown_rise_m=float(np.ptp(points[:, 2])))


def measure_interface_excess(frame, variant):
    ring = np.concatenate([r.vertices for r in frame.ring.values()])
    into = variant["hinge_sign"]
    front = (ring[:, 2] * into).min()
    values = []
    for name, region in frame.interfaces.items():
        if name.startswith("FRAME/"):
            values.append(float((front - into * region.vertices[:, 2]).max()))
    return max(values)


class FitMeasurements:
    def __init__(self, seal_misses):
        self.seal_misses = seal_misses


def validate_fit(frame, variant):
    for solid in variant["frame_solids"]:
        if solid["id"] not in frame.ring:
            continue
        local = np.einsum("ij,jk->ik", frame.ring[solid["id"]].vertices - solid["transform"]["origin"], np.asarray(solid["transform"]["basis"]))
        excess = np.abs(local) - np.asarray(solid["size"]) / 2
        if excess.max() > .001:
            raise FitError(f"fit part {solid['id']}: reservation exceeded by {excess.max():.9f} m")
    if set(frame.interfaces) != set(variant["fit"]["required_seal_ids"]):
        raise FitError("interfaces: missing required sealing region")
    triangles = np.concatenate([region.vertices[region.faces] for region in frame.interfaces.values()])
    a = triangles[:, 1, :2] - triangles[:, 0, :2]
    b = triangles[:, 2, :2] - triangles[:, 0, :2]
    area = a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]
    usable = abs(area) > 1e-12
    triangles, a, b, area = triangles[usable], a[usable], b[usable], area[usable]
    misses = 0
    for x in np.linspace(-variant["leaf_aperture"][0] / 2 + .001, variant["leaf_aperture"][0] / 2 - .001, 21):
        for y in np.linspace(.081, variant["aperture"][1] - .001, 47):
            offset = [x, y] - triangles[:, 0, :2]
            u = (offset[:, 0] * b[:, 1] - offset[:, 1] * b[:, 0]) / area
            v = (a[:, 0] * offset[:, 1] - a[:, 1] * offset[:, 0]) / area
            inside = (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9)
            for side in [-1, 1]:
                if not (inside & (area * side > 0)).any():
                    misses += 1
    return FitMeasurements(misses)
