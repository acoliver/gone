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

## Minimal reusable hatch fixture, also used by connector assembly in S06.
static func build(spec: ShipLayout.DoorSpec) -> DoorView:
	assert(spec.animation() == ShipLayout.AnimationRecipe.HINGE and spec.has_wheel(), "hinged wheel fixture required")
	var view := DoorView.new()
	view._spec = spec
	view.transform = spec.frame()
	view._hinge = Node3D.new()
	view._hinge.transform = spec.hinge_frame()
	view.add_child(view._hinge)
	var leaf := MeshInstance3D.new()
	var mesh := BoxMesh.new()
	mesh.size = Vector3(spec.aperture().x, spec.aperture().y, ShipLayout.WALL)
	leaf.mesh = mesh
	leaf.position = Vector3(spec.aperture().x / 2.0, spec.aperture().y / 2.0, 0)
	leaf.material_override = Hatch._flat_grey(Hatch.HATCH_DOOR_SHADE)
	view._hinge.add_child(leaf)
	view._wheel = Node3D.new()
	view._wheel.position = Vector3(spec.aperture().x / 2.0, 1.2, -0.15)
	view._hinge.add_child(view._wheel)
	var ring := MeshInstance3D.new()
	var torus := TorusMesh.new()
	torus.inner_radius = 0.14
	torus.outer_radius = 0.18
	ring.mesh = torus
	ring.rotation.x = PI / 2.0
	ring.material_override = leaf.material_override
	view._wheel.add_child(ring)
	for angle: float in [0, TAU / 3.0, 2.0 * TAU / 3.0]:
		var spoke := MeshInstance3D.new()
		var spoke_mesh := BoxMesh.new()
		spoke_mesh.size = Vector3(0.30, 0.025, 0.025)
		spoke.mesh = spoke_mesh
		spoke.rotation.z = angle
		spoke.material_override = leaf.material_override
		view._wheel.add_child(spoke)
	view._reverse_wheel = view._wheel.duplicate() as Node3D
	view._reverse_wheel.position.z = 0.15
	view._reverse_wheel.rotation.y = PI
	view._hinge.add_child(view._reverse_wheel)
	return view

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
