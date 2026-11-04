class_name RoomGeometry
extends Node3D
## Room shell and separate torn-ceiling dressing. Architectural surfaces use
## Surfaces; tray and wire materials remain local to their presentation.

const TRAY_SHADE: float = 0.24
const WIRE_SHADE: float = 0.18

static var _box_cache: Dictionary = {}

## The shell's +X wall index: the one wall the hallway's doorway
## pierces when p_open_east_wall is set — the hallway module authors
## and renders the pierced replacement pieces.
const EAST_WALL_INDEX: int = 5

static func build(p_open_east_wall := false, layout: ShipLayout = ShipLayout.authored().layout) -> RoomGeometry:
	var room := RoomGeometry.new()
	var shell := Placement.room_shell(p_open_east_wall)
	assert(
		shell[EAST_WALL_INDEX].center.x > 0.0,
		"the east wall's authored shell index holds"
	)
	for index: int in range(shell.size()):
		if p_open_east_wall and index == EAST_WALL_INDEX:
			continue
		var material := wall_material()
		if index == 0:
			material = floor_material()
		elif index == 1:
			material = ceiling_material()
		var piece := _box_instance(shell[index], material)
		Surfaces.bind_solid(piece, layout, shell[index])
		room.add_child(piece)
	room.add_child(_build_ceiling_damage())
	return room

static func floor_material() -> ShaderMaterial:
	return Surfaces.material(&"floor")

static func ceiling_material() -> ShaderMaterial:
	return Surfaces.material(&"ceiling")

static func wall_material() -> ShaderMaterial:
	return Surfaces.material(&"wall")

## The torn ceiling: cable tray runs concentrated over the room center,
## each tipped off level, with hanging wire loops beneath them.
static func _build_ceiling_damage() -> Node3D:
	var damage := Node3D.new()
	damage.name = "CeilingDamage"
	var tray_material := _flat_grey(TRAY_SHADE)
	var wire_material := _flat_grey(WIRE_SHADE)
	for placement: Placement.SolidPlacement in Placement.cable_trays():
		damage.add_child(_box_instance(placement, tray_material))
	for loop: Placement.WireLoop in Placement.wire_loops():
		var mesh := TorusMesh.new()
		mesh.inner_radius = Placement.WIRE_INNER_RADIUS
		mesh.outer_radius = Placement.WIRE_OUTER_RADIUS
		var wire := MeshInstance3D.new()
		wire.mesh = mesh
		wire.material_override = wire_material
		wire.position = loop.center
		wire.quaternion = loop.rotation
		damage.add_child(wire)
	return damage

static func _box_instance(placement: Placement.SolidPlacement, material: Material) -> MeshInstance3D:
	var instance := MeshInstance3D.new()
	instance.mesh = _box_mesh(placement.size)
	instance.material_override = material
	instance.position = placement.center
	instance.quaternion = placement.rotation
	return instance

static func _box_mesh(size: Vector3) -> BoxMesh:
	if _box_cache.has(size):
		return _box_cache[size]
	var mesh := BoxMesh.new()
	mesh.size = size
	_box_cache[size] = mesh
	return mesh

static func _flat_grey(shade: float) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = Color(shade, shade, shade)
	material.roughness = 0.95
	return material
