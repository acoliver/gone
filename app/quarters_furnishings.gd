class_name QuartersFurnishings
extends RefCounted

const ROOT := "res://assets/props/quarters/"
static var _fits: Dictionary = {}
const REAL_FURNITURE := {
	"bed": "bed", "desk_chair": "desk_chair", "dining_table": "dining_table",
	"dining_chair_1": "dining_chair", "dining_chair_2": "dining_chair",
	"desk": "desk", "console": "console", "bedside_l": "bedside", "bedside_r": "bedside",
	"view_screen": "view_screen", "media_cabinet": "media_cabinet", "lockers_over_bed": "lockers_over_bed",
}

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
			_wardrobe(group, state, finish)
		elif REAL_FURNITURE.has(prop.id):
			var source: String = REAL_FURNITURE[prop.id]
			var asset := _asset(source + ".glb", StringName(source), state)
			# The accepted bed includes the separate 1.1 m layout headboard.
			if prop.id == "bed": bounds.size.y = 1.1
			_fit(asset, bounds, prop.get("faces", "+z"), source + ".glb")
			group.add_child(asset)
			if prop.id == "bed": _bed_soft(group, asset, state)
		elif prop.id == "headboard":
			continue
		elif prop.id.begins_with("storage_"):
			_storage(group, prop, bounds, state, QuartersProps.interim_material(&"PaintedSteel", state))
		else:
			group.add_child(box("Standin_" + prop.id, bounds, finish))
	# The plan's .76 m desk envelope includes a .06 m rear upstand.
	# Seat the console on the accepted worktop, not on that raised lip.
	var desk := root.get_node("Placement_desk/desk")
	var top := desk.find_child("Worktop", true, false) as MeshInstance3D
	var worktop := ShipScene._world_frame(top) * top.get_aabb()
	var console := root.get_node("Placement_console/console") as Node3D
	console.position.y += worktop.end.y - _bounds(console).position.y
	var item_finish := StandardMaterial3D.new()
	item_finish.albedo_color = Color(0.32, 0.33, 0.33)
	item_finish.roughness = 0.85
	for item: Dictionary in QuartersInventory.small_items():
		var small := box("Standin_" + item.id, item.bounds, item_finish)
		if item.on == "desk":
			# The free strip beside the console ends at the worktop's outer edge.
			small.position.y = worktop.end.y + small.get_aabb().size.y / 2
			small.position.z = worktop.end.z - small.get_aabb().size.z / 2 - 0.05
		root.add_child(small)
	return root

static func _asset(path: String, prop: StringName, state: StringName) -> Node3D:
	var scene: PackedScene = load(ROOT + path)
	var asset := scene.instantiate() as Node3D
	asset.name = String(prop)
	QuartersProps.apply(asset, prop, state)
	return asset

static func _bounds(node: Node3D, parent: Transform3D = Transform3D.IDENTITY, visible_only: bool = false) -> AABB:
	if visible_only and not node.visible: return AABB()
	var result := AABB()
	var frame := parent * node.transform
	if node is MeshInstance3D: result = frame * node.get_aabb()
	for child: Node in node.get_children():
		if child is Node3D:
			var child_bounds := _bounds(child, frame, visible_only)
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
		var locker: bool = prop.id in ["storage_left_near", "storage_right_near"]
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
	if state == &"aged":
		for mesh: MeshInstance3D in group.find_children("Standin_*", "MeshInstance3D", false, false):
			mesh.set_instance_shader_parameter(&"floor_datum", QuartersLayout.FLOOR_Y)
			mesh.set_instance_shader_parameter(&"lateral_bounds", Vector4(41, 49, 1.7, 7.7))

static func _bed_soft(group: Node3D, bed: Node3D, state: StringName) -> void:
	var source := "bed_soft.glb" if state == &"as_built" else "bed_soft_aged.glb"
	var scene: PackedScene = load(ROOT + source)
	var soft := scene.instantiate() as Node3D
	soft.name = "bed_soft"
	# Cloth and debris share the frame's authored origin and imported finishes.
	soft.transform = bed.transform
	group.add_child(soft)

static func _wardrobe(group: Node3D, state: StringName, finish: Material) -> void:
	var wardrobe := _asset("wardrobe.glb", &"wardrobe", state)
	# The plan's X axis is mirrored in ship space. Preserve the documented
	# room -90 degree rotation and hinge handedness across that mapping.
	wardrobe.basis = Basis(Vector3.LEFT, Vector3.UP, Vector3.BACK) * Basis(Vector3.UP, -PI / 2)
	wardrobe.position = QuartersLayout.to_world(Vector3(7.675, 0, 3.6))
	group.add_child(wardrobe)
	var rail := wardrobe.find_child("Rail", true, false) as Node3D
	var shelf := wardrobe.find_child("BottomPanel", true, false) as MeshInstance3D
	var rail_frame := ShipScene._world_frame(rail)
	var shelf_top := (ShipScene._world_frame(shelf) * shelf.get_aabb()).end.y
	for debris: bool in [false, true]:
		var garment := _asset("dress_uniform.glb" if state == &"as_built" else "dress_uniform_aged.glb", &"dress_uniform", state)
		for piece: MeshInstance3D in garment.find_children("*", "MeshInstance3D", true, false):
			var fallen := String(piece.name).begins_with("FallenHem") or piece.name in [&"FibreDust", &"HeapFibres"]
			piece.visible = fallen == debris
		garment.name = "UniformFragments" if debris else "HangingUniform"
		# The former 55-degree preview turn protruded through the new carcass.
		# The source hook is at its origin; hang it directly on the real rail.
		garment.position = rail_frame.origin
		garment.basis = Basis(Vector3.UP, PI / 2)
		if debris and state == &"aged":
			var visible_bounds := _bounds(garment, Transform3D.IDENTITY, true)
			garment.position.y += shelf_top + 0.0005 - visible_bounds.position.y
		group.add_child(garment)
	for index: int in range(2):
		group.add_child(box("Standin_her_dress_%d" % (index + 1), AABB(Vector3(7.67, 0.45, 3.17 + index * 0.17), Vector3(0.08, 1.12, 0.12)), finish))
