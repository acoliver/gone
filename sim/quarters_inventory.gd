class_name QuartersInventory
extends RefCounted
## The approved plan supplies the single placement list for both states and collision.

static var _plan: Dictionary = {}

static func plan() -> Dictionary:
	if _plan.is_empty():
		_plan = JSON.parse_string(FileAccess.get_file_as_string("res://docs/art/quarters/layout.json"))
		assert(_plan.has_all(["room", "props", "small_items", "reach_targets", "camera"]), "quarters plan is complete")
	return _plan

static func prop_bounds(prop: Dictionary) -> AABB:
	var box: Array = prop.box
	var base := float(prop.get("h_from", 0.0))
	return AABB(Vector3(box[0], base, box[1]), Vector3(box[2] - box[0], float(prop.h) - base, box[3] - box[1]))

static func props() -> Array[Dictionary]:
	var result: Array[Dictionary] = []
	result.assign(plan().props)
	return result

static func small_items() -> Array[Dictionary]:
	var by_id := {}
	for prop: Dictionary in props(): by_id[prop.id] = prop
	var result: Array[Dictionary] = []
	var counts := {}
	for item: Dictionary in plan().small_items:
		var bounds: AABB
		if item.has("at"):
			bounds = AABB(Vector3(item.at[0] - 0.14, 0, item.at[1] - 0.12), Vector3(0.28, 0.25, 0.24))
		else:
			var parent := prop_bounds(by_id[item.on])
			var index := int(counts.get(item.on, 0))
			counts[item.on] = index + 1
			var point := parent.get_center()
			point.y = parent.end.y
			point.x += (index % 2 - 0.5) * minf(0.25, parent.size.x * 0.35)
			point.z += (index / 2 - 0.5) * minf(0.22, parent.size.z * 0.30)
			bounds = AABB(point - Vector3(0.05, 0, 0.05), Vector3(0.10, 0.08, 0.10))
		result.append({"id": item.id, "on": item.on, "bounds": bounds})
	return result

static func world_bounds(local: AABB) -> AABB:
	var start := QuartersLayout.to_world(local.position)
	var end := QuartersLayout.to_world(local.end)
	return AABB(start.min(end), (end - start).abs())

static func wardrobe_door() -> AABB:
	# The approved parked leaf extends toward room-left from its hinge.
	var end := Vector3(7.35 - sin(deg_to_rad(100)), 0, 4.1 - cos(deg_to_rad(100)))
	return AABB(Vector3(end.x, 0, 4.07), Vector3(7.35 - end.x, 2.2, end.z - 4.07))
