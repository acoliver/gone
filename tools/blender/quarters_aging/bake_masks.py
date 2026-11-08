"""Bake one rigid prop's geometry masks in Blender's native Z-up frame.

Blender --background --factory-startup --python-exit-code 1 --python
 tools/blender/quarters_aging/bake_masks.py -- --blend source.blend
 --objects Door Carcass --output assets/props/quarters/locker --seed 9501
 --fields tmp/mat/locker/geometry.npz
 --export assets/props/quarters/storage_locker_module.glb

Object names may identify meshes or roots. Nothing outside those roots is exported.
The source is saved only with --save-source. Live modifiers are rejected: bake the
fitted source first, so atlas coordinates and exported geometry cannot disagree.
"""
import argparse
import importlib.util
import json
import math
from pathlib import Path
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/quarters_aging"))
from finish_fields import gravity_runs

SPEC = importlib.util.spec_from_file_location("hatch_bake", ROOT / "tools/blender/hatch_bake.py")
hatch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(hatch)


def selected_parts(names):
    found = set()
    def visit(obj):
        found.add(obj)
        for child in obj.children:
            visit(child)
    for name in names:
        visit(bpy.data.objects[name])
    return sorted(found, key=lambda obj: obj.name)


def planar_atlas(objects, resolution):
    """Isometric face islands, then one shared pack at an unchanged relative scale.

    Unlike independent smart projections, planar face islands preserve physical
    area exactly, including the small bevels. No minimum-footprint enlargement
    changes the texel density. Margins are reserved by Blender's island packer.
    """
    for obj in objects:
        if obj.modifiers:
            raise ValueError(f"apply modifiers before baking: {obj.name}")
        # Rounded corner quads need not be planar. Unfold their constituent
        # triangles rather than projecting away physical area.
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        nonplanar = [face for face in bm.faces if len(face.verts) > 3 and
                     max(abs((v.co - face.verts[0].co).dot(face.normal)) for v in face.verts) > 1e-7]
        bmesh.ops.triangulate(bm, faces=nonplanar)
        bm.to_mesh(obj.data)
        bm.free()
        if not obj.data.uv_layers:
            obj.data.uv_layers.new(name="UVMap")
        uv = obj.data.uv_layers.active.data
        for polygon in obj.data.polygons:
            points = np.array([obj.matrix_world @ obj.data.vertices[i].co for i in polygon.vertices])
            normal = np.cross(points[1] - points[0], points[2] - points[0])
            normal /= np.linalg.norm(normal)
            tangent = points[1] - points[0]
            tangent /= np.linalg.norm(tangent)
            local = (points - points[0]) @ np.stack([tangent, np.cross(normal, tangent)], axis=1)
            for index, point in zip(polygon.loop_indices, local + polygon.index * 4 / resolution):
                uv[index].uv = point
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(rotate=True, scale=True, margin_method="FRACTION", margin=3 / resolution)
    bpy.ops.object.mode_set(mode="OBJECT")


def geometry(obj):
    mesh = obj.data
    mesh.calc_loop_triangles()
    points = np.array([obj.matrix_world @ v.co for v in mesh.vertices], dtype=np.float64)
    triangles = [list(tri.vertices) for tri in mesh.loop_triangles]
    return points, triangles


def edge_segments(obj, points):
    adjacent = {}
    normals = []
    for face in obj.data.polygons:
        normal = obj.matrix_world.to_3x3().inverted().transposed() @ face.normal
        normals.append(np.array(normal.normalized()))
        for pair in face.edge_keys:
            adjacent.setdefault(tuple(sorted(pair)), []).append(face.index)
    return [(points[a], points[b]) for (a, b), faces in adjacent.items()
            if len(faces) != 2 or np.dot(normals[faces[0]], normals[faces[1]]) < math.cos(math.radians(12))]


def connected_sources(obj, points):
    """Find individual rivets/hinges even when they share one named object."""
    groups = []
    remaining = set(range(len(points)))
    adjacent = [set() for _ in points]
    for edge in obj.data.edges:
        a, b = edge.vertices
        adjacent[a].add(b)
        adjacent[b].add(a)
    while remaining:
        stack, component = [min(remaining)], set()
        while stack:
            i = stack.pop()
            if i in component:
                continue
            component.add(i)
            stack.extend(adjacent[i] - component)
        remaining -= component
        part = points[sorted(component)]
        lo, hi = part.min(0), part.max(0)
        groups.append((lo, hi))
    return groups


def rasterize(objects, resolution):
    size = (resolution, resolution)
    position = np.zeros((*size, 3), np.float32)
    normal = np.zeros_like(position)
    edge_mask = np.zeros(size, np.float32)
    contact = np.zeros(size, np.float32)
    ownership = np.zeros(size, np.uint8)
    occupied = np.zeros(size, bool)
    face_owner = np.full(size, -1, np.int32)
    sources, densities = [], []
    geos = {obj: geometry(obj) for obj in objects}
    for object_index, obj in enumerate(objects):
        points, triangles = geos[obj]
        edges = edge_segments(obj, points)
        other_points, other_triangles = [], []
        for other, (vertices, faces) in geos.items():
            if other == obj:
                continue
            offset = len(other_points)
            other_points.extend(vertices)
            other_triangles.extend([[i + offset for i in face] for face in faces])
        tree = BVHTree.FromPolygons(other_points, other_triangles, all_triangles=True) if other_points else None
        # Contact is sampled on the actual surface, not inferred from its name.
        uv = obj.data.uv_layers.active.data
        for tri in obj.data.loop_triangles:
            p = points[list(tri.vertices)]
            tex = np.array([uv[i].uv[:] for i in tri.loops]) * resolution
            if np.any(tex < 0) or np.any(tex > resolution):
                raise ValueError(f"UV outside atlas: {obj.name}/{tri.index}")
            tex[:, 1] = resolution - tex[:, 1]
            denominator = np.cross(tex[1] - tex[0], tex[2] - tex[0]).item()
            if abs(denominator) < 1e-10:
                raise ValueError(f"collapsed triangle in atlas: {obj.name}/{tri.index}")
            area = np.linalg.norm(np.cross(p[1] - p[0], p[2] - p[0]))
            densities.append(math.sqrt(abs(denominator) / area))
            lo = np.maximum(np.floor(tex.min(0)).astype(int), 0)
            hi = np.minimum(np.ceil(tex.max(0)).astype(int), resolution - 1)
            yy, xx = np.mgrid[lo[1]:hi[1] + 1, lo[0]:hi[0] + 1]
            q = np.stack([xx + .5, yy + .5], axis=-1)
            a = np.cross(q - tex[0], tex[2] - tex[0]) / denominator
            b = np.cross(tex[1] - tex[0], q - tex[0]) / denominator
            inside = (a >= 0) & (b >= 0) & (a + b <= 1)
            x, y = xx[inside], yy[inside]
            wa, wb = a[inside], b[inside]
            if not len(x):
                # Hatch's conservative bake also reserves a sample for a bevel
                # narrower than a pixel; delivered UVs keep their physical scale.
                centre = np.floor(tex.mean(0)).astype(int)
                x, y = np.array([centre[0]]), np.array([centre[1]])
                wa, wb = np.array([1 / 3]), np.array([1 / 3])
            owner = object_index * 100000 + tri.polygon_index
            overlap = occupied[y, x] & (face_owner[y, x] != owner)
            if np.any(overlap):
                raise ValueError(f"overlapping UV triangle interiors: {obj.name}/{tri.index}, face {tri.polygon_index}, previous {np.unique(face_owner[y[overlap], x[overlap]])}, count {overlap.sum()}, UV {tex.tolist()}")
            face_owner[y, x] = owner
            positions = p[0] + wa[:, None] * (p[1] - p[0]) + wb[:, None] * (p[2] - p[0])
            n = np.cross(p[1] - p[0], p[2] - p[0])
            n /= np.linalg.norm(n)
            n *= np.sign(obj.matrix_world.determinant())
            position[y, x] = positions
            normal[y, x] = n
            occupied[y, x] = True
            mat = obj.data.materials[obj.data.polygons[tri.polygon_index].material_index].name
            ownership[y, x] = {"PaintedSteel": 1, "BareSteel": 2, "DarkSteel": 3}.get(mat, 4)
            distance = np.full(len(x), 1.0)
            for start, end in edges:
                if np.any(np.maximum(start, end) < positions.min(0) - .15) or np.any(np.minimum(start, end) > positions.max(0) + .15):
                    continue
                segment = end - start
                t = np.clip(np.sum((positions - start) * segment, axis=1) / np.sum(segment * segment), 0, 1)
                distance = np.minimum(distance, np.linalg.norm(positions - (start + t[:, None] * segment), axis=1))
            edge_mask[y, x] = np.exp(-distance / .012)
            if tree is not None:
                distances = np.array([tree.find_nearest(Vector(point), .025)[3] for point in positions], dtype=object)
                contact[y, x] = [math.exp(-float(d) / .005) if d is not None else 0 for d in distances]
        if any(token in obj.name.lower() for token in ("rivet", "hinge", "handle", "vent")):
            for lo, hi in connected_sources(obj, points):
                centre = (lo + hi) / 2
                centre[2] = lo[2]
                outlets = [centre]
                if "vent" in obj.name.lower():
                    outlets = [np.array([x, centre[1], lo[2]]) for x in np.linspace(lo[0] + .015, hi[0] - .015, 3)]
                for outlet in outlets:
                    sources.append({"part": obj.name, "position_blender": outlet.tolist(),
                                    "width_m": .0075, "length_m": .15,
                                    "bounds_blender": [lo.tolist(), hi.tolist()]})
        print("RASTER", obj.name, "texels", int(occupied.sum()), flush=True)
    densities = np.asarray(densities)
    if np.ptp(densities) / np.median(densities) > .015:
        raise ValueError(f"inconsistent texel density: {densities.min()} to {densities.max()}")
    return position, normal, edge_mask, contact, ownership, occupied, sources, densities, np.where(occupied, face_owner // 100000, -1).astype(np.int16)


def save_rgba(name, data, output):
    if not np.isfinite(data).all():
        raise ValueError(f"nonfinite mask field: {name}")
    resolution = data.shape[0]
    image = bpy.data.images.new(name, resolution, resolution, alpha=True)
    image.colorspace_settings.name = "Non-Color"
    image.pixels.foreach_set(np.flipud(np.clip(data, 0, 1)).astype(np.float32).ravel())
    hatch.save_image(image, output / (name + ".png"))
    bpy.data.images.remove(image)


def bake_ao(objects, resolution, seed):
    visibility = {obj: (obj.hide_render, obj.hide_get()) for obj in bpy.context.scene.objects}
    for obj in visibility:
        if obj not in objects:
            obj.hide_render = True
    joined = hatch.bake_mesh(objects)
    hatch.bake_footprints(joined, resolution)
    mat = bpy.data.materials.new("QuartersMaskBake")
    mat.use_nodes = True
    joined.data.materials.clear()
    joined.data.materials.append(mat)
    for face in joined.data.polygons:
        face.material_index = 0
    image = hatch.new_image("QuartersAO", resolution)
    target = mat.node_tree.nodes.new("ShaderNodeTexImage")
    target.image = image
    mat.node_tree.nodes.active = target
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 16
    scene.cycles.seed = seed
    scene.cycles.use_animated_seed = False
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 8
    scene.render.bake.margin = 3
    bpy.ops.object.select_all(action="DESELECT")
    joined.select_set(True)
    bpy.context.view_layer.objects.active = joined
    bpy.ops.object.bake(type="AO", uv_layer="BakeCoverage")
    pixels = np.empty(resolution * resolution * 4, np.float32)
    image.pixels.foreach_get(pixels)
    ao = np.flipud(pixels.reshape(resolution, resolution, 4)[:, :, 0]).copy()
    bpy.data.objects.remove(joined, do_unlink=True)
    for obj, (render_hidden, viewport_hidden) in visibility.items():
        obj.hide_render = render_hidden
        obj.hide_set(viewport_hidden)
    bpy.data.images.remove(image)
    return ao


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blend", type=Path, required=True)
    parser.add_argument("--objects", nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--resolution", type=int, default=2048)
    parser.add_argument("--export", type=Path, required=True)
    parser.add_argument("--fields", type=Path, required=True, help="scratch path for authoring geometry NPZ")
    parser.add_argument("--save-source", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    bpy.ops.wm.open_mainfile(filepath=str(args.blend.resolve()))
    parts = selected_parts(args.objects)
    objects = [obj for obj in parts if obj.type == "MESH"]
    args.output.mkdir(parents=True, exist_ok=True)
    planar_atlas(objects, args.resolution)
    positions, normals, edge, contact, ownership, occupied, sources, density, part_index = rasterize(objects, args.resolution)
    ao = bake_ao(objects, args.resolution, args.seed)
    streak = np.zeros_like(edge)
    p, n = positions[occupied], normals[occupied]
    streak[occupied] = gravity_runs(p, n, sources, args.seed)
    cavity = np.clip((1 - ao) * 1.6, 0, 1)
    exposure = np.clip(normals[:, :, 2], 0, 1) * ao
    save_rgba("geometry_masks", np.stack([ao, cavity, edge, occupied], -1), args.output)
    save_rgba("weather_masks", np.stack([exposure, streak, contact, ownership / 4], -1), args.output)
    # Geometry fields remain authoring inputs, not runtime allocations.
    args.fields.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.fields, position=positions, normal=normals,
                        ownership=ownership, occupied=occupied, part_index=part_index,
                        part_names=np.array([obj.name for obj in objects]))
    document = {"version": 1, "seed": args.seed, "atlas_size": [args.resolution] * 2,
                "texels_per_metre": float(np.median(density)),
                "density_range_px_m": [float(density.min()), float(density.max())],
                "uv_overlap_texels": 0, "uv_method": "isometric planar face islands, shared pack, 3 px margin",
                "occupied_texels": int(occupied.sum()), "ao_method": "Cycles geometry AO, 16 samples, CPU",
                "channels": {"geometry_masks.png": {"R": "ambient occlusion (1 = open)", "G": "cavity (1 = recessed)", "B": "edge curvature proximity (12 mm falloff)", "A": "surface coverage"},
                             "weather_masks.png": {"R": "up-facing exposure times AO", "G": "gravity streak field", "B": "contact with other parts (5 mm falloff, 25 mm search)", "A": "material class / 4: PaintedSteel=1, BareSteel=2, DarkSteel=3, other=4"}},
                "parts": [obj.name for obj in parts], "sources": sources}
    (args.output / "masks.json").write_text(json.dumps(document, indent=2) + "\n")
    if args.save_source:
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(args.blend.resolve()))
    bpy.ops.object.select_all(action="DESELECT")
    for obj in parts:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(filepath=str(args.export.resolve()), export_format="GLB", use_selection=True,
                              export_yup=True, export_apply=False, export_materials="EXPORT",
                              export_cameras=False, export_lights=False)
    print("MASKS", document["atlas_size"], document["texels_per_metre"], "px/m", flush=True)


if __name__ == "__main__":
    main()
