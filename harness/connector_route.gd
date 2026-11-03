extends HarnessRoute
## Layout-authored capture journey. Every change is ordinary Player input.

const AFT: StringName = &"C-001-LADDER"
var label_beats: Dictionary = {}
var white_beats: Array[String] = []

func opening() -> void:
	var source: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://scenarios/power-room.json"))
	replay_prefix(source.actions, int(source.beats.back().tick) + 2)
	beats = source.beats.duplicate(true)
	white_beats.assign(["power-active", "hall-white"])

func _center(index: int, deck: int = 14) -> Vector3:
	return player.game.layout.connector(ShipLayout.connector_id(deck, index)).bounds().get_center() * Vector3(1, 0, 1) + Vector3(0, player.game.layout.floor_y(deck), 0)

func hatch(id: StringName, from: Vector3, to: Vector3, prefix: String, white: bool = false) -> void:
	walk_to(from)
	look_at(player.game.layout.door(id).frame().origin)
	beat(prefix + "-closed")
	if white:
		white_beats.append(prefix + "-closed")
	var count := HatchResistance.schedule(player.game.run_seed, id).weights.size()
	for attempt: int in range(count):
		press()
		hold(6)
		if attempt == count / 2:
			beat(prefix + "-mid-crank")
			if white:
				white_beats.append(prefix + "-mid-crank")
	hold(48)
	if white:
		# The reverse face is inside the red connector; the approach stays white.
		walk_to(to)
		look_at(player.game.layout.door(id).frame().origin)
	beat(prefix + "-open")
	walk_to(to)

func read_label(id: StringName, name: String, white: bool = false, first: bool = false) -> void:
	var layout := player.game.layout
	var face := layout.face(id)
	var door := layout.door(face.door_id())
	var frame := door.frame() * face.label_frame()
	var approach := frame.origin + frame.basis.z * 1.7
	approach.y = layout.floor_y(door.deck_number())
	walk_to(approach)
	# Walking looks horizontally. Aim at the physical sign only after stopping.
	var delta := frame.origin - player.motion.eye(player.game)
	look_at(frame.origin, rad_to_deg(atan2(delta.y, Vector2(delta.x, delta.z).length())))
	beat(name + "-native")
	label_beats[name + "-native"] = {"id": String(id), "stage": "native"}
	hold((DisplayPerception.FIRST_HOLD + DisplayPerception.FIRST_RAMP / 2 if first else DisplayPerception.LATER_HOLD + DisplayPerception.LATER_RAMP / 2) - 2)
	beat(name + "-partial")
	label_beats[name + "-partial"] = {"id": String(id), "stage": "partial"}
	hold(DisplayPerception.FIRST_HOLD + DisplayPerception.FIRST_RAMP)
	beat(name + "-resolved")
	label_beats[name + "-resolved"] = {"id": String(id), "stage": "resolved"}
	if white:
		white_beats.append_array([name + "-native", name + "-partial", name + "-resolved"])

func refuse(id: StringName, from: Vector3) -> void:
	walk_to(from)
	look_at(player.game.layout.door(id).frame().origin)
	press()
	hold(10)

func mount() -> void:
	var landing := player.game.layout.well(AFT).landing(player.motion.deck()).origin
	walk_to(Vector3(landing.x, landing.y, -0.5))
	walk_to(landing)
	look_at(landing + Vector3(0, 0, -2))
	press()
	hold(24)
	assert(player.motion.mounted(), "real input mounts aft ladder")

func climb_to(deck: int, capture_mid: bool = false) -> void:
	var state := player.motion.locomotion.ladder_state()
	var distance := player.game.layout.floor_y(deck) - state.height()
	var steps := roundi(absf(distance) / (Ladder.CLIMB_SPEED * Sim.LOGICAL_TICK_SECS))
	for index: int in range(steps):
		step([{"type": "climb", "value": signf(distance)}])
		if capture_mid and index == steps / 2:
			look_at(player.motion.eye(player.game) + Vector3(0, 3, -2), 55)
			beat("mid-shaft")
	assert(absf(state.height() - player.game.layout.floor_y(deck)) < 1e-8, "route reaches exact landing")

func dismount(deck: int) -> void:
	press()
	hold(23)
	assert(player.motion.locomotion.mode() == Locomotion.Mode.WALK and player.motion.deck() == deck, "input dismounts onto requested deck")
	var center := _center(1, deck)
	var opening := player.game.layout.connector(ShipLayout.connector_id(deck, 1)).port_opening().origin
	walk_to(Vector3(opening.x, center.y, -0.5))
	walk_to(center)

func endpoint(deck: int) -> void:
	var layout := player.game.layout
	var spec := layout.connector(ShipLayout.connector_id(deck, 1))
	var center := _center(1, deck)
	for id: StringName in spec.hatch_ids():
		var door := layout.door(id)
		refuse(id, door.frame().origin + Vector3(signf(center.x - door.frame().origin.x) * 1.7, 0, 0))
		if id == spec.hatch_ids()[0]:
			var face_id: StringName
			for candidate: StringName in door.face_ids():
				if layout.face(candidate).source_space() == spec.id():
					face_id = candidate
			read_label(face_id, "d%02d-connector" % deck)
	refuse(layout.lift(spec.lift_id()).door_id(), center)
	walk_to(center)

func journey() -> void:
	opening()
	var layout := player.game.layout
	# Capture all four open D14 faces; only the aft well needs windowed travel.
	var fore := layout.connector(ShipLayout.connector_id(14, 0))
	var fore_center := _center(0)
	var inner := layout.door(fore.hatch_ids()[1])
	var outer := layout.door(fore.hatch_ids()[0])
	hatch(inner.id(), inner.frame().origin + Vector3(1.8, 0, 0), fore_center, "fore-inner", true)
	hatch(outer.id(), outer.frame().origin + Vector3(1.7, 0, 0), outer.frame().origin - Vector3(2, 0, 0), "fore-outer")
	walk_to(fore_center)
	walk_to(inner.frame().origin + Vector3(2, 0, 0))
	var aft := layout.connector(ShipLayout.connector_id(14, 1))
	inner = layout.door(aft.hatch_ids()[0])
	outer = layout.door(aft.hatch_ids()[1])
	var face_id: StringName
	for candidate: StringName in inner.face_ids():
		if layout.face(candidate).source_space() == &"D14-S-041":
			face_id = candidate
	read_label(face_id, "d14-label", true, true)
	hatch(inner.id(), inner.frame().origin - Vector3(1.8, 0, 0), _center(1), "x30", true)
	look_at(outer.frame().origin)
	beat("aft-connector")
	hatch(outer.id(), outer.frame().origin - Vector3(1.7, 0, 0), outer.frame().origin + Vector3(2, 0, 0), "x36")
	var side := layout.door(layout.section(&"D14-S-042").side_door_ids()[0])
	refuse(side.id(), side.frame().origin - side.frame().basis.z * 1.5)
	beat("section42-refusal")
	walk_to(outer.frame().origin + Vector3(2, 0, 0))
	walk_to(_center(1))
	mount()
	climb_to(1, true)
	dismount(1)
	endpoint(1)
	mount()
	climb_to(30)
	dismount(30)
	endpoint(30)
	mount()
	climb_to(14)
	dismount(14)
	look_at(inner.frame().origin)
	beat("back-d14")
