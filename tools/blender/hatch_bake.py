"""Offline UV projection, shared baking, coverage and export material helpers."""
import hashlib
import importlib.util
import math
from pathlib import Path
import bpy
from bpy_extras.mesh_utils import mesh_linked_uv_islands
import numpy as np
from mathutils import Matrix

C = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
CINV = C.inverted()


def painted_coordinates(objects, nodes, document):
    frame_bounds = {}
    for variant in document["variants"]:
        points = [CINV @ (obj.matrix_world @ vertex.co).to_4d()
                  for obj in objects if nodes[obj.name]["kind"] == "frame"
                  and nodes[obj.name]["variant"] == variant["index"] for vertex in obj.data.vertices]
        frame_bounds[variant["index"]] = (min(p.x for p in points), max(p.x for p in points),
                                           min(p.y for p in points), max(p.y for p in points))
    plates = {(nodes[obj.name]["variant"], nodes[obj.name]["side"]): obj for obj in objects
              if nodes[obj.name]["kind"] == "leaf" and nodes[obj.name]["id"].endswith("Steel/plate")}
    for obj in objects:
        row = nodes[obj.name]
        backing = row["kind"] == "leaf" and row["id"].startswith("BackingLap")
        leaf = row["kind"] == "leaf" and (row["id"].endswith("Steel/plate") or backing)
        frame = row["kind"] == "frame"
        side = (1 if document["variants"][row["variant"]]["hinge_sign"] > 0 else 0) if backing else row["side"]
        projection = plates[(row["variant"], side)] if leaf else obj
        projection_row = nodes[projection.name]
        relative = projection.matrix_world.inverted() @ obj.matrix_world
        colour = obj.data.color_attributes.new(name="PaintOwnership", type="BYTE_COLOR", domain="CORNER")
        uv = obj.data.uv_layers.new(name="PaintProjection")
        if leaf:
            part = document["variants"][row["variant"]]["groups"][projection_row["group"]]["parts"][projection_row["part"]]
        for polygon in obj.data.polygons:
            normal = polygon.normal if leaf else obj.matrix_world.to_3x3().inverted().transposed() @ polygon.normal
            normal = CINV.to_3x3() @ normal
            axis = max(range(3), key=lambda i: abs(normal[i]))
            for index in polygon.loop_indices:
                loop = obj.data.loops[index]
                # The solid slab's edge is machined steel; only its broad caps carry paint.
                colour.data[index].color = (float(leaf and axis == 2), float(side), float(frame), 1)
                if not (leaf or frame):
                    continue
                point = obj.data.vertices[loop.vertex_index].co
                # The backing covers the reverse slab. Project in that slab's
                # frame so its visible cap shares the full mirrored paint image.
                point = CINV @ ((relative @ point).to_4d() if leaf else (obj.matrix_world @ point).to_4d())
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


def _project_edge_on_triangles(obj, resolution):
    uv = obj.data.uv_layers.active.data
    for polygon in obj.data.polygons:
        indices = list(polygon.loop_indices)
        values = np.array([uv[i].uv[:] for i in indices])
        determinant = abs(np.linalg.det((values[1:] - values[0]).T))
        edges = np.roll(values, -1, axis=0) - values
        longest_squared = np.max(np.sum(edges * edges, axis=1))
        points = np.array([obj.data.vertices[obj.data.loops[i].vertex_index].co[:] for i in indices])
        geometry_edges = np.roll(points, -1, axis=0) - points
        geometry_area = np.linalg.norm(np.cross(geometry_edges[0], geometry_edges[1]))
        geometry_quality = geometry_area / np.max(np.sum(geometry_edges * geometry_edges, axis=1))
        # Compare with the triangle's intrinsic aspect ratio: a thin source
        # triangle is valid, but an edge-on projection loses additional area.
        if determinant > 1e-12 and determinant > longest_squared * geometry_quality * math.sqrt(np.finfo(np.float32).eps):
            continue
        edges = geometry_edges
        tangent = edges[np.argmax(np.linalg.norm(edges, axis=1))]
        tangent /= np.linalg.norm(tangent)
        normal = np.cross(edges[0], edges[1])
        normal /= np.linalg.norm(normal)
        projected = (points - points.mean(axis=0)) @ np.stack((tangent, np.cross(normal, tangent)), axis=1)
        projected *= np.maximum(1, 2 / resolution / np.ptp(projected, axis=0))
        # Separate islands without large integer offsets that erase texel-
        # sized differences when Blender stores the coordinates as float32.
        for i, point in zip(indices, projected + 10 + polygon.index * 4 / resolution):
            uv[i].uv = point


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
    # Use smart projection's island grouping, but project original geometry in
    # float64 before imposing the minimum footprint. Tiny reservation cuts can
    # already have identical float32 UVs in smart_project's output.
    for obj in objects:
        uv = obj.data.uv_layers.active.data
        for island in mesh_linked_uv_islands(obj.data):
            indices = [i for face in island for i in obj.data.polygons[face].loop_indices]
            points = np.array([obj.data.vertices[obj.data.loops[i].vertex_index].co[:] for i in indices], dtype=np.float64)
            origin = points.mean(axis=0)
            normals = [np.cross(points[j + 1] - points[j], points[j + 2] - points[j])
                       for j in range(0, len(points), 3)]
            normal = max(normals, key=np.linalg.norm)
            length = np.linalg.norm(normal)
            if length == 0:
                raise ValueError(f"zero-area UV island: {obj.name}")
            normal /= length
            axis = np.eye(3)[abs(normal).argmin()]
            tangent = np.cross(normal, axis)
            tangent /= np.linalg.norm(tangent)
            delta = points - origin
            bitangent = np.cross(normal, tangent)
            points = np.column_stack(((delta * tangent).sum(axis=1), (delta * bitangent).sum(axis=1)))
            if not np.isfinite(points).all():
                raise ValueError(f"nonfinite geometric UV projection: {obj.name}")
            _, axes = np.linalg.eigh(np.cov(points.T))
            projected = points @ axes
            span = np.ptp(projected, axis=0)
            if min(span) <= 0:
                raise ValueError(f"collapsed UV island: {obj.name}")
            scale = np.maximum(1, 2 / resolution / span)
            for i, point in zip(indices, (projected * scale) @ axes.T):
                uv[i].uv = point
        _project_edge_on_triangles(obj, resolution)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.uv.pack_islands(rotate=True, scale=True, margin=2 / resolution)
    bpy.ops.object.mode_set(mode="OBJECT")
    # Packing rescales the minimum footprints along with everything else.
    # Reserve area, restore each island's final texel width, then repack at
    # fixed scale. This keeps narrow contour strips sampleable after packing.
    for obj in objects:
        # The first pack rescales into float32 UVs. Reproject triangles whose
        # small area vanished there before restoring final island footprints.
        _project_edge_on_triangles(obj, resolution)
        uv = obj.data.uv_layers.active.data
        for island in mesh_linked_uv_islands(obj.data):
            indices = [i for face in island for i in obj.data.polygons[face].loop_indices]
            points = np.array([uv[i].uv[:] for i in indices], dtype=np.float64) * .85
            centre = points.mean(axis=0)
            _, axes = np.linalg.eigh(np.cov(points.T))
            local = (points - centre) @ axes
            local *= np.maximum(1, 1.25 / resolution / np.ptp(local, axis=0))
            for i, point in zip(indices, local @ axes.T + centre):
                uv[i].uv = point
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.uv.pack_islands(rotate=False, scale=False, margin=2 / resolution)
    bpy.ops.object.mode_set(mode="OBJECT")
    print("ATLAS unwrapped", len(objects), "objects", flush=True)


def validate_mesh_attributes(objects, nodes, resolution):
    for obj in objects:
        mesh = obj.data
        mesh.calc_tangents()
        for loop in mesh.loops:
            if abs(loop.tangent.length - 1) > 1e-4:
                raise ValueError(f"invalid delivered tangent: {obj.name} loop {loop.index}")
        if nodes[obj.name]["kind"] == "frame":
            for face in mesh.polygons:
                a, b, c = [mesh.vertices[i].co for i in face.vertices]
                normal = (b - a).cross(c - a)
                if normal.length <= 1e-12:
                    raise ValueError(f"degenerate fixed triangle: {obj.name} face {face.index}")
                normal.normalize()
                if any(normal.dot(mesh.corner_normals[i].vector) <= .999999 for i in face.loop_indices):
                    raise ValueError(f"nonflat fixed normal: {obj.name} face {face.index}")
        uv = mesh.uv_layers.active.data
        for island in mesh_linked_uv_islands(mesh):
            points = np.array([uv[i].uv[:] for face in island for i in mesh.polygons[face].loop_indices])
            _, axes = np.linalg.eigh(np.cov(points.T))
            if np.ptp(points @ axes, axis=0).min() * resolution < 1:
                raise ValueError(f"subtexel delivered UV island: {obj.name}")
    print("MESH_ATTRIBUTES unit_tangents flat_fixed_normals minimum_one_texel_islands PASS", flush=True)


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
