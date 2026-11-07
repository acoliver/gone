"""Measure the exported locker GLB and certify its door sweep."""
import argparse
import json
import math
from pathlib import Path
import subprocess
import sys

import bpy
from mathutils import Matrix
from mathutils.bvhtree import BVHTree


def world_mesh(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    matrix = obj.matrix_world
    vertices = [matrix @ v.co for v in mesh.vertices]
    faces = [tuple(p.vertices) for p in mesh.polygons]
    return vertices, faces, mesh


def bounds_for(objects):
    points = []
    for obj in objects:
        if obj.type == "MESH":
            verts, _, mesh = world_mesh(obj)
            points.extend(verts)
            obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh_clear()
    mins = [min(v[i] for v in points) for i in range(3)]
    maxs = [max(v[i] for v in points) for i in range(3)]
    return mins, maxs, [maxs[i] - mins[i] for i in range(3)]


def bvh_for(objects, hinge_edge=None, clearance_m=0.015):
    vertices = []
    faces = []
    for obj in objects:
        verts, polygons, mesh = world_mesh(obj)
        offset = len(vertices)
        vertices.extend(verts)
        for poly in mesh.polygons:
            if obj == hinge_edge:
                local_x = sum(mesh.vertices[index].co.x for index in poly.vertices) / len(poly.vertices)
                if local_x <= clearance_m:
                    continue
            faces.append(tuple(index + offset for index in poly.vertices))
        obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh_clear()
    return BVHTree.FromPolygons(vertices, faces, all_triangles=False)


def descendants(root, objects):
    result = [root] if root.type == "MESH" else []
    for candidate in objects:
        parent = candidate.parent
        while parent:
            if parent == root:
                result.append(candidate)
                break
            parent = parent.parent
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(args.input.resolve()))
    objects = [o for o in bpy.data.objects if o.type == "MESH"]
    by_name = {o.name: o for o in bpy.data.objects}
    mins, maxs, extents = bounds_for(objects)
    expected = {"Carcass": None, "Door": None, "DoorVents": "Door", "HandlePocket": "Door",
                "Handle": "Door", "Hinges": "Carcass", "Rivets": "Carcass"}
    hierarchy = {}
    for name, parent in expected.items():
        obj = by_name.get(name)
        hierarchy[name] = {"present": obj is not None,
                           "parent": obj.parent.name if obj and obj.parent else None,
                           "expected_parent": parent,
                           "pass": bool(obj is not None and ((obj.parent.name if obj.parent else None) == parent))}
    door = by_name["Door"]
    door_base = door.matrix_world.copy()
    pivot = list(door.matrix_world.translation)
    pivot_matrix = Matrix.Translation(door.matrix_world.translation)
    expected_pivot = [-0.240, -0.258, 0.110]
    pivot_error = [pivot[i] - expected_pivot[i] for i in range(3)]
    carcass = by_name["Carcass"]
    door_parts = descendants(door, objects)
    carcass_parts = descendants(carcass, objects)
    fixed_parts = [part for part in carcass_parts if part.name != "Hinges"]
    hinge_clearance_m = 0.015
    carcass_tree = bvh_for(fixed_parts)
    sweep = []
    for deg in range(101):
        rotation = Matrix.Rotation(math.radians(-deg), 4, "Z")
        door.matrix_world = pivot_matrix @ rotation @ pivot_matrix.inverted() @ door_base
        bpy.context.view_layer.update()
        bpy.context.evaluated_depsgraph_get().update()
        moving_tree = bvh_for(door_parts, hinge_edge=door, clearance_m=hinge_clearance_m)
        overlaps = moving_tree.overlap(carcass_tree)
        detail = []
        if overlaps:
            for moving in door_parts:
                for fixed in fixed_parts:
                    count = len(bvh_for([moving], hinge_edge=door if moving == door else None,
                                        clearance_m=hinge_clearance_m).overlap(bvh_for([fixed])))
                    if count:
                        detail.append({"moving": moving.name, "fixed": fixed.name, "pairs": count})
        sample = {"angle_degrees_outward": deg, "surface_intersection_pairs": len(overlaps), "object_pairs": detail}
        if deg in (0, 10, 45, 90, 100):
            moving_vertices, _, mesh = world_mesh(door)
            sample["door_bounds_m"] = [[min(v[i] for v in moving_vertices), max(v[i] for v in moving_vertices)] for i in range(3)]
            door.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh_clear()
        sweep.append(sample)
    door.matrix_world = door_base
    bpy.context.view_layer.update()

    triangle_count = 0
    nonmanifold_edges = 0
    degenerate_faces = 0
    zero_or_inward_normals = 0
    missing_uvs = []
    mesh_reports = {}
    for obj in objects:
        mesh = obj.data
        if not mesh.uv_layers:
            missing_uvs.append(obj.name)
        triangle_count += sum(max(0, len(poly.vertices) - 2) for poly in mesh.polygons)
        edge_counts = {}
        positions = [tuple(round(float(c), 6) for c in vertex.co) for vertex in mesh.vertices]
        for poly in mesh.polygons:
            area = poly.area
            if area <= 1e-12:
                degenerate_faces += 1
            points = [positions[index] for index in poly.vertices]
            for a, b in zip(points, points[1:] + points[:1]):
                edge = tuple(sorted((a, b)))
                edge_counts[edge] = edge_counts.get(edge, 0) + 1
        bad = sum(count != 2 for count in edge_counts.values())
        nonmanifold_edges += bad
        signed_volume = 0.0
        for poly in mesh.polygons:
            if poly.area > 1e-12 and poly.normal.length < 0.999:
                zero_or_inward_normals += 1
            points = [mesh.vertices[index].co for index in poly.vertices]
            for index in range(1, len(points) - 1):
                signed_volume += points[0].dot(points[index].cross(points[index + 1])) / 6.0
        if signed_volume <= 0:
            zero_or_inward_normals += 1
        mesh_reports[obj.name] = {"triangles": sum(max(0, len(p.vertices) - 2) for p in mesh.polygons),
                                  "nonmanifold_edges": bad,
                                  "degenerate_faces": sum(p.area <= 1e-12 for p in mesh.polygons),
                                  "signed_volume_m3": signed_volume}

    tolerance = 0.002
    dimension_pass = all(abs(extents[i] - (0.6, 0.6, 2.4)[i]) <= tolerance for i in range(3))
    kick_plate = by_name.get("KickPlate")
    kick_min, kick_max, kick_extents = bounds_for([kick_plate]) if kick_plate else ([], [], [])
    kick_plate_pass = bool(kick_plate and max(abs(kick_extents[i] - (0.520, 0.520, 0.105)[i]) for i in range(3)) <= tolerance
                          and abs(kick_min[2]) <= tolerance and abs(kick_max[2] - 0.105) <= tolerance)
    swing_hits = [v for v in sweep if v["surface_intersection_pairs"] > 0]
    required_materials = {"PaintedSteel", "BareSteel", "DarkSteel"}
    exported_materials = sorted({material.name for obj in objects for material in obj.data.materials if material})
    report = {
        "bounds_m": {"min": mins, "max": maxs, "extents_xyz": extents,
                     "target_xyz": [0.6, 0.6, 2.4], "tolerance_m": tolerance, "pass": dimension_pass},
        "hierarchy": hierarchy,
        "kick_plate": {"present": kick_plate is not None, "bounds_min_m": kick_min,
                       "bounds_max_m": kick_max, "extents_xyz_m": kick_extents,
                       "target_extents_xyz_m": [0.520, 0.520, 0.105],
                       "recess_m": 0.040, "pass": kick_plate_pass},
        "door_pivot": {"world_position_m": pivot, "expected_m": expected_pivot,
                       "error_m": pivot_error, "pass": max(abs(v) for v in pivot_error) <= 0.002},
        "door_sweep": {"sample_count": len(sweep), "range_degrees": [0, 100],
                       "direction": "outward, negative local Y rotation", "hinge_edge_clearance_m": hinge_clearance_m,
                       "hinges_excluded_as_mating_hardware": True, "intersections": swing_hits,
                       "diagnostic_samples": [v for v in sweep if "door_bounds_m" in v],
                       "pass": not swing_hits},
        "topology": {"triangle_count": triangle_count, "triangle_limit": 6000,
                     "nonmanifold_edges": nonmanifold_edges, "degenerate_faces": degenerate_faces,
                     "invalid_normals": zero_or_inward_normals,
                     "missing_uv_meshes": missing_uvs,
                     "materials": exported_materials,
                     "required_materials": sorted(required_materials),
                     "missing_materials": sorted(required_materials - set(exported_materials)),
                     "meshes": mesh_reports,
                     "pass": triangle_count < 6000 and nonmanifold_edges == 0 and degenerate_faces == 0 and zero_or_inward_normals == 0 and not missing_uvs and required_materials.issubset(exported_materials)},
    }
    report["pass"] = (dimension_pass and kick_plate_pass and all(v["pass"] for v in hierarchy.values()) and
                      report["door_pivot"]["pass"] and report["door_sweep"]["pass"] and report["topology"]["pass"])
    trimesh_python = "/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python"
    trimesh_script = Path(__file__).with_name("trimesh_verify.py")
    trimesh_result = subprocess.run([trimesh_python, str(trimesh_script), str(args.input.resolve())],
                                    capture_output=True, text=True, check=True)
    report["trimesh_export"] = json.loads(trimesh_result.stdout)
    report["pass"] = report["pass"] and report["trimesh_export"]["pass"]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if not report["pass"]:
        raise SystemExit("locker verification failed")


if __name__ == "__main__":
    main()
