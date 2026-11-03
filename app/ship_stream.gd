class_name ShipStream
extends Node
## Presentation residency only. A render frame constructs at most one room;
## simulation and collider availability never depend on this queue.

var _scene: ShipScene
var _game: Game
var _parent: Node3D
var _rooms: Dictionary = {}
var _shafts: Dictionary = {}
var _wanted: Array[StringName] = []
var _queue: Array[StringName] = []
var constructed_rooms: int = 0
var last_build_usec: int = 0
var _opening_shown: bool = true

static func build(scene: ShipScene, game: Game, parent: Node3D) -> ShipStream:
	var stream := ShipStream.new()
	stream.name = "ShipStream"
	stream._scene = scene
	stream._game = game
	stream._parent = parent
	return stream

func ensure_shaft(well_id: StringName) -> void:
	if _shafts.has(well_id):
		return
	var shaft := LadderShaft.build(_game.layout, _game.layout.well(well_id))
	_parent.add_child(shaft)
	_shafts[well_id] = shaft
	var index := _game.layout.well_ids().find(well_id)
	if _scene.connector_prepared(ShipLayout.connector_id(14, index)):
		shaft.detail_resident(14, true)

func focus(well_id: StringName, deck: int) -> void:
	ensure_shaft(well_id)
	var index := _game.layout.well_ids().find(well_id)
	var wanted: Array[StringName] = []
	for d: int in range(maxi(1, deck - 2), mini(30, deck + 2) + 1):
		if d != 14:
			wanted.append(ShipLayout.connector_id(d, index))
	if wanted == _wanted:
		return
	_wanted = wanted
	for id: StringName in _rooms.keys():
		if id not in _wanted:
			var spec := _game.layout.connector(id)
			_scene.remove_remote(spec, _rooms[id])
			_shafts[spec.well_id()].detail_resident(spec.deck_number(), false)
			_rooms.erase(id)
	_queue.clear()
	# Build the central deck first, then the nearest neighbors.
	var pending := _wanted.duplicate()
	pending.sort_custom(func(a: StringName, b: StringName) -> bool:
		var da := absi(_game.layout.connector(a).deck_number() - deck)
		var db := absi(_game.layout.connector(b).deck_number() - deck)
		return String(a) < String(b) if da == db else da < db)
	for id: StringName in pending:
		if not _rooms.has(id):
			_queue.append(id)

func update(motion: PlayerMotion) -> void:
	if motion.locomotion == null:
		return
	if motion.mounted():
		var ladder := motion.locomotion.ladder_state()
		focus(ladder.well_id(), ladder.nearest_landing())
	else:
		var foot := motion.capsule().foot
		for id: StringName in (_game.layout.deck(motion.deck()).connector_ids() if foot.z < -1.0 else []):
			var spec := _game.layout.connector(id)
			if foot.z < -1.0 and absf(foot.x - spec.port_opening().origin.x) < 1.2:
				focus(spec.well_id(), motion.deck())
	var show := motion.locomotion.ladder_state().nearest_landing() == 14 if motion.mounted() else motion.deck() == 14
	if show != _opening_shown:
		_opening_shown = show
		_scene.set_opening_visible(show)

func _process(_delta: float) -> void:
	build_next()

func build_next() -> void:
	if _queue.is_empty():
		return
	var start := Time.get_ticks_usec()
	var id: StringName = _queue.pop_front()
	var spec := _game.layout.connector(id)
	_rooms[id] = _scene.build_remote(spec)
	_shafts[spec.well_id()].detail_resident(spec.deck_number(), true)
	constructed_rooms += 1
	last_build_usec = Time.get_ticks_usec() - start

func resident_ids() -> Array[StringName]:
	var ids: Array[StringName] = []
	ids.assign(_rooms.keys())
	ids.sort_custom(func(a: StringName, b: StringName) -> bool: return String(a) < String(b))
	return ids

func pending_count() -> int:
	return _queue.size()

func shaft_count() -> int:
	return _shafts.size()

func remote_light_count() -> int:
	return _rooms.size() * 3

func room(id: StringName) -> Node3D:
	return _rooms[id]

func show_d14_shell(well_id: StringName, show: bool) -> void:
	if _shafts.has(well_id):
		var index := _game.layout.well_ids().find(well_id)
		_shafts[well_id].detail_resident(14, not show and _scene.connector_prepared(ShipLayout.connector_id(14, index)))
