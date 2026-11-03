class_name LabelAttention
extends RefCounted
## Spatially indexed face state survives presentation unloads.

class Face:
	extends RefCounted
	var deck: int
	var space: StringName
	var frame: Transform3D
	var anchor: Transform3D
	var size: Vector2
	var perception: DisplayPerception
	var loaded: bool = true

var _memory: DisplayPerception.Memory
var _faces: Dictionary = {}
var _index: Dictionary = {}
var _decay: Dictionary = {}
var last_ticked_count: int = 0

func _init(memory: DisplayPerception.Memory) -> void:
	_memory = memory

static func _cell(position: Vector3) -> Vector3i:
	return Vector3i((position / DisplayPerception.ATTENTION_RANGE).floor())

func register_face(id: StringName, deck: int, space: StringName, frame: Transform3D, size: Vector2) -> DisplayPerception:
	if _faces.has(id):
		var existing: Face = _faces[id]
		assert(existing.deck == deck and existing.space == space and existing.anchor == frame and existing.size == size, "face identity survives reload")
		existing.loaded = true
		return existing.perception
	var face := Face.new()
	face.deck = deck
	face.space = space
	face.frame = frame
	face.anchor = frame
	face.size = size
	face.perception = DisplayPerception.new(_memory)
	_faces[id] = face
	if not _index.has(deck):
		_index[deck] = {}
	var cell := _cell(frame.origin)
	if not _index[deck].has(cell):
		_index[deck][cell] = []
	_index[deck][cell].append(id)
	return face.perception

func state(id: StringName) -> DisplayPerception:
	return _faces[id].perception

func move_face(id: StringName, frame: Transform3D) -> void:
	var face: Face = _faces[id]
	if face.frame == frame: return
	var before := _cell(face.frame.origin)
	var after := _cell(frame.origin)
	face.frame = frame
	if before == after: return
	_index[face.deck][before].erase(id)
	if _index[face.deck][before].is_empty(): _index[face.deck].erase(before)
	if not _index[face.deck].has(after): _index[face.deck][after] = []
	_index[face.deck][after].append(id)

func unload(id: StringName) -> void:
	_faces[id].loaded = false

func load_face(id: StringName) -> void:
	_faces[id].loaded = true

func decaying_count() -> int:
	return _decay.size()

func tick(deck: int, eye: Vector3, forward: Vector3, solids: Array[AABB], oriented: Array[ShipGeometry.SightBox] = []) -> void:
	var attending: Dictionary = {}
	if _index.has(deck):
		var cell := _cell(eye)
		for x: int in range(-1, 2):
			for y: int in range(-1, 2):
				for z: int in range(-1, 2):
					for id: StringName in _index[deck].get(cell + Vector3i(x, y, z), []):
						var face: Face = _faces[id]
						if face.loaded and _attends(face, eye, forward, solids, oriented):
							attending[id] = true
	var work := attending.duplicate()
	work.merge(_decay)
	var ordered := work.keys()
	ordered.sort()
	last_ticked_count = ordered.size()
	for id: StringName in ordered:
		var perception := state(id)
		var attend := attending.has(id)
		perception.tick(attend)
		if attend or perception.perceive > 0:
			_decay[id] = true
		else:
			_decay.erase(id)

static func _attends(face: Face, eye: Vector3, forward: Vector3, solids: Array[AABB], oriented: Array[ShipGeometry.SightBox] = []) -> bool:
	var frame := face.frame
	if not DisplayPerception.attends(eye, forward, frame.origin, frame.basis.x * face.size.x / 2, frame.basis.y * face.size.y / 2, frame.basis.z):
		return false
	var distance := (frame.origin - eye).dot(frame.basis.z) / forward.dot(frame.basis.z)
	var end := eye + forward * distance
	for solid: AABB in solids:
		var hit := Interactions.segment_hit(eye, end, solid)
		if hit >= 0 and hit < 1.0 - 0.00001:
			return false
	for solid: ShipGeometry.SightBox in oriented:
		var hit := Interactions.segment_hit(solid.inverse * eye, solid.inverse * end, solid.bounds)
		if hit >= 0 and hit < 1.0 - 0.00001:
			return false
	return true
