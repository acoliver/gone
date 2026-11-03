class_name Hatch
extends Node3D
## The bay uses the shared hatch dressing at its authored ajar leaf pose.
## The original solid recipe still owns collision and the retract/slide origin.

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
	var solids := Placement.hatch_solids()
	var aperture := Vector2(ShipLayout.HATCH_WIDTH, ShipLayout.HATCH_HEIGHT)
	var masks: Array[int] = [1, 1]
	var orientation := Basis(Vector3.BACK, Vector3.UP, Vector3.LEFT)
	var frame := Node3D.new()
	frame.name = "Frame"
	frame.transform = Transform3D(orientation, Vector3(ShipGeometry.HATCH_FRAME_X, 0, 0))
	HatchModel.add_faces(frame, &"frame", aperture, masks, false)
	hatch.add_child(frame)
	var sill := solids[3]
	var coaming := DoorView.mesh_piece(_box_mesh(sill.size), sill.transform, 1, HatchModel.steel())
	coaming.name = "Coaming"
	hatch.add_child(coaming)
	var solid := solids[HATCH_FRAME_PIECES]
	hatch._door_piece = MeshInstance3D.new()
	hatch._door_piece.name = "MovingLeaf"
	hatch._door_piece.transform = solid.transform
	hatch._door_base = solid.center
	hatch.add_child(hatch._door_piece)
	var leaf := HatchModel.leaf(aperture, masks)
	leaf.transform = Transform3D(orientation, Vector3(0, -ShipGeometry.DOOR_HEIGHT / 2, -aperture.x / 2))
	hatch._door_piece.add_child(leaf)
	var hinges := Node3D.new()
	hinges.name = "Hinges"
	hinges.transform = frame.transform * Transform3D(Basis(), Vector3(-aperture.x / 2, 0, ShipLayout.WALL / 2))
	HatchModel.add_faces(hinges, &"hinges", aperture, masks, true)
	hatch.add_child(hinges)
	for side: int in [-1, 1]:
		var panel := DoorView.control_panel()
		panel.name = "ForePanel" if side < 0 else "AftPanel"
		panel.transform = frame.transform * Transform3D(Basis(Vector3.UP, PI) if side < 0 else Basis(), Vector3(aperture.x / 2 + 0.38, 1.25, -0.08 if side < 0 else ShipLayout.WALL + 0.08))
		hatch.add_child(panel)
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
