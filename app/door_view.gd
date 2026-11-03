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

static var _leaf_meshes: Dictionary = {}
static var _materials: Dictionary = {}
static var _cylinders: Dictionary = {}
static var _wheel_ring: TorusMesh

static func build(spec: ShipLayout.DoorSpec, fore_mask: int = 1, aft_mask: int = 1) -> DoorView:
	assert(spec.animation() == ShipLayout.AnimationRecipe.HINGE and spec.has_wheel(), "hinged wheel fixture required")
	var view := DoorView.new()
	view.name = String(spec.id())
	view._spec = spec
	view.transform = spec.frame()
	var frame := Node3D.new()
	frame.name = "Frame"
	view.add_child(frame)
	for solid: ShipGeometry.SolidSpec in ShipGeometry.hatch_frame_solids(spec):
		var piece := split_surface(solid, spec.frame(), fore_mask, aft_mask)
		if solid.id == StringName("%s/COAMING" % spec.id()):
			piece.name = "Coaming"
			view.add_child(piece)
		else:
			frame.add_child(piece)
	view._hinge = Node3D.new()
	view._hinge.name = "Hinge"
	view._hinge.transform = spec.hinge_frame()
	view.add_child(view._hinge)
	var leaf := Node3D.new()
	leaf.name = "Leaf"
	view._hinge.add_child(leaf)
	var size := Vector3(spec.aperture().x, spec.aperture().y - ShipGeometry.SILL_HEIGHT, ShipLayout.WALL / 2)
	for side: int in [-1, 1]:
		leaf.add_child(mesh_piece(_rounded_leaf(size), Transform3D(Basis(), Vector3(spec.aperture().x / 2, ShipGeometry.SILL_HEIGHT + size.y / 2, side * ShipLayout.WALL / 4)), fore_mask if side < 0 else aft_mask))
	view._wheel = _wheel_mesh()
	view._wheel.name = "Wheel"
	view._wheel.position = Vector3(spec.aperture().x / 2, spec.aperture().y / 2, -0.19)
	view._hinge.add_child(view._wheel)
	view._reverse_wheel = _wheel_mesh()
	view._reverse_wheel.name = "ReverseWheel"
	view._reverse_wheel.position = Vector3(spec.aperture().x / 2, spec.aperture().y / 2, 0.19)
	view._reverse_wheel.rotation.y = PI
	view._hinge.add_child(view._reverse_wheel)
	Lighting.mesh_layers(view._wheel, fore_mask)
	Lighting.mesh_layers(view._reverse_wheel, aft_mask)
	var hinges := Node3D.new()
	hinges.name = "Hinges"
	view.add_child(hinges)
	for height: float in [0.4, spec.aperture().y - 0.4]:
		var cylinder := _cylinder(0.075, 0.24)
		hinges.add_child(mesh_piece(cylinder, Transform3D(Basis(), Vector3(-spec.aperture().x / 2, height, ShipLayout.WALL / 2)), fore_mask | aft_mask))
	var lugs := Node3D.new()
	lugs.name = "Lugs"
	view._hinge.add_child(lugs)
	for side: int in [-1, 1]:
		for height: float in [0.35, spec.aperture().y / 2, spec.aperture().y - 0.35]:
			for face: int in [-1, 1]:
				lugs.add_child(mesh_piece(Hallway._box_mesh(Vector3(0.16, 0.10, 0.065)), Transform3D(Basis(), Vector3(0.09 if side < 0 else spec.aperture().x - 0.09, height, face * 0.125)), fore_mask if face < 0 else aft_mask))
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

static func _wheel_mesh() -> Node3D:
	var wheel := Node3D.new()
	if _wheel_ring == null:
		_wheel_ring = TorusMesh.new()
		_wheel_ring.inner_radius = 0.18
		_wheel_ring.outer_radius = 0.22
	wheel.add_child(mesh_piece(_wheel_ring, Transform3D(Basis(Vector3.RIGHT, PI / 2), Vector3.ZERO), 1))
	var axle := _cylinder(0.055, 0.20)
	wheel.add_child(mesh_piece(axle, Transform3D(Basis(Vector3.RIGHT, PI / 2), Vector3(0, 0, -0.035)), 1))
	for angle: float in [0, TAU / 3, 2 * TAU / 3]:
		wheel.add_child(mesh_piece(Hallway._box_mesh(Vector3(0.38, 0.027, 0.035)), Transform3D(Basis(Vector3.BACK, angle), Vector3.ZERO), 1))
	return wheel

static func _rounded_leaf(size: Vector3) -> ArrayMesh:
	if _leaf_meshes.has(size):
		return _leaf_meshes[size]
	var outline := PackedVector2Array()
	var radius := 0.13
	for corner: int in range(4):
		var angle := PI / 2 * corner
		var center := Vector2((size.x / 2 - radius) * (1 if corner in [0, 3] else -1), (size.y / 2 - radius) * (1 if corner < 2 else -1))
		for segment: int in range(7):
			var theta := angle + segment * PI / 12
			outline.append(center + Vector2(cos(theta), sin(theta)) * radius)
	var tool := SurfaceTool.new()
	tool.begin(Mesh.PRIMITIVE_TRIANGLES)
	for index: int in range(outline.size()):
		var next := (index + 1) % outline.size()
		var a := Vector3(outline[index].x, outline[index].y, -size.z / 2)
		var b := Vector3(outline[next].x, outline[next].y, -size.z / 2)
		var c := a + Vector3(0, 0, size.z)
		var d := b + Vector3(0, 0, size.z)
		for point: Vector3 in [Vector3(0, 0, -size.z / 2), b, a, Vector3(0, 0, size.z / 2), c, d, a, b, c, b, d, c]:
			tool.add_vertex(point)
	tool.generate_normals()
	var mesh := tool.commit()
	_leaf_meshes[size] = mesh
	return mesh

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
