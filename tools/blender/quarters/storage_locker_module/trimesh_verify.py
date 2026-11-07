"""Verify the exported GLB in trimesh, outside Blender."""
import json
import sys

import numpy as np
import trimesh

scene = trimesh.load(sys.argv[1], force="scene")
minimum, maximum = scene.bounds
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
locker_bounds = scene.bounds
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
    "pass": bounds_pass and name_pass and front_normal_pass and opening_axis_pass and hinge_components == 3 and kick_pass,
}
print(json.dumps(report, indent=2))
if not report["pass"]:
    raise SystemExit("exported GLB verification failed")
