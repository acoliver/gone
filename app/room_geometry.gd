class_name RoomGeometry
extends Node3D
## Room shell with shared architectural surface materials.

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
	return room

static func floor_material() -> ShaderMaterial:
	return Surfaces.material(&"floor")

static func ceiling_material() -> ShaderMaterial:
	return Surfaces.material(&"ceiling")

static func wall_material() -> ShaderMaterial:
	return Surfaces.material(&"wall")

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
