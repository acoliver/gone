class_name Hatch
extends Node3D
## The jammed hatch on the +X short wall, ported from gone_app
## geometry.rs (spawn_hatch): a frame protruding from the wall around a
## recessed door slab that leans ajar into the room. Since the hallway
## milestone the slab is no longer static: it still spawns at its
## authored ajar pose, and the player rig projects the sim's
## deterministic opening offset onto it every tick. All five pieces
## spawn verbatim from Placement.hatch_solids, the same data the
## collider set is derived from.

const HATCH_FRAME_SHADE: float = 0.33
const HATCH_DOOR_SHADE: float = 0.38

## How many of the hatch group's pieces are frame (posts, lintel, sill);
## the last piece is the ajar door slab.
const HATCH_FRAME_PIECES: int = 4

static var _box_cache: Dictionary = {}

var _door_piece: MeshInstance3D = null
var _door_base: Vector3 = Vector3.ZERO

static func build() -> Hatch:
	var hatch := Hatch.new()
	var frame_material := _flat_grey(HATCH_FRAME_SHADE)
	var door_material := _flat_grey(HATCH_DOOR_SHADE)
	var solids := Placement.hatch_solids()
	for index: int in range(solids.size()):
		var material := frame_material
		if index >= HATCH_FRAME_PIECES:
			material = door_material
		var piece := MeshInstance3D.new()
		piece.mesh = _box_mesh(solids[index].size)
		piece.material_override = material
		piece.position = solids[index].center
		piece.quaternion = solids[index].rotation
		if index >= HATCH_FRAME_PIECES:
			hatch._door_piece = piece
			hatch._door_base = solids[index].center
		hatch.add_child(piece)
	return hatch

## The ajar door slab's mesh piece, the node the player rig animates.
func door_piece() -> MeshInstance3D:
	return _door_piece

## Project the sim's deterministic opening offset onto the door slab,
## from its authored ajar base pose.
func set_door_offset(offset: Vector3) -> void:
	if _door_piece == null:
		return
	_door_piece.position = _door_base + offset

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
