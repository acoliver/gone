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
		var suffix := String(solid.id).trim_prefix("%s/" % spec.id())
		if suffix in ["COAMING", "FRAME/RIGHT", "FRAME/TOP"]:
			var piece := collar_surface(solid, spec, fore_mask, aft_mask)
			piece.name = {"COAMING": "Coaming", "FRAME/RIGHT": "LatchJamb", "FRAME/TOP": "Lintel"}[suffix]
			view.add_child(piece)
	view._hinge = Node3D.new()
	view._hinge.name = "Hinge"
	view._hinge.transform = spec.hinge_frame()
	view.add_child(view._hinge)
	var leaf := HatchModel.leaf(spec, masks)
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
		var panel := HatchModel.control_panel()
		panel.name = "ForePanel" if side < 0 else "AftPanel"
		panel.position = Vector3(spec.aperture().x / 2 + 0.38, 1.25, -0.08 if side < 0 else ShipLayout.WALL + 0.08)
		if side < 0:
			panel.rotation.y = PI
		Lighting.mesh_layers(panel, fore_mask if side < 0 else aft_mask)
		view.add_child(panel)
	return view

static func collar_surface(solid: ShipGeometry.SolidSpec, spec: ShipLayout.DoorSpec, fore_mask: int, aft_mask: int) -> Node3D:
	var group := Node3D.new()
	var arrays := HatchModel.box_mesh(solid.size).surface_get_arrays(0)
	var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
	var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
	var faces: Array[SurfaceTool] = [SurfaceTool.new(), SurfaceTool.new()]
	for face: SurfaceTool in faces:
		face.begin(Mesh.PRIMITIVE_TRIANGLES)
	# The sleeve between the wall and setback leaf is in the approach room.
	# Only its far end cap faces the other room, not half of every side wall.
	var approach := 0 if spec.hinge_frame().origin.z > ShipLayout.WALL / 2 else 1
	for index: int in indices:
		var normal := normals[index]
		var side := (0 if normal.z < 0 else 1) if absf(normal.z) > 0.5 else approach
		faces[side].set_normal(normal)
		faces[side].add_vertex(vertices[index])
	var pose := spec.frame().affine_inverse() * solid.transform
	for side: int in range(2):
		group.add_child(HatchModel.mesh_piece(faces[side].commit(), pose, fore_mask if side == 0 else aft_mask))
	return group

static func split_surface(solid: ShipGeometry.SolidSpec, frame: Transform3D, fore_mask: int, aft_mask: int) -> Node3D:
	var group := Node3D.new()
	var pose := frame.affine_inverse() * solid.transform
	var material := RoomGeometry.wall_material() if solid.material_role == &"wall" else HatchModel.material(HatchModel.DOOR_SHADE)
	for side: int in [-1, 1]:
		var half_size := solid.size
		half_size.z /= 2
		var half_pose := pose
		half_pose.origin += pose.basis.z * side * half_size.z / 2
		group.add_child(HatchModel.mesh_piece(HatchModel.box_mesh(half_size), half_pose, fore_mask if side < 0 else aft_mask, material))
	return group

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
		_hinge.basis = Basis(Vector3.UP, snapshot.open_radians * snapshot.leaf_fraction)
		_wheel.rotation.z = deg_to_rad(_angle)
		_reverse_wheel.rotation.z = -deg_to_rad(_angle)

func wheel_angle() -> float:
	return _angle

func door_id() -> StringName:
	return _spec.id()
