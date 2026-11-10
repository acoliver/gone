class_name SeatRailComponent
extends RefCounted
## Shared lower-seat source. Origin is the bearing top; length +X, +Y up.

const DIR := "res://assets/props/stasis-wiring/seat-rail/"
const PARTS := [&"full", &"left", &"middle", &"right"]
static var _scenes: Dictionary = {}
static var _material: Material

static func build(part: StringName = &"full") -> Node3D:
	assert(PARTS.has(part), "known shared seat rail source part")
	if not _scenes.has(part):
		var packed := load(DIR + String(part) + ".glb") as PackedScene
		assert(packed != null, "shared seat rail export must import")
		_scenes[part] = packed
	var result := (_scenes[part] as PackedScene).instantiate() as Node3D
	_bind(result)
	return result

static func material() -> Material:
	if _material == null:
		var source := load(DIR + "full.glb") as PackedScene
		assert(source != null, "shared seat rail material source must import")
		var instance := source.instantiate()
		_material = _find_material(instance)
		instance.free()
		assert(_material != null, "seat rail source contains its image-derived PBR material")
	return _material

static func _find_material(node: Node) -> Material:
	if node is MeshInstance3D: return (node as MeshInstance3D).mesh.surface_get_material(0)
	for child: Node in node.get_children():
		var found := _find_material(child)
		if found != null: return found
	return null

static func _bind(node: Node) -> void:
	if node is MeshInstance3D: (node as MeshInstance3D).material_override = material()
	for child: Node in node.get_children(): _bind(child)

static func floor_pose() -> Transform3D:
	var file := FileAccess.open(DIR + "manifest.json", FileAccess.READ)
	assert(file != null, "measured floor contact pose exists")
	var data: Dictionary = JSON.parse_string(file.get_as_text())
	var rows: Array = data.floor_pose_bay_local
	return Transform3D(Basis(Vector3(rows[0][0],rows[1][0],rows[2][0]),Vector3(rows[0][1],rows[1][1],rows[2][1]),Vector3(rows[0][2],rows[1][2],rows[2][2])),Vector3(rows[0][3],rows[1][3],rows[2][3]))
