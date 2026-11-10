class_name StasisWiring
extends RefCounted
## Shared baked installation and standalone engineering proof presenters.

const DIR := "res://assets/props/stasis-wiring/"
# Issue 110: measured -65 mm local back on X=-6, ports facing the +X trunk.
const SOURCE := Vector3(-5.935, 2.75, -3.1)
const TYPES := [&"supported-transition", &"fault-frame-pair"]
static var _packed: Dictionary = {}
static var _frame: Surfaces.SurfaceFrame
static var _panel_hardware: StandardMaterial3D

static func _asset(path: String) -> Node3D:
	if not _packed.has(path):
		var resource := load(path) as PackedScene
		assert(resource != null, "required wiring proof asset: " + path)
		_packed[path] = resource
	return (_packed[path] as PackedScene).instantiate() as Node3D

static func installation() -> Node3D:
	var result := Node3D.new()
	result.name = "StasisWiringInstallation"
	result.add_child(_asset(DIR + "production-installation.glb"))
	var enclosure := _asset(DIR + "stasis-wiring-enclosure.glb")
	enclosure.name = "PhysicalSourceEnclosure"
	enclosure.position = SOURCE
	enclosure.rotation.y = PI / 2.0
	result.add_child(enclosure)
	return result

static func build(kind: StringName, include_context: bool = true) -> Node3D:
	assert(TYPES.has(kind), "unknown wiring proof assembly")
	var result := Node3D.new()
	result.name = "StasisWiringProof"
	var asset_name := "supported-transition-aligned" if kind == &"supported-transition" else String(kind)
	var mesh := _asset(DIR + asset_name + ".glb")
	result.add_child(mesh)
	_bind_steel(mesh, kind == &"supported-transition")
	if kind == &"fault-frame-pair": _source_retained_seats(mesh)
	if kind == &"supported-transition":
		var enclosure := _asset(DIR + "stasis-wiring-enclosure.glb")
		enclosure.name = "PhysicalSourceEnclosure"
		enclosure.position = SOURCE
		enclosure.rotation.y = PI / 2.0
		result.add_child(enclosure)
	if include_context:
		var context := Node3D.new()
		context.name = "ProofContext"
		result.add_child(context)
		if kind == &"supported-transition":
			for x: float in [-5.4, -4.2]: _panel(context, Vector3(x, 2.99, -3.3))
			_stage_box(context, Vector3(-4.8, -0.12, -3.25), Vector3(3.0, 0.24, 1.8), &"floor")
			_stage_box(context, Vector3(-4.8, 1.65, -4.04), Vector3(3.0, 3.3, 0.08), &"wall")
			_stage_box(context, Vector3(-6.04, 1.65, -3.25), Vector3(0.08, 3.3, 1.8), &"wall")
		else:
			for x: float in [-1.8, -0.6, 0.6]:
				for z: float in [-1.5, -0.9, -0.3]:
					if is_equal_approx(x, -0.6) and is_equal_approx(z, -0.9): continue
					_panel(context, Vector3(x, 2.99, z))
			_stage_box(context, Vector3(-0.6, -0.04, -0.9), Vector3(4.0, 0.08, 3.2), &"floor")
	return result

static func _steel_frame() -> Surfaces.SurfaceFrame:
	if _frame == null:
		_frame = Surfaces.surface_frame(ShipLayout.authored().layout, ShipLayout.BAY_ID, &"RAILS")
		_frame.world_from_surface = Transform3D.IDENTITY
		_frame.bounds = AABB(Vector3(-6.1, -0.3, -4.1), Vector3(12.2, 3.7, 8.2))
		_frame.floor_datum = 0.0
	return _frame

static func _bind_steel(node: Node, keep_native_fittings: bool = false) -> void:
	if node is MeshInstance3D:
		var piece := node as MeshInstance3D
		var label := String(piece.name)
		if label.begins_with("seat_") or label.begins_with("fallen_fragment"):
			piece.material_override = SeatRailComponent.material()
		elif label.begins_with("steel_frame"):
			piece.material_override = _hardware_material()
		elif label.begins_with("steel_") and not keep_native_fittings:
			Surfaces.bind(piece, &"pipe" if label.contains("pipe") else &"hardware", _steel_frame())
	for child: Node in node.get_children(): _bind_steel(child, keep_native_fittings)

static func _panel(parent: Node3D, position: Vector3) -> void:
	var panel := _asset("res://assets/props/bay-ceiling/intact.glb")
	panel.position = position
	parent.add_child(panel)
	_panel_materials(panel)

static func _hardware_material() -> StandardMaterial3D:
	if _panel_hardware == null: _panel_hardware = BayCeiling._hardware_material()
	return _panel_hardware

static func _source_retained_seats(parent: Node3D) -> void:
	var grouped := parent.get_node("seat_retained")
	parent.remove_child(grouped)
	grouped.free()
	for part: StringName in [&"left", &"right"]:
		var source := SeatRailComponent.build(part)
		source.name = "SeatRail_" + String(part)
		source.position = BayCeiling.FAILED_SEAT_CENTER
		parent.add_child(source)

static func _panel_materials(node: Node) -> void:
	if node is MeshInstance3D:
		var piece := node as MeshInstance3D
		if String(piece.name).contains("mount_head"):
			if _panel_hardware == null: _panel_hardware = BayCeiling._hardware_material()
			piece.material_override = _panel_hardware
		else:
			piece.material_override = BayCeilingMaterial.material_for_variant(&"intact")
	for child: Node in node.get_children(): _panel_materials(child)

static func _stage_box(parent: Node3D, position: Vector3, size: Vector3, role: StringName) -> void:
	var piece := MeshInstance3D.new()
	var mesh := BoxMesh.new()
	mesh.size = size
	piece.mesh = mesh
	piece.position = position
	parent.add_child(piece)
	Surfaces.bind(piece, role, _steel_frame())

static func isolate_fragment(assembly: Node3D) -> void:
	for child: Node in assembly.get_children():
		if child.name == &"ProofContext":
			for part: Node in child.get_children():
				if part is Node3D and not part is MeshInstance3D: (part as Node3D).visible = false
			continue
		_fragment_only(child)

static func _fragment_only(node: Node) -> void:
	if node is MeshInstance3D: (node as MeshInstance3D).visible = String(node.name).begins_with("fallen_fragment")
	for child: Node in node.get_children(): _fragment_only(child)

static func cache_size() -> int:
	return _packed.size()
