"""Verify the exported GLB in trimesh, outside Blender."""
import json
import sys

import numpy as np
import trimesh

scene = trimesh.load(sys.argv[1], force="scene")
body_meshes = []
for node in scene.graph.nodes_geometry:
    if node in {"Hinges", "DoorVents", "Handle"}:
        continue
    transform, geometry_name = scene.graph[node]
    mesh = scene.geometry[geometry_name].copy()
    mesh.apply_transform(transform)
    body_meshes.append(mesh)
minimum, maximum = trimesh.util.concatenate(body_meshes).bounds
expected_minimum = np.array([-0.3, 0.0, -0.3])
expected_maximum = np.array([0.3, 2.4, 0.3])
bounds_pass = bool(np.all(np.abs(minimum - expected_minimum) <= 0.002) and
                    np.all(np.abs(maximum - expected_maximum) <= 0.002))
node_names = sorted(scene.graph.nodes_geometry)
face_transform, face_geometry = scene.graph["Door"]
door_mesh = scene.geometry[face_geometry].copy()
door_mesh.apply_transform(face_transform)
front_normal = door_mesh.face_normals[np.argmax(door_mesh.face_normals[:, 2])]
front_normal_pass = bool(front_normal[2] > 0.99)
door_matrix, _ = scene.graph["Door"]
opening_axis = -door_matrix[:3, 2]
opening_axis = opening_axis / np.linalg.norm(opening_axis)
opening_axis_pass = bool(np.dot(opening_axis, [0, 1, 0]) > 0.99)
hinge_matrix, hinge_geometry = scene.graph["Hinges"]
hinges = scene.geometry[hinge_geometry].copy()
hinges.apply_transform(hinge_matrix)
welded_vertices, vertex_indices = np.unique(np.round(hinges.vertices, 6), axis=0, return_inverse=True)
hinges = trimesh.Trimesh(vertices=welded_vertices,
                         faces=vertex_indices[hinges.faces], process=False)
hinge_components = len(hinges.split(only_watertight=False))
locker_bounds = np.array([minimum, maximum])
kick_matrix, kick_geometry = scene.graph["KickPlate"]
kick = scene.geometry[kick_geometry].copy()
kick.apply_transform(kick_matrix)
kick_bounds = kick.bounds
kick_setback = {
    "front_m": float(locker_bounds[1, 2] - kick_bounds[1, 2]),
    "left_m": float(kick_bounds[0, 0] - locker_bounds[0, 0]),
    "right_m": float(locker_bounds[1, 0] - kick_bounds[1, 0]),
}
kick_pass = all(abs(value - 0.040) <= 0.002 for value in kick_setback.values())

# Probe the six exported bounds faces toward the locker centre at 50 mm spacing.
probe_meshes = []
for node in scene.graph.nodes_geometry:
    transform, geometry_name = scene.graph[node]
    mesh = scene.geometry[geometry_name].copy()
    mesh.apply_transform(transform)
    probe_meshes.append(mesh)
combined = trimesh.util.concatenate(probe_meshes)
ray_origins = []
ray_directions = []
for axis in range(3):
    other_axes = [index for index in range(3) if index != axis]
    coords = [np.arange(minimum[index] + 0.025, maximum[index], 0.05) for index in other_axes]
    for side in (0, 1):
        face_value = (minimum if side == 0 else maximum)[axis]
        for a in coords[0]:
            for b in coords[1]:
                point = np.zeros(3)
                point[axis] = face_value + (-0.001 if side == 0 else 0.001)
                point[other_axes[0]] = a
                point[other_axes[1]] = b
                if point[1] < 0.105:
                    continue
                direction = np.array([0.0, 1.2, 0.0]) - point
                direction /= np.linalg.norm(direction)
                ray_origins.append(point)
                ray_directions.append(direction)
ray_origins = np.asarray(ray_origins)
ray_directions = np.asarray(ray_directions)
locations, ray_ids, _ = combined.ray.intersects_location(
    ray_origins, ray_directions, multiple_hits=False)
hit_distances = np.linalg.norm(locations - ray_origins[ray_ids], axis=1)
centre_distances = np.linalg.norm(np.array([0.0, 1.2, 0.0]) - ray_origins[ray_ids], axis=1)
valid_ray_ids = np.unique(ray_ids[hit_distances < centre_distances])
missed_rays = len(ray_origins) - len(valid_ray_ids)

# Sample visible faces on target meshes from the specified front-left hero camera.
visibility = {}
camera = np.array([-1.75, 2.107, 3.031])
for target_name in ("Hinges", "Handle", "DoorVents"):
    target_parts = []
    for node in scene.graph.nodes_geometry:
        if node == target_name or node.startswith(target_name + "_"):
            matrix, geometry_name = scene.graph[node]
            part = scene.geometry[geometry_name].copy()
            part.apply_transform(matrix)
            if target_name != "DoorVents" or part.bounds[1, 2] > 0.28:
                target_parts.append(part)
    target = trimesh.util.concatenate(target_parts)
    centroids = target.triangles_center
    if len(centroids) > 48:
        centroids = centroids[np.linspace(0, len(centroids) - 1, 48, dtype=int)]
    origins = np.repeat(camera[None, :], len(centroids), axis=0)
    directions = centroids - origins
    target_distances = np.linalg.norm(directions, axis=1)
    directions /= target_distances[:, None]
    hit_locations, hit_rays, _ = combined.ray.intersects_location(origins, directions, multiple_hits=False)
    first_hit = np.zeros(len(centroids), dtype=bool)
    for location, ray_id in zip(hit_locations, hit_rays):
        first_hit[ray_id] = np.linalg.norm(location - camera) >= target_distances[ray_id] - 0.025
    fraction = float(first_hit.mean()) if len(first_hit) else 0.0
    visibility[target_name] = fraction
visibility_pass = all(value >= 0.60 for value in visibility.values())
expected_names = {
    "KickPlate", "DoorReturn_L", "DoorReturn_R", "DoorReturn_T", "DoorReturn_B",
    "SidePanel_L", "SidePanel_R", "BackPanel", "TopPanel", "BottomPanel",
    "SurroundStile_L", "SurroundStile_R", "SurroundHead", "SurroundSill",
}
name_pass = expected_names.issubset(node_names) and all(" " not in name and ".00" not in name for name in node_names)
report = {
    "bounds_source": "trimesh exported GLB, primary bounds check",
    "bounds_m": {"min": minimum.tolist(), "max": maximum.tolist(),
                 "expected_min": expected_minimum.tolist(), "expected_max": expected_maximum.tolist(),
                 "tolerance_m": 0.002, "pass": bounds_pass},
    "node_names": node_names,
    "required_named_nodes_present": name_pass,
    "door_front_normal": front_normal.tolist(),
    "door_front_normal_points_plus_z": front_normal_pass,
    "door_opening_axis_local_plus_y": opening_axis.tolist(),
    "door_opening_axis_pass": opening_axis_pass,
    "hinge_connected_components_after_merge": hinge_components,
    "kick_plate_setback_m": kick_setback,
    "kick_plate_setback_pass": kick_pass,
    "closed_carcass": {"missed_rays": missed_rays, "sample_count": len(ray_origins), "pass": missed_rays == 0},
    "front_visibility_fraction": visibility,
    "front_visibility_pass": visibility_pass,
    "pass": bounds_pass and name_pass and front_normal_pass and opening_axis_pass and hinge_components == 3 and kick_pass and missed_rays == 0 and visibility_pass,
}
print(json.dumps(report, indent=2))
if not report["pass"]:
    raise SystemExit("exported GLB verification failed")
