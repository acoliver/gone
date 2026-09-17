class_name RoomGeometry
extends Node3D
## Greybox room shell and torn-ceiling dressing, ported from gone_app
## geometry.rs (spawn_room_shell, spawn_ceiling_damage). Every mesh is an
## engine primitive spawned verbatim from the pure placements in
## Placement; flat grey materials are shared per shade, box meshes cached
## per size.

const FLOOR_SHADE: float = 0.32
const WALL_SHADE: float = 0.4
const CEILING_SHADE: float = 0.26
const TRAY_SHADE: float = 0.24
const WIRE_SHADE: float = 0.18

static var _box_cache: Dictionary = {}

static func build() -> RoomGeometry:
	var room := RoomGeometry.new()
	var floor_material := _flat_grey(FLOOR_SHADE)
	var ceiling_material := _flat_grey(CEILING_SHADE)
	var wall_material := _flat_grey(WALL_SHADE)
	var shell := Placement.room_shell()
	for index: int in range(shell.size()):
		var material := wall_material
		if index == 0:
			material = floor_material
		elif index == 1:
			material = ceiling_material
		room.add_child(_box_instance(shell[index], material))
	room.add_child(_build_ceiling_damage())
	return room

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

static func _box_instance(placement: Placement.SolidPlacement, material: StandardMaterial3D) -> MeshInstance3D:
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
