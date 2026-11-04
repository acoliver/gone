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
var _surface_bindings: Array[Surfaces.MotionBinding] = []

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
	var binding := Surfaces.MotionBinding.new(leaf)
	_collect_bound(leaf, binding.pieces)
	assert(not binding.pieces.is_empty(), "side/lift leaf has bound steel")
	view._surface_bindings.append(binding)
	return view

static func build(spec: ShipLayout.DoorSpec, fore_mask: int = 1, aft_mask: int = 1) -> DoorView:
	assert(spec.animation() == ShipLayout.AnimationRecipe.HINGE and spec.has_wheel(), "hinged wheel fixture required")
	var view := DoorView.new()
	view.name = String(spec.id())
	view._spec = spec
	view.transform = spec.frame()
	var masks: Array[int] = [fore_mask, aft_mask]
	view.add_child(HatchModel.surround_faces(spec, masks))
	view._hinge = Node3D.new()
	view._hinge.name = "Hinge"
	view._hinge.transform = spec.hinge_frame()
	view.add_child(view._hinge)
	var leaf := HatchModel.leaf(spec, masks, view._surface_bindings)
	view._hinge.add_child(leaf)
	view._wheel = leaf.get_node("Wheel")
	view._reverse_wheel = leaf.get_node("ReverseWheel")
	for side: int in range(2):
		var services := HatchServices.build(spec, side, masks[side])
		view.add_child(services)
		var panel := services.get_node("Control")
		services.remove_child(panel)
		panel.name = "ForePanel" if side == 0 else "AftPanel"
		view.add_child(panel)
	view.refresh_surfaces()
	return view

static func collar_surface(solid: ShipGeometry.SolidSpec, spec: ShipLayout.DoorSpec, fore_mask: int, aft_mask: int, material: Material = null, surface_frame: Surfaces.SurfaceFrame = null) -> Node3D:
	var group := Node3D.new()
	var arrays := (HatchModel.box_mesh(solid.size) if solid.section.is_empty() else HatchModel.solid_mesh(solid)).surface_get_arrays(0)
	var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
	var faces: Array[SurfaceTool] = [SurfaceTool.new(), SurfaceTool.new()]
	for face: SurfaceTool in faces:
		face.begin(Mesh.PRIMITIVE_TRIANGLES)
	# The sleeve between the wall and setback leaf is in the approach room.
	# Only its far end cap faces the other room, not half of every side wall.
	var approach := 0 if spec.hinge_frame().origin.z > ShipLayout.WALL / 2 else 1
	for index: int in range(vertices.size()):
		vertices[index] = ShipGeometry.hatch_wall_vertex(solid, vertices[index]) if solid.hatch_profile != null else ShipGeometry.hatch_frame_vertex(spec, solid, vertices[index])
	for triangle: int in range(0, indices.size(), 3):
		var a := vertices[indices[triangle]]
		var b := vertices[indices[triangle + 1]]
		var c := vertices[indices[triangle + 2]]
		var normal := (c - a).cross(b - a).normalized()
		var side := (0 if normal.z < 0 else 1) if absf(normal.z) > 0.5 else approach
		for vertex: Vector3 in [a, b, c]:
			faces[side].set_normal(normal)
			faces[side].add_vertex(vertex)
	var pose := spec.frame().affine_inverse() * solid.transform
	var binding := Surfaces.door_frame(spec, &"FRAME") if surface_frame == null else surface_frame
	var role := solid.material_role if material == null else &"wall"
	var surface := Surfaces.material(role) if material == null else material
	for side: int in range(2):
		var piece := HatchModel.mesh_piece(faces[side].commit(), pose, fore_mask if side == 0 else aft_mask, surface)
		Surfaces.bind(piece, role, binding)
		group.add_child(piece)
	return group

static func split_surface(solid: ShipGeometry.SolidSpec, frame: Transform3D, fore_mask: int, aft_mask: int, layout: ShipLayout = ShipLayout.authored().layout) -> Node3D:
	var material := Surfaces.material(Surfaces.role_for_solid(solid))
	var binding := Surfaces.frame_for_solid(layout, solid)
	if solid.hatch_profile != null:
		assert(frame == solid.hatch_profile.frame(), "profiled wall uses its portal frame")
		return collar_surface(solid, solid.hatch_profile, fore_mask, aft_mask, material, binding)
	var group := Node3D.new()
	var pose := frame.affine_inverse() * solid.transform
	for side: int in [-1, 1]:
		var half_size := solid.size
		half_size.z /= 2
		var half_pose := pose
		half_pose.origin += pose.basis.z * side * half_size.z / 2
		var piece := HatchModel.mesh_piece(HatchModel.box_mesh(half_size), half_pose, fore_mask if side < 0 else aft_mask, material)
		Surfaces.bind(piece, Surfaces.role_for_solid(solid), binding)
		group.add_child(piece)
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
	refresh_surfaces()

func refresh_surfaces() -> void:
	for binding: Surfaces.MotionBinding in _surface_bindings: binding.refresh()

static func _collect_bound(node: Node, pieces: Array[GeometryInstance3D]) -> void:
	if node is GeometryInstance3D and node.has_meta(&"surface_frame"): pieces.append(node)
	for child: Node in node.get_children(): _collect_bound(child, pieces)

func wheel_angle() -> float:
	return _angle

func door_id() -> StringName:
	return _spec.id()
