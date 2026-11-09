extends SimTestCase

func test_room_frame_doorway_and_far_corners_are_pinned() -> void:
	assert_vec3_equal(QuartersLayout.to_world(Vector3(4, 0, 0)), Vector3(45, -11, 1.7), "room-side doorway centre")
	assert_vec3_equal(QuartersLayout.to_world(Vector3(0, 0, 6)), Vector3(49, -11, 7.7), "far left corner as viewed from doorway")
	assert_vec3_equal(QuartersLayout.to_world(Vector3(8, 0, 6)), Vector3(41, -11, 7.7), "far right corner")
	assert_close(QuartersLayout.from_world(Vector3(42.8, -9.35, 3.7)), Vector3(6.2, 1.65, 2), "inverse maps console approach")
	var layout := ShipLayout.authored().layout
	assert_vec3_equal(layout.door(QuartersLayout.DOOR).frame().origin, Vector3(45, -11, 1.5), "corridor-side door centre")
	assert_true(layout.door(QuartersLayout.DOOR).aperture() == Vector2(1.2, 2.4), "approved doorway size")
	var room: ShipLayout.Spec
	for spec: ShipLayout.Spec in layout.records():
		if spec.id() == QuartersLayout.ID: room = spec
	assert_true(room is ShipLayout.QuartersSpec, "room is an authored layout space")
	var approved: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://docs/art/quarters/layout.json"))
	assert_float_equal(QuartersLayout.WIDTH, approved.room.width_x, "approved width")
	assert_float_equal(QuartersLayout.DEPTH, approved.room.depth_z, "approved depth")
	assert_float_equal(QuartersLayout.HEIGHT, approved.room.clear_height, "approved height")

func test_room_envelope_clears_connectors_lifts_and_wells() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in layout.deck(16).connector_ids():
		var spec := layout.connector(id)
		assert_false(QuartersLayout.envelope().intersects(spec.bounds()), "connector clearance")
		assert_false(QuartersLayout.envelope().intersects(layout.lift(spec.lift_id()).bounds()), "lift clearance")
		assert_false(QuartersLayout.envelope().intersects(layout.well(spec.well_id()).bounds()), "well clearance")
	assert_int_equal(QuartersGeometry.shell().size(), 6, "five room faces plus the entrance head return")
	var ids := ShipCollision.new(layout).solid_ids(16)
	for part: String in ["FLOOR", "CEILING", "FORE", "AFT", "STARBOARD", "ENTRANCE-HEAD"]:
		assert_true(StringName("D16-QUARTERS/" + part) in ids, "shell collider " + part)

func test_manual_release_uses_shared_sliding_door_and_clears_passage() -> void:
	var game := Game.new(0)
	var door := game.layout.door(QuartersLayout.DOOR)
	assert_int_equal(door.kind(), ShipLayout.DoorKind.SIDE, "regular side-door appearance")
	assert_int_equal(door.policy(), ShipLayout.Policy.PRESS_SLIDE, "existing release policy")
	assert_true(SlidingDoorParts.has_pocket(door), "shared in-wall pocket")
	var context := Doors.Context.new()
	context.face_id = door.face_ids()[1]
	assert_false(game.doors.press(door.id(), context).accepted(), "release is on corridor face")
	context.face_id = door.face_ids()[0]
	assert_true(game.doors.press(door.id(), context).accepted(), "corridor release needs no badge or tool")
	for tick: int in range(47): game.advance_doors()
	assert_true(StringName("%s/BLOCKER" % door.id()) in game.collision.solid_ids(16), "opening remains blocked until completion")
	game.advance_doors()
	assert_false(StringName("%s/BLOCKER" % door.id()) in game.collision.solid_ids(16), "passage opens on completion")
	assert_float_equal(game.doors.snapshot(door.id()).offset.x, Vector3(1.35, 0, 0).x, "full-width leaf clears 1.2 m opening")
	assert_vec3_equal(game.doors.snapshot(door.id()).offset, Vector3(1.35, 0, 0), "slides along entrance wall")
