"""Verify exported issue-110 hardware geometry and produce fixed CPU proof captures.

Run with the local Hunyuan environment's Python, not Blender's embedded Python.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
ASSET = ROOT / "assets/props/stasis-wiring"
EVIDENCE = ROOT / "tmp/verify-stasis-wiring/hardware-fit"
GLB = ASSET / "stasis-wiring-enclosure.glb"
BLEND = ASSET / "stasis-wiring-enclosure.blend"
BUILD = ROOT / "tools/blender/stasis_wiring_hardware.py"
REFERENCE = ROOT / "art-source/stasis-wiring/sealed-harness-enclosure-reference.png"
BLENDER = Path("/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender")
WEIGHTS = Path("/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv/hunyuan3d-dit-v2-mv/model.fp16.safetensors")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def ray_intersections(triangles: np.ndarray, origin: np.ndarray, direction: np.ndarray):
    """Return face IDs and distances so failed clearance checks identify the solid."""
    v0, v1, v2 = triangles[:, 0], triangles[:, 1], triangles[:, 2]
    edge1, edge2 = v1 - v0, v2 - v0
    h = np.cross(np.broadcast_to(direction, edge2.shape), edge2)
    a = np.einsum("ij,ij->i", edge1, h)
    mask = np.abs(a) > 1e-10
    f = np.zeros_like(a)
    f[mask] = 1.0 / a[mask]
    s = origin - v0
    u = f * np.einsum("ij,ij->i", s, h)
    q = np.cross(s, edge1)
    v = f * np.einsum("ij,ij->i", np.broadcast_to(direction, q.shape), q)
    t = f * np.einsum("ij,ij->i", edge2, q)
    valid = mask & (u >= -1e-7) & (v >= -1e-7) & (u + v <= 1 + 1e-7) & (t >= 0)
    indices = np.flatnonzero(valid)
    order = np.argsort(t[indices])
    return indices[order], t[indices][order]


def ray_hits(triangles: np.ndarray, origin: np.ndarray, direction: np.ndarray) -> np.ndarray:
    return ray_intersections(triangles, origin, direction)[1]


def test_geometry():
    sockets_doc = json.loads((ASSET / "sockets.json").read_text())
    sockets = sockets_doc["sockets"]
    assert sockets_doc["units"] == "metres"
    assert len(sockets) == 3
    assert [s["class"] for s in sockets] == ["power", "power", "control-data"]
    assert all(s["axis_local"] == [0, 0, 1] for s in sockets)
    assert all(abs(s["gland_outer_diameter_m"] - d) < 1e-9
               for s, d in zip(sockets, (.034, .034, .028)))

    scene = trimesh.load(GLB, force="scene")
    world_meshes, face_owners, part_metrics = [], [], {}
    for node in scene.graph.nodes_geometry:
        transform, geometry = scene.graph[node]
        part = scene.geometry[geometry].copy()
        part.apply_transform(transform)
        normals = part.vertex_normals
        normal_length_error = float(np.max(np.abs(np.linalg.norm(normals, axis=1) - 1)))
        normal_alignment = float(np.min(np.einsum("ijk,ik->ij", normals[part.faces], part.face_normals)))
        assert normal_length_error < 3e-5, node
        assert normal_alignment > 0, (node, normal_alignment)
        # Render vertices split at normal/UV seams. Topology is measured on
        # position-welded vertices without dropping or repairing any faces.
        face_owners.extend((node, part.visual.material.name, index) for index in range(len(part.faces)))
        part.merge_vertices(merge_tex=True, merge_norm=True)
        counts = np.bincount(part.edges_unique_inverse)
        topology = {"watertight": bool(part.is_watertight),
                    "winding_consistent": bool(part.is_winding_consistent),
                    "boundary_edges": int(np.count_nonzero(counts == 1)),
                    "nonmanifold_edges": int(np.count_nonzero(counts > 2)),
                    "degenerate_faces": int(np.count_nonzero(part.area_faces < 1e-12)),
                    "components": len(part.split(only_watertight=False)),
                    "volume_m3": float(part.volume), "triangles": len(part.faces),
                    "minimum_corner_normal_dot_face_normal": normal_alignment,
                    "max_unit_normal_length_error": normal_length_error}
        assert topology["watertight"] and topology["winding_consistent"], (node, topology)
        assert topology["components"] == 1 and topology["volume_m3"] > 0, (node, topology)
        assert topology["degenerate_faces"] == 0, (node, topology)
        part_metrics[node] = topology
        world_meshes.append(part)
    mesh = trimesh.util.concatenate(world_meshes)
    bounds = mesh.bounds
    extents = mesh.extents
    triangles = mesh.triangles
    assert 20000 <= len(triangles) <= 35000, f"triangle budget: {len(triangles)}"
    assert np.all(extents > np.array([.27, .17, .18])) and np.all(extents < np.array([.33, .23, .25])), extents
    assert bounds[0, 2] <= -.065 and bounds[1, 2] >= .119, bounds
    # Exported glTF is +Y-up; each prescribed connector opening is a real unobstructed axial path.
    clear_rays = 0
    edge_hits = 0
    gland_gaps = {}
    packing = {}
    direction = np.array([0., 0., -1.])
    def assert_clear(origin, label):
        faces, distances = ray_intersections(triangles, np.asarray(origin), direction)
        obstructions = [{"node": face_owners[face][0], "material": face_owners[face][1],
                         "face_id": face_owners[face][2], "distance_m": float(distance),
                         "hit_m": (origin + distance * direction).tolist(),
                         "triangle_m": triangles[face].tolist()}
                        for face, distance in zip(faces, distances)]
        if obstructions:
            EVIDENCE.mkdir(parents=True, exist_ok=True)
            (EVIDENCE / "failed-ray.json").write_text(json.dumps({"ray": label, "obstructions": obstructions}, indent=2))
        assert not obstructions, (label, obstructions)
    for socket in sockets:
        x, y, _ = socket["center_local_m"]
        bundle_diameter = socket.get("bundle_outer_diameter_m", socket.get("cable_outer_diameter_m"))
        cable_r = bundle_diameter / 2
        bore_r = socket["bore_diameter_m"] / 2
        assert_clear(np.array([x, y, .15]), socket["id"] + " axis")
        clear_rays += 1
        for radius, samples, label in ((cable_r * .9, 8, "original jacket"),
                                       (cable_r, 64, "full jacket"),
                                       (bore_r - .0000005, 64, "bore clearance")):
            for angle_index in range(samples):
                angle = angle_index * 2 * math.pi / samples
                origin = np.array([x + radius * math.cos(angle), y + radius * math.sin(angle), .15])
                assert_clear(origin, f"{socket['id']} {label} angle {angle_index}")
                clear_rays += 1
        origin = np.array([x + (bore_r + .001), y, .15])
        wall_hits = ray_hits(triangles, origin, direction)
        assert len(wall_hits) >= 1, f"bore edge failed to encounter manufactured wall: {socket['id']}"
        edge_hits += len(wall_hits)
        radial_clearance = bore_r - cable_r
        assert radial_clearance >= .0005, (socket["id"], radial_clearance)
        assert socket["compression_liner_radial_thickness_m"] == .0012
        if socket["class"] == "control-data":
            assert socket["strand_count"] == 6 and socket["strand_outer_diameter_m"] == .006
            centers = np.array([[x + .0065 * math.cos(i * math.pi / 3),
                                 y + .0065 * math.sin(i * math.pi / 3)] for i in range(6)])
            separations = [np.linalg.norm(a - b) for i, a in enumerate(centers) for b in centers[i + 1:]]
            assert min(separations) >= .006
            assert .0065 + .003 <= cable_r
            for strand, center in enumerate(centers):
                for angle_index in range(32):
                    angle = angle_index * 2 * math.pi / 32
                    origin = np.array([center[0] + .003 * math.cos(angle), center[1] + .003 * math.sin(angle), .15])
                    assert_clear(origin, f"control-data strand {strand} angle {angle_index}")
                    clear_rays += 1
            packing = {"strand_count": 6, "strand_diameter_m": .006, "centers_xy_m": centers.tolist(),
                       "minimum_center_separation_m": min(separations), "packing_outer_diameter_m": .019,
                       "declared_loom_outer_diameter_m": bundle_diameter}
        for suffix in ("black compression gland", "compression nut", "sleeve collar 1", "sleeve collar 2"):
            name = socket["id"] + " " + suffix
            part = world_meshes[list(scene.graph.nodes_geometry).index(name)]
            assert np.allclose(part.bounds[:, :2].mean(axis=0), [x, y], atol=1e-7), name
            radial = np.linalg.norm(part.vertices[:, :2] - [x, y], axis=1)
            assert np.min(radial) >= bore_r - 1e-7, name
            if suffix == "black compression gland":
                for z in np.unique(np.round(part.vertices[:, 2], 7)):
                    loop = radial[np.abs(part.vertices[:, 2] - z) < 1e-7]
                    assert loop.max() - loop.min() >= .0012 - 1e-7, (name, z, loop.min(), loop.max())
    head_names = [name for name in scene.graph.nodes_geometry if "Mount bolt head" in name]
    assert len(head_names) == 4, head_names
    # Every cable/gland axis has adequate spacing for its outer compression envelope.
    for i, left in enumerate(sockets):
        for right in sockets[i + 1:]:
            a, b = np.array(left["center_local_m"][:2]), np.array(right["center_local_m"][:2])
            gap = float(np.linalg.norm(a - b) - left["gland_outer_diameter_m"] / 2 - right["gland_outer_diameter_m"] / 2)
            assert gap > .005, (left["id"], right["id"], gap)
            gland_gaps[f"{left['id']} / {right['id']}"] = gap
    body_node = next(name for name in scene.graph.nodes_geometry if "Cast enclosure body" in name)
    body_transform, body_geometry = scene.graph[body_node]
    body_mesh = scene.geometry[body_geometry].copy()
    body_mesh.apply_transform(body_transform)
    body_mesh.merge_vertices(merge_tex=True, merge_norm=True)
    edge_incidence = np.bincount(body_mesh.edges_unique_inverse)
    boundary_edges = int(np.count_nonzero(edge_incidence == 1))
    nonmanifold_edges = int(np.count_nonzero(edge_incidence > 2))
    degenerate_faces = int(np.count_nonzero(body_mesh.area_faces < 1e-12))
    winding_consistent = bool(body_mesh.is_winding_consistent)
    assert body_mesh.is_watertight and boundary_edges == 0, "cast enclosure is open"
    assert winding_consistent, "cast enclosure has inconsistent triangle winding"
    assert nonmanifold_edges == 0, f"cast enclosure has {nonmanifold_edges} nonmanifold edges"
    assert degenerate_faces == 0, f"cast enclosure has {degenerate_faces} degenerate faces"
    manifest = json.loads((ASSET / "provenance.json").read_text())
    assert manifest["raw_sha256"] == sha256(ROOT / manifest["raw_glb"])
    assert manifest["source_fit"]["source_faces"] == 739324
    radii = np.asarray(manifest["source_fit"]["fitted_outline_radii"])
    assert len(radii) == 64
    angles = np.arange(64) * 2 * math.pi / 64
    guides = np.column_stack((.14 * radii * np.cos(angles), .09 * radii * np.sin(angles)))
    directions = np.column_stack((np.cos(angles), np.sin(angles)))
    expected_support = np.max(guides @ directions.T, axis=0)
    actual_support = np.max(body_mesh.vertices[:, :2] @ directions.T, axis=0)
    contour_error = np.abs(expected_support - actual_support)
    assert contour_error.max() < .002, contour_error.max()
    assert np.corrcoef(expected_support, actual_support)[0, 1] > .999
    materials = test_materials(scene)
    return {"bounds_glb_m": bounds.tolist(), "extents_glb_m": extents.tolist(),
            "body_shell_bounds_glb_m": body_mesh.bounds.tolist(),
            "body_shell_extents_glb_m": body_mesh.extents.tolist(),
            "body_shell_watertight": bool(body_mesh.is_watertight),
            "body_shell_surface_components": len(body_mesh.split(only_watertight=False)),
            "body_shell_boundary_edges": boundary_edges,
            "body_shell_nonmanifold_edges": nonmanifold_edges,
            "body_shell_degenerate_faces": degenerate_faces,
            "body_shell_winding_consistent": winding_consistent,
            "triangle_count": int(len(triangles)), "clear_cable_rays": clear_rays,
            "bore_edge_wall_hits": edge_hits, "socket_gland_edge_clearances_m": gland_gaps,
            "physical_parts": part_metrics, "six_strand_packing": packing, "materials": materials,
            "source_contour": {"samples": 64, "support_max_error_m": float(contour_error.max()),
                               "support_rms_error_m": float(np.sqrt(np.mean(contour_error ** 2))),
                               "support_correlation": float(np.corrcoef(expected_support, actual_support)[0, 1])}}


def test_materials(scene):
    colors = {}
    for name, mesh in scene.geometry.items():
        material = mesh.visual.material
        if "Cast olive" in material.name:
            assert material.baseColorTexture is not None, name
            pixels = np.asarray(material.baseColorTexture.convert("RGB")) / 255
            mean = pixels.mean(axis=(0, 1))
            assert mean[1] > mean[0] > mean[2], (name, mean)
            assert .03 < mean[1] < .65, (name, mean)
            assert material.roughnessFactor >= .6 and material.metallicFactor < .4
            colors[material.name] = {"mean_texture_srgb": mean.tolist(), "roughness": material.roughnessFactor,
                                     "metallic": material.metallicFactor}
        elif "black compression gland" in name:
            assert material.name == "Black compression polymer"
            assert max(material.baseColorFactor[:3]) < 10
        elif "compression nut" in name or "sleeve collar" in name:
            assert material.name == "Aged zinc fasteners"
            assert material.metallicFactor > .8
    return colors


def render_script_path() -> Path:
    path = EVIDENCE / "capture_hardware_blender.py"
    path.write_text(r'''import bpy, math
from mathutils import Vector
from pathlib import Path
out = Path(r"''' + str(EVIDENCE) + r'''")
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(out.parents[2] / "assets/props/stasis-wiring/stasis-wiring-enclosure.glb"))
scene = bpy.context.scene
assert scene.view_layers[0].material_override is None
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 20
scene.render.resolution_x = scene.render.resolution_y = 768
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.view_settings.view_transform = "AgX"
scene.world.color = (.18, .18, .18)
# Hide imported reference meshes and enable the neutral studio ground.
for ob in scene.objects:
    if ob.name == "Capture-only ground":
        ob.hide_render = False
        ob.location = (0, 0, -.13)
        ob.hide_set(False)
        ob.data.materials.clear()
        m = bpy.data.materials.new("Capture ground"); m.diffuse_color = (.25,.26,.27,1); m.use_nodes=True
        m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=(.25,.26,.27,1)
        m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value=.85
        ob.data.materials.append(m)
    if ob.type == "MESH" and "Capture-only ground" not in ob.name:
        ob.hide_render = False
# Capture rig is not part of the exported asset.
def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
def area(name, loc, power, size, color):
    data=bpy.data.lights.new(name, "AREA"); data.energy=power; data.shape="DISK"; data.size=size; data.color=color
    ob=bpy.data.objects.new(name,data); scene.collection.objects.link(ob); ob.location=loc; aim(ob,(0,0,0)); return ob
area("Key softbox",(-.32,-.40,.42),12,.38,(1.0,1.0,1.0))
area("Cool fill",(.38,-.22,.18),8,.32,(1.0,1.0,1.0))
area("Rim",(.10,.30,.34),10,.30,(1.0,1.0,1.0))
views=[("front-three-quarter",(.33,-.48,.26)),("power-port-side",(-.34,-.48,.18)),("rear-mounting-face",(.10,.48,.23)),("upper-profile",(.44,-.28,.48))]
cam_data=bpy.data.cameras.new("Hardware proof camera"); cam=bpy.data.objects.new("Hardware proof camera",cam_data); scene.collection.objects.link(cam); cam_data.lens=58; scene.camera=cam
for name,loc in views:
    cam.location=loc; aim(cam,(0,0,0)); scene.render.filepath=str(out/(name+".png")); bpy.ops.render.render(write_still=True)
''')
    return path


def render_captures():
    helper = render_script_path()
    log = EVIDENCE / "capture-blender.log"
    subprocess.run([str(BLENDER), "--background", str(BLEND), "--threads", "4",
                    "--python-exit-code", "1", "--python", str(helper)],
                   cwd=ROOT, check=True, stdout=log.open("w"), stderr=subprocess.STDOUT)
    images = [Image.open(EVIDENCE / f"{n}.png").convert("RGB") for n in
              ("front-three-quarter", "power-port-side", "rear-mounting-face", "upper-profile")]
    sheet = Image.new("RGB", (1280, 1280), (235, 235, 235))
    for image, xy in zip(images, ((0, 0), (640, 0), (0, 640), (640, 640))):
        image.thumbnail((640, 640))
        sheet.paste(image, xy)
    sheet.save(EVIDENCE / "hardware-four-views.png")
    original = Image.open(REFERENCE).convert("RGB")
    render = images[0]
    original = original.resize((640, 480), Image.Resampling.LANCZOS)
    render = render.resize((640, 480), Image.Resampling.LANCZOS)
    compare = Image.new("RGB", (1280, 480), (240, 240, 240))
    compare.paste(original, (0, 0)); compare.paste(render, (640, 0))
    draw = ImageDraw.Draw(compare)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 17)
    except OSError:
        font = ImageFont.load_default()
    draw.rectangle((0, 0, 639, 28), fill=(35, 35, 35)); draw.text((10, 5), "Reference | left", fill="white", font=font)
    draw.rectangle((640, 0, 1279, 28), fill=(35, 35, 35)); draw.text((650, 5), "Fitted | right", fill="white", font=font)
    compare.save(EVIDENCE / "hardware-reference-comparison.png")


def reexport_identity():
    before = sha256(GLB)
    log = EVIDENCE / "reexport.log"
    with log.open("w") as stream:
        subprocess.run([str(BLENDER), "--background", "--factory-startup", "--threads", "4",
                        "--python-exit-code", "1", "--python", str(BUILD)],
                       cwd=ROOT, check=True, stdout=stream, stderr=subprocess.STDOUT)
    after = sha256(GLB)
    assert before == after, f"byte identity failed: {before} != {after}"
    return before


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reexport", action="store_true")
    parser.add_argument("--capture", action="store_true")
    args = parser.parse_args()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    identity = reexport_identity() if args.reexport else None
    metrics = test_geometry()
    manifest_path = ASSET / "provenance.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["body_plus_accessories_bounds_glb_m"] = {"min": metrics["bounds_glb_m"][0], "max": metrics["bounds_glb_m"][1]}
    manifest["triangles_exported"] = metrics["triangle_count"]
    manifest["weights_sha256"] = sha256(WEIGHTS)
    manifest["fitted_glb_sha256"] = sha256(GLB)
    manifest["editable_blend_sha256"] = sha256(BLEND)
    manifest["test_metrics"] = metrics
    manifest["checks"]["through_bore_and_cable_clearance"] = (
        f"PASS: {metrics['clear_cable_rays']} jacket rays clear; "
        f"{metrics['bore_edge_wall_hits']} bore-edge rays hit manufactured walls"
    )
    manifest["checks"]["body_shell_topology"] = (
        f"PASS: watertight={metrics['body_shell_watertight']}, "
        f"components={metrics['body_shell_surface_components']}, "
        f"boundary_edges={metrics['body_shell_boundary_edges']}; "
        f"winding_consistent={metrics['body_shell_winding_consistent']}, "
        f"nonmanifold_edges={metrics['body_shell_nonmanifold_edges']}, "
        f"degenerate_faces={metrics['body_shell_degenerate_faces']}; "
        "bore paths separately pass ray-clearance and wall checks"
    )
    if args.reexport:
        manifest["byte_identical_reexport_sha256"] = identity
        manifest["checks"]["byte_identical_reexport"] = "PASS; two independent builds yielded identical fitted GLB SHA-256"
    if args.capture:
        render_captures()
        manifest["captures"] = [str((EVIDENCE / f"{n}.png").relative_to(ROOT)) for n in
                                 ("front-three-quarter", "power-port-side", "rear-mounting-face", "upper-profile")]
        manifest["comparison"] = str((EVIDENCE / "hardware-reference-comparison.png").relative_to(ROOT))
    manifest["verification"] = str((EVIDENCE / "verification.json").relative_to(ROOT))
    manifest["checks"]["physical_parts"] = f"PASS: all {len(metrics['physical_parts'])} parts closed, positive-volume, consistently wound; zero degenerate faces"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    (EVIDENCE / "verification.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"metrics": metrics, "weights_sha256": manifest["weights_sha256"],
                      "reexport": manifest.get("byte_identical_reexport_sha256"),
                      "captures": manifest.get("captures")}, indent=2))


if __name__ == "__main__":
    main()
