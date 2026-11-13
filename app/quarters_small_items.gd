class_name QuartersSmallItems
extends RefCounted

# Room X/Z positions leave the imported lamps, desk upstands and console clear.
const PLACEMENTS := {
	"photo_frame": ["photo_frame", "bedside_r", "Top", Vector2(5.16, 5.74), PI],
	"boots": ["boots", "floor", "", Vector2(5.06, 5.28), PI],
	"hairbrush": ["hairbrush", "bedside_l", "Top", Vector2(2.83, 5.70), PI / 2],
	"jewellery_box": ["jewellery_box", "bedside_l", "Top", Vector2(2.99, 5.82), PI],
	"medal_case": ["medal_case", "desk", "Worktop", Vector2(7.80, 2.67), PI / 2],
	"data_tablet_1": ["data_tablet", "sofa", "SeatCushion_C", Vector2(1.98, 2.63), PI / 2],
	"data_tablet_2": ["data_tablet", "desk", "Worktop", Vector2(7.48, 2.67), PI / 2],
	"mug_1": ["mug", "dining_table", "Top", Vector2(4.91, 1.65), 0.0],
	"mug_2": ["mug", "dining_table", "Top", Vector2(5.39, 1.75), PI],
	"plate_1": ["plate", "dining_table", "Top", Vector2(5.15, 1.48), 0.0],
	"plate_2": ["plate", "dining_table", "Top", Vector2(5.15, 1.92), 0.0],
}

static func add_to(root: Node3D, state: StringName) -> void:
	for id: String in PLACEMENTS:
		var placement: Array = PLACEMENTS[id]
		var group := Node3D.new()
		group.name = "Item_" + id
		group.position = QuartersLayout.to_world(Vector3(placement[3].x, 0, placement[3].y))
		group.rotation.y = placement[4]
		root.add_child(group)
		var path: String = placement[0] + (".glb" if state == &"as_built" else "_aged.glb")
		var asset := (load(QuartersFurnishings.ROOT + path) as PackedScene).instantiate() as Node3D
		group.add_child(asset)
		var bounds := QuartersFurnishings._bounds(asset, group.transform)
		var height := QuartersLayout.FLOOR_Y
		if placement[1] != "floor":
			var furniture := root.get_node("Placement_" + placement[1])
			var support := furniture.find_child(placement[2], true, false) as MeshInstance3D
			height = seat_height(support, bounds) if placement[1] == "sofa" else (ShipScene._world_frame(support) * support.get_aabb()).end.y
		# Keep the layout root identical. The aged sofa's collapsed seat needs
		# a lower child offset; rigid support surfaces have identical offsets.
		asset.position.y += height + 0.0005 - bounds.position.y
		if id == "photo_frame":
			for mesh: MeshInstance3D in asset.find_children("*", "MeshInstance3D", true, false):
				for surface: int in range(mesh.mesh.get_surface_count()):
					if mesh.mesh.surface_get_material(surface).resource_name == "Glass":
						mesh.set_surface_override_material(surface, QuartersProps.interim_material(&"Glass", state))

static func seat_height(support: MeshInstance3D, footprint: AABB) -> float:
	var frame := ShipScene._world_frame(support)
	var faces := support.mesh.get_faces()
	var highest := -INF
	for index: int in range(0, faces.size(), 3):
		var polygon: Array[Vector3] = [frame * faces[index], frame * faces[index + 1], frame * faces[index + 2]]
		for edge: Vector3 in [Vector3(0, footprint.position.x, 1), Vector3(0, footprint.end.x, -1), Vector3(2, footprint.position.z, 1), Vector3(2, footprint.end.z, -1)]:
			polygon = _clip(polygon, int(edge.x), edge.y, edge.z)
		for point: Vector3 in polygon: highest = maxf(highest, point.y)
	assert(is_finite(highest), "tablet footprint must intersect the real seat")
	return highest

static func _clip(polygon: Array[Vector3], axis: int, edge: float, direction: float) -> Array[Vector3]:
	var result: Array[Vector3] = []
	if polygon.is_empty(): return result
	var previous: Vector3 = polygon.back()
	for point: Vector3 in polygon:
		var before := (previous[axis] - edge) * direction
		var after := (point[axis] - edge) * direction
		if (before >= 0) != (after >= 0): result.append(previous.lerp(point, before / (before - after)))
		if after >= 0: result.append(point)
		previous = point
	return result
