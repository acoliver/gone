class_name DoorView
extends Node3D
## Projects a persistent snapshot. It never advances a wheel or an animation.

var _spec: ShipLayout.DoorSpec
var _hinge: Node3D
var _wheel: Node3D
var _reverse_wheel: Node3D
var _leaf: Node3D
var _leaf_base := Vector3.ZERO
var _offset_sink: Callable
var _angle: float = 0.0

static func adapter(spec: ShipLayout.DoorSpec, sink: Callable) -> DoorView:
	var view := DoorView.new()
	view._spec = spec
	view._offset_sink = sink
	return view

static func bind_leaf(spec: ShipLayout.DoorSpec, leaf: Node3D) -> DoorView:
	var view := DoorView.new()
	view._spec = spec
	view._leaf = leaf
	view._leaf_base = leaf.position
	return view

static var _materials: Dictionary = {}
static var _cylinders: Dictionary = {}

static func build(spec: ShipLayout.DoorSpec, fore_mask: int = 1, aft_mask: int = 1) -> DoorView:
	assert(spec.animation() == ShipLayout.AnimationRecipe.HINGE and spec.has_wheel(), "hinged wheel fixture required")
	var view := DoorView.new()
	view.name = String(spec.id())
	view._spec = spec
	view.transform = spec.frame()
	var frame := Node3D.new()
	frame.name = "Frame"
	view.add_child(frame)
	var masks: Array[int] = [fore_mask, aft_mask]
	HatchModel.add_faces(frame, &"frame", spec.aperture(), masks, false)
	for solid: ShipGeometry.SolidSpec in ShipGeometry.hatch_frame_solids(spec):
		if solid.id == StringName("%s/COAMING" % spec.id()):
			var piece := split_surface(solid, spec.frame(), fore_mask, aft_mask)
			piece.name = "Coaming"
			view.add_child(piece)
	view._hinge = Node3D.new()
	view._hinge.name = "Hinge"
	view._hinge.transform = spec.hinge_frame()
	view.add_child(view._hinge)
	var leaf := HatchModel.leaf(spec.aperture(), masks)
	view._hinge.add_child(leaf)
	view._wheel = leaf.get_node("Wheel")
	view._reverse_wheel = leaf.get_node("ReverseWheel")
	var hinges := Node3D.new()
	hinges.name = "Hinges"
	view.add_child(hinges)
	hinges.transform = spec.hinge_frame()
	HatchModel.add_faces(hinges, &"hinges", spec.aperture(), masks, true)
	# Both faces have an unpowered button and reader, without emissive material.
	for side: int in [-1, 1]:
		var panel := control_panel()
		panel.name = "ForePanel" if side < 0 else "AftPanel"
		panel.position = Vector3(spec.aperture().x / 2 + 0.38, 1.25, -0.08 if side < 0 else ShipLayout.WALL + 0.08)
		if side < 0:
			panel.rotation.y = PI
		Lighting.mesh_layers(panel, fore_mask if side < 0 else aft_mask)
		view.add_child(panel)
	return view

static func split_surface(solid: ShipGeometry.SolidSpec, frame: Transform3D, fore_mask: int, aft_mask: int) -> Node3D:
	var group := Node3D.new()
	var pose := frame.affine_inverse() * solid.transform
	var material := RoomGeometry.wall_material() if solid.material_role == &"wall" else _material(Hatch.HATCH_DOOR_SHADE)
	for side: int in [-1, 1]:
		var half_size := solid.size
		half_size.z /= 2
		var half_pose := pose
		half_pose.origin += pose.basis.z * side * half_size.z / 2
		group.add_child(mesh_piece(Hallway._box_mesh(half_size), half_pose, fore_mask if side < 0 else aft_mask, material))
	return group

static func mesh_piece(mesh: Mesh, pose: Transform3D, mask: int, material: Material = null) -> MeshInstance3D:
	var piece := MeshInstance3D.new()
	piece.mesh = mesh
	piece.transform = pose
	piece.layers = mask
	piece.material_override = _material(Hatch.HATCH_DOOR_SHADE) if material == null else material
	return piece

static func control_panel() -> Node3D:
	var panel := Node3D.new()
	panel.add_child(mesh_piece(Hallway._box_mesh(Vector3(0.19, 0.34, 0.07)), Transform3D.IDENTITY, 1, _material(0.12)))
	var button := _cylinder(0.036, 0.025)
	var piece := mesh_piece(button, Transform3D(Basis(Vector3.RIGHT, PI / 2), Vector3(0, 0.07, 0.045)), 1, _material(0.055))
	piece.name = "Button"
	panel.add_child(piece)
	var reader := mesh_piece(Hallway._box_mesh(Vector3(0.12, 0.018, 0.01)), Transform3D(Basis(), Vector3(0, -0.075, 0.04)), 1, _material(0.015))
	reader.name = "CardReader"
	panel.add_child(reader)
	return panel

static func _material(shade: float) -> StandardMaterial3D:
	if not _materials.has(shade):
		_materials[shade] = Hatch._flat_grey(shade)
	return _materials[shade]

static func _cylinder(radius: float, height: float) -> CylinderMesh:
	var key := Vector2(radius, height)
	if not _cylinders.has(key):
		var mesh := CylinderMesh.new()
		mesh.top_radius = radius
		mesh.bottom_radius = radius
		mesh.height = height
		_cylinders[key] = mesh
	return _cylinders[key]

func label_leaf() -> Node3D:
	return _hinge.get_node("Leaf") if _hinge != null else _leaf

func present(snapshot: Doors.Snapshot) -> void:
	assert(snapshot.id == _spec.id(), "view snapshot belongs to its door")
	_angle = snapshot.wheel_angle + snapshot.refusal_offset
	if _offset_sink.is_valid():
		_offset_sink.call(snapshot.offset)
	if _leaf != null:
		_leaf.position = _leaf_base + _spec.frame().basis.z * (snapshot.shudder * 0.012)
	if _hinge != null:
		_hinge.basis = Basis(Vector3.UP, _spec.swing_radians() * snapshot.leaf_fraction)
		_wheel.rotation.z = deg_to_rad(_angle)
		_reverse_wheel.rotation.z = -deg_to_rad(_angle)

func wheel_angle() -> float:
	return _angle

func door_id() -> StringName:
	return _spec.id()
