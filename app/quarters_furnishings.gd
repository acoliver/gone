class_name QuartersFurnishings
extends RefCounted

const ROOT := "res://assets/props/quarters/"
static var _fits: Dictionary = {}

static func build(state: StringName) -> Node3D:
	var root := Node3D.new()
	root.name = "Remembered" if state == &"as_built" else "Present"
	var finish := StandardMaterial3D.new()
	finish.albedo_color = Color(0.58, 0.47, 0.33) if state == &"as_built" else Color(0.25, 0.23, 0.20)
	finish.roughness = 0.65 if state == &"as_built" else 1.0
	for prop: Dictionary in QuartersInventory.props():
		var group := Node3D.new()
		group.name = "Placement_" + prop.id
		root.add_child(group)
		var bounds := QuartersInventory.prop_bounds(prop)
		if prop.id == "sofa":
			var sofa := _asset("sofa.glb" if state == &"as_built" else "sofa_aged.glb", &"sofa", state)
			_fit(sofa, bounds, prop.faces, "sofa.glb")
			group.add_child(sofa)
		elif prop.id == "wardrobe":
			_wardrobe(group, bounds, state, finish)
		elif prop.id.begins_with("storage_") or prop.id == "lockers_over_bed":
			_storage(group, prop, bounds, state, finish)
		else:
			group.add_child(box("Standin_" + prop.id, bounds, finish))
	for item: Dictionary in QuartersInventory.small_items():
		root.add_child(box("Standin_" + item.id, item.bounds, finish))
	return root

static func _asset(path: String, prop: StringName, state: StringName) -> Node3D:
	var scene: PackedScene = load(ROOT + path)
	var asset := scene.instantiate() as Node3D
	asset.name = String(prop)
	QuartersProps.apply(asset, prop, state)
	return asset

static func _bounds(node: Node3D, parent: Transform3D = Transform3D.IDENTITY) -> AABB:
	var result := AABB()
	var frame := parent * node.transform
	if node is MeshInstance3D: result = frame * node.get_aabb()
	for child: Node in node.get_children():
		if child is Node3D:
			var child_bounds := _bounds(child, frame)
			if child_bounds.has_volume(): result = child_bounds if not result.has_volume() else result.merge(child_bounds)
	return result

static func _yaw(face: String) -> float:
	# Imported props face +Z; the plan's +X points toward ship -X.
	return {"-z": PI, "+z": 0.0, "+x": -PI / 2, "-x": PI / 2}[face]

static func _fit(asset: Node3D, local: AABB, face: String, source: String) -> void:
	var key := source + str(local) + face
	if not _fits.has(key):
		var scene: PackedScene = load(ROOT + source)
		var reference := scene.instantiate() as Node3D
		reference.rotation.y = _yaw(face)
		var bounds := _bounds(reference)
		var target := QuartersInventory.world_bounds(local)
		reference.basis = Basis.from_scale(target.size / bounds.size) * reference.basis
		bounds = _bounds(reference)
		reference.position = target.position - bounds.position
		_fits[key] = reference.transform
		reference.free()
	asset.transform = _fits[key]

static func box(id: String, local: AABB, finish: Material) -> MeshInstance3D:
	var result := MeshInstance3D.new()
	result.name = id
	var bounds := QuartersInventory.world_bounds(local)
	result.mesh = RoomGeometry._box_mesh(bounds.size)
	result.position = bounds.get_center()
	result.material_override = finish
	return result

static func _storage(group: Node3D, prop: Dictionary, bounds: AABB, state: StringName, finish: Material) -> void:
	var along_x: bool = prop.faces in ["-z", "+z"]
	var length := bounds.size.x if along_x else bounds.size.z
	var count := floori((length + 0.0001) / 0.6)
	for index: int in range(count):
		var slot := bounds
		if along_x:
			slot.position.x += index * 0.6
			slot.size.x = 0.6
		else:
			slot.position.z += index * 0.6
			slot.size.z = 0.6
		var locker: bool = prop.id == "lockers_over_bed" or prop.id in ["storage_left_near", "storage_right_near"]
		if prop.id == "storage_far_l": locker = index in [0, 2]
		if prop.id == "storage_far_r": locker = index in [2, 3]
		if prop.id == "storage_right_far": locker = index == count - 1
		if locker:
			var asset := _asset("storage_locker_module.glb", &"storage_locker_module", state)
			_fit(asset, slot, prop.faces, "storage_locker_module.glb")
			group.add_child(asset)
		else:
			group.add_child(box("Standin_%s_slot_%d" % [prop.id, index], slot, finish))
	var remainder := length - count * 0.6
	if remainder > 0.0001:
		var slot := bounds
		if along_x:
			slot.position.x += count * 0.6
			slot.size.x = remainder
		else:
			slot.position.z += count * 0.6
			slot.size.z = remainder
		group.add_child(box("Standin_" + prop.id + "_infill", slot, finish))

static func _wardrobe(group: Node3D, bounds: AABB, state: StringName, finish: Material) -> void:
	var carcass := Node3D.new()
	carcass.name = "Standin_wardrobe"
	group.add_child(carcass)
	for z: float in [bounds.position.z, bounds.end.z - 0.04]:
		carcass.add_child(box("Side", AABB(Vector3(bounds.position.x, 0, z), Vector3(bounds.size.x, bounds.size.y, 0.04)), finish))
	carcass.add_child(box("Back", AABB(Vector3(bounds.end.x - 0.04, 0, bounds.position.z), Vector3(0.04, bounds.size.y, bounds.size.z)), finish))
	for y: float in [0.0, bounds.end.y - 0.04]:
		carcass.add_child(box("Shelf", AABB(Vector3(bounds.position.x, y, bounds.position.z), Vector3(bounds.size.x, 0.04, bounds.size.z)), finish))
	var leaf := box("OpenDoor", AABB(Vector3(6.85, 0, 4.08), Vector3(1, 2.2, 0.04)), finish)
	leaf.position = QuartersLayout.to_world(Vector3(7.35 - sin(deg_to_rad(100)) / 2, 1.1, 4.1 - cos(deg_to_rad(100)) / 2))
	leaf.rotation.y = deg_to_rad(-10)
	carcass.add_child(leaf)
	var inward := Basis(Vector3.UP, PI / 2)
	for debris: bool in [false, true]:
		var garment := _asset("dress_uniform.glb" if state == &"as_built" else "dress_uniform_aged.glb", &"dress_uniform", state)
		for piece: MeshInstance3D in garment.find_children("*", "MeshInstance3D", true, false):
			var fallen := String(piece.name).begins_with("FallenHem") or piece.name in [&"FibreDust", &"HeapFibres"]
			piece.visible = fallen == debris
		garment.name = "UniformFragments" if debris else "HangingUniform"
		var preview_offset := Vector3(-0.015, 1.055, 0.10) if debris else Vector3(-0.015, 1.65, 0.17)
		garment.position = QuartersLayout.to_world(Vector3(7.70, 0, 3.58)) + inward * preview_offset
		garment.basis = inward * Basis(Vector3.UP, deg_to_rad(55))
		group.add_child(garment)
	var rail := box("Rail", AABB(Vector3(7.57, 1.633, 3.13), Vector3(0.018, 0.018, 0.94)), finish)
	carcass.add_child(rail)
	for index: int in range(2):
		carcass.add_child(box("Standin_her_dress_%d" % (index + 1), AABB(Vector3(7.67, 0.45, 3.17 + index * 0.17), Vector3(0.08, 1.12, 0.12)), finish))
